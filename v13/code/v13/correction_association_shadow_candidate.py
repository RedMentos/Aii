"""Source-bound episodic associations from human corrections, shadow only.

The frozen runtime does not import this module. The separate source-bound
integration candidate calls it after F1/F5 feedback and during later recall.
No generated text, model state, retrieval authority or model weights change.
"""
import json

from .memory import Memory


KEY = 'correction-association-shadow-v1'
REVISION = 'correction-association-shadow-v1'
MAX_LINKS = 256
MAX_RETRIEVED = 8


def _empty():
    return {'revision': REVISION, 'mode': 'off', 'links': []}


def _load(store):
    state, version = store.state(KEY, None)
    state = _empty() if state is None else state
    if (type(state) is not dict or state.get('revision') != REVISION
            or state.get('mode') not in ('off', 'shadow')
            or type(state.get('links')) is not list or len(state['links']) > MAX_LINKS):
        raise ValueError('correction association state invalid')
    return state, version


def _mutate(store, change):
    for _ in range(8):
        state, version = _load(store)
        result = change(state)
        try:
            store.set_state(KEY, state, expected=version)
            return result
        except ValueError as exc:
            if str(exc) != 'Stale state write':
                raise
    raise ValueError('correction association state contention')


def set_mode(store, mode):
    """Explicit operator selects off or shadow; there is no active mode."""
    if mode not in ('off', 'shadow'):
        raise ValueError('correction association mode: off|shadow')
    return _mutate(store, lambda state: state.update(mode=mode) or mode)


def _memory(store, cfg, memory_id, session):
    row = store.one("""SELECT m.*,s.hash,s.chars FROM memories m
        JOIN sources s ON s.id=m.source_id
        WHERE m.id=? AND m.active=1 AND s.deleted=0
          AND m.kind IN ('fact','style','preference')
          AND (m.session_id=? OR m.scope='global')""", (memory_id, session))
    if row is None or not Memory(store, cfg)._verified_rows([row]):
        raise ValueError('memory authority unavailable')
    ref = {'source_id': row['source_id'], 'sha256': row['hash'],
           'char_start': 0, 'char_end': row['chars'], 'modality': 'text'}
    if store.read_source(ref) != row['value']:
        raise ValueError('memory source changed')
    return row, ref


def record_correction(store, cfg, event_id, memory_id, session):
    """Bind a correction to memories actually retrieved in its finished turn."""
    state, _ = _load(store)
    if state['mode'] != 'shadow':
        return {'status': 'OFF', 'recorded': 0}
    event = store.one('SELECT packet FROM events WHERE id=? AND session_id=?', (event_id, session))
    message = store.one("""SELECT metadata FROM messages WHERE event_id=? AND session_id=?
        AND role='assistant' AND status='FINAL' ORDER BY id DESC LIMIT 1""", (event_id, session))
    if not event or not message:
        raise ValueError('finished event required')
    envelope = json.loads(event['packet'])
    if envelope.get('authority') != 'AUTHORITATIVE' or envelope.get('event_id') != event_id:
        raise ValueError('authoritative event required')
    store.read_source(envelope['source_ref'])
    kind = store.one('SELECT kind FROM memories WHERE id=?', (memory_id,))
    if kind is not None and kind['kind'] not in ('fact', 'style', 'preference'):
        return {'status': 'UNSUPPORTED_FEEDBACK_KIND', 'recorded': 0}
    target, target_ref = _memory(store, cfg, memory_id, session)
    if target['event_id'] != event_id:
        raise ValueError('correction event mismatch')
    metadata = json.loads(message['metadata'])
    retrieved = metadata.get('memory_retrieval')
    if type(retrieved) is not list or len(retrieved) > MAX_RETRIEVED:
        raise ValueError('retrieval trace unavailable')
    additions = []
    for item in retrieved:
        if type(item) is not dict or type(item.get('memory_id')) is not str:
            raise ValueError('invalid retrieval trace')
        prior, prior_ref = _memory(store, cfg, item['memory_id'], session)
        if item.get('source_ref') != prior_ref:
            raise ValueError('retrieval source mismatch')
        if prior['id'] == target['id']:
            continue
        additions.append({'event_id': event_id, 'session_id': session,
                          'from_memory_id': prior['id'], 'to_memory_id': target['id'],
                          'from_source_ref': prior_ref, 'to_source_ref': target_ref})

    def add(current):
        if current['mode'] != 'shadow':
            return {'status': 'OFF', 'recorded': 0}
        known = {(x['event_id'], x['from_memory_id'], x['to_memory_id']) for x in current['links']}
        unique = []
        for item in additions:
            identity = (item['event_id'], item['from_memory_id'], item['to_memory_id'])
            if identity not in known:
                unique.append(item)
                known.add(identity)
        if len(current['links']) + len(unique) > MAX_LINKS:
            raise ValueError('correction association capacity exhausted')
        current['links'].extend(unique)
        return {'status': 'SHADOW_RECORDED', 'recorded': len(unique)}
    return _mutate(store, add)


def _replay_pass(store, event_id, memory_id, source_ref):
    for row in store.rows("SELECT id,payload FROM packets WHERE kind='ReplayItem' AND event_id=?", (event_id,)):
        p = json.loads(row['payload'])
        if (type(p) is dict and p.get('packet_id') == row['id']
                and p.get('event_id') == event_id and p.get('producer_component') == 'F9_SLEEP_A'
                and p.get('stage') == 'SLEEP_A' and p.get('outcome') == 'PASS'
                and source_ref in p.get('source_refs', [])
                and any(type(c) is dict and c.get('memory_id') == memory_id
                        and c.get('probe') == 'RECALL' and c.get('pass') is True
                        for c in p.get('checks', []))):
            return p['packet_id']
    return None


def candidates(store, cfg, session, memories):
    """Actual later recall consumes verified links, but produces shadow IDs only."""
    state, _ = _load(store)
    if state['mode'] != 'shadow':
        return []
    direct = {m['id']: m for m in memories}
    found = []
    for link in state['links']:
        if (type(link) is not dict or link.get('session_id') != session
                or link.get('from_memory_id') not in direct
                or link.get('to_memory_id') in direct):
            continue
        try:
            _, from_ref = _memory(store, cfg, link['from_memory_id'], session)
            _, to_ref = _memory(store, cfg, link['to_memory_id'], session)
            if (from_ref != link['from_source_ref'] or to_ref != link['to_source_ref']
                    or direct[link['from_memory_id']].get('source_ref') != from_ref):
                continue
            replay = _replay_pass(store, link['event_id'], link['to_memory_id'], to_ref)
            if not replay:
                continue
            found.append({'memory_id': link['to_memory_id'], 'via_memory_id': link['from_memory_id'],
                          'source_ref': to_ref, 'correction_event_id': link['event_id'],
                          'replay_packet_id': replay, 'relation': 'CORRELATIONAL_CONTEXT',
                          'authority': 'SHADOW_ONLY'})
        except (ValueError, TypeError, KeyError, OSError):
            continue
        if len(found) >= 2:
            break
    return found


def rollback(store, memory_id):
    """Remove candidate links only; original memories and replay remain intact."""
    def remove(state):
        old = state['links']
        state['links'] = [x for x in old if x.get('to_memory_id') != memory_id]
        return {'removed': len(old) - len(state['links'])}
    return _mutate(store, remove)
