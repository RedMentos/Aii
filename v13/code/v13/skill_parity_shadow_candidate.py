"""Source-bound route-parity observations for an isolated AG4 review copy.

The derived view is optional and has no skill-promotion, output, or weight
authority. A completed turn and a matching route are not correctness labels.
"""
import json

from . import c5_feedback_shadow_store_candidate as feedback
from .agi.skills import SkillLibrary
from .common import digest, dumps


POLICY_KEY = 'AG4_PARITY_SHADOW_POLICY_V1'
POLICY_REVISION = 'ag4-parity-shadow-policy-v1'
KEY = 'AG4_PARITY_SHADOW_V1'
REVISION = 'ag4-parity-shadow-v1'
MAX_EVENTS = 1024
ROUTES = {'simple', 'detail', 'gist', 'both'}
LEARNING = {'CANDIDATE', 'SHADOW'}


def _enabled(conn):
    row = conn.execute('SELECT payload FROM states WHERE key=?', (POLICY_KEY,)).fetchone()
    if row is None:
        return False
    policy = json.loads(row['payload'])
    if (not isinstance(policy, dict) or set(policy) != {'revision', 'enabled'}
            or policy['revision'] != POLICY_REVISION or type(policy['enabled']) is not bool):
        raise ValueError('invalid parity shadow policy')
    return policy['enabled']


def capture_enabled(store):
    with store.tx() as conn:
        return _enabled(conn)


def set_capture_enabled(store, enabled, authority='SYSTEM'):
    if type(enabled) is not bool:
        raise ValueError('enabled must be boolean')
    if enabled and authority != 'EXPLICIT_HUMAN':
        raise PermissionError('shadow capture requires explicit human choice')
    with store.tx() as conn:
        try:
            old = _enabled(conn)
        except ValueError:
            if enabled:
                raise
            old = None
        if old == enabled:
            return enabled
        row = conn.execute('SELECT version FROM states WHERE key=?', (POLICY_KEY,)).fetchone()
        version = row['version'] if row else 0
        conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                     (POLICY_KEY, version + 1, dumps({'revision': POLICY_REVISION, 'enabled': enabled})))
    return enabled


def _fingerprint(skill):
    return digest(dumps({key: skill.get(key) for key in
                         ('name', 'steps', 'trigger', 'origin', 'created', 'human_credit_instance')}))


def annotate_candidates(store, candidates):
    """Bind predictions to a particular skill instance before the answer."""
    if not capture_enabled(store):
        return candidates
    from .skilllive import _route_only
    lib = SkillLibrary(store)
    result = []
    for candidate in candidates:
        name, route = candidate['name'], candidate['route']
        binding = lib.human_binding(name)
        skill = lib.get(name)
        if (skill.get('human_credit_instance') != binding['instance']
                or skill.get('human_credit_epoch', 0) != binding['epoch']
                or skill.get('stage') not in LEARNING or _route_only(skill) != route):
            raise ValueError('skill changed during prediction')
        result.append({'name': name, 'route': route,
                       'shadow_receipt': binding | {'skill_sha256': _fingerprint(skill)}})
    return result


def _state(conn):
    row = conn.execute('SELECT version,payload FROM states WHERE key=?', (KEY,)).fetchone()
    if row is None:
        return {'revision': REVISION, 'events': {}}, 0
    state = json.loads(row['payload'])
    if (not isinstance(state, dict) or set(state) != {'revision', 'events'}
            or state['revision'] != REVISION or not isinstance(state['events'], dict)
            or len(state['events']) > MAX_EVENTS):
        raise ValueError('invalid parity shadow state')
    return state, row['version']


def _event_snapshot(store, conn, session, event_id, expected_route=None):
    from .skilllive import _route_only
    binding = feedback._binding(store, conn, session, event_id)
    row = conn.execute('SELECT metadata FROM messages WHERE id=?', (binding['message_id'],)).fetchone()
    metadata = json.loads(row['metadata'])
    candidates = metadata.get('skill_shadow')
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 4:
        raise ValueError('no bound shadow predictions')
    selected = conn.execute('SELECT payload FROM packets WHERE id=?', (binding['selection_id'],)).fetchone()
    route = json.loads(selected['payload']).get('route_hint')
    if route not in ROUTES or (expected_route is not None and route != expected_route):
        raise ValueError('route hint changed')
    row = conn.execute('SELECT payload FROM states WHERE key=?', ('G4_SKILLS',)).fetchone()
    skills = json.loads(row['payload']).get('skills', {}) if row else {}
    seen = set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != {'name', 'route', 'shadow_receipt'}:
            raise ValueError('invalid shadow prediction')
        name, proposed, receipt = candidate['name'], candidate['route'], candidate['shadow_receipt']
        if (not isinstance(name, str) or not name or name in seen or proposed not in ROUTES
                or not isinstance(receipt, dict) or set(receipt) != {'instance', 'epoch', 'skill_sha256'}):
            raise ValueError('invalid shadow prediction binding')
        seen.add(name)
        skill = skills.get(name)
        if (not isinstance(skill, dict) or skill.get('stage') not in LEARNING
                or skill.get('human_credit_instance') != receipt['instance']
                or skill.get('human_credit_epoch', 0) != receipt['epoch']
                or _fingerprint(skill) != receipt['skill_sha256'] or _route_only(skill) != proposed):
            raise ValueError('shadow skill source changed')
    return {'binding': binding, 'route_hint': route, 'candidates': candidates}


def observe_final(store, event_id, route):
    """Persist an event once after checking its answer and pre-answer receipt."""
    with store.tx() as conn:
        if not _enabled(conn):
            return {'status': 'OFF', 'learning_authority': 0}
        event = conn.execute('SELECT session_id FROM events WHERE id=?', (event_id,)).fetchone()
        if event is None:
            raise ValueError('event not found')
        entry = _event_snapshot(store, conn, event['session_id'], event_id, route)
        state, version = _state(conn)
        previous = state['events'].get(event_id)
        if previous is not None and previous != entry:
            raise ValueError('stored observation binding changed')
        if previous == entry:
            return {'status': 'UNCHANGED', 'learning_authority': 0}
        if len(state['events']) >= MAX_EVENTS:
            raise ValueError('shadow parity ledger full')
        state['events'][event_id] = entry
        conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)', (KEY, version + 1, dumps(state)))
        return {'status': 'RECORDED', 'learning_authority': 0}


def _has_current_fact_correction(store, conn, session, event_id):
    """Check live F5/feedback/F1 lineage without treating it as model truth."""
    event = conn.execute('SELECT generation_id FROM events WHERE id=? AND session_id=?',
                         (event_id, session)).fetchone()
    if event is None:
        raise ValueError('event no longer available')
    rows = conn.execute("SELECT f.source_id,f.value,f.permission,m.value AS memory_value,m.session_id, "
                        "s.kind AS source_kind,s.chars AS source_chars "
                        "FROM feedback f JOIN memories m ON m.event_id=f.event_id AND m.source_id=f.source_id "
                        "JOIN sources s ON s.id=f.source_id "
                        "WHERE f.event_id=? AND f.kind='fact' AND m.kind='fact' AND m.active=1 LIMIT 65",
                        (event_id,)).fetchall()
    packets = conn.execute("SELECT id,generation_id,payload FROM packets WHERE event_id=? "
                           "AND kind='HumanDecision' LIMIT 129", (event_id,)).fetchall()
    if len(rows) > 64 or len(packets) > 128:
        raise ValueError('fact correction scan saturated')
    decisions = []
    for packet in packets:
        try:
            payload = json.loads(packet['payload'])
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            decisions.append((packet, payload))
    valid = invalid = False
    for row in rows:
        if (row['session_id'] != session or row['permission'] not in {'record', 'learn'}
                or row['source_kind'] != 'HUMAN_DECISION'):
            invalid = True
            continue
        candidates = [(p, x) for p, x in decisions if isinstance(x.get('source_ref'), dict)
                      and x['source_ref'].get('source_id') == row['source_id']]
        if len(candidates) != 1:
            invalid = True
            continue
        packet, payload = candidates[0]
        ref = payload['source_ref']
        if (packet['generation_id'] != event['generation_id'] or payload.get('packet_id') != packet['id']
                or payload.get('brain_generation_id') != event['generation_id']
                or payload.get('event_id') != event_id or payload.get('producer_component') != 'F5_HUMAN_CONTROL'
                or payload.get('schema_version') != '1.0' or ref.get('modality') != 'text'
                or ref.get('char_start') != 0 or ref.get('char_end') != row['source_chars']
                or payload.get('kind') != 'fact' or payload.get('learning_permission') != row['permission']
                or not isinstance(payload.get('provenance'), list) or ref not in payload['provenance']):
            invalid = True
            continue
        try:
            text = store.read_source(ref)
        except (ValueError, OSError, KeyError, TypeError):
            invalid = True
            continue
        if text == payload.get('value') == row['value'] == row['memory_value']:
            valid = True
        else:
            invalid = True
    return valid, invalid


def view(store, session):
    """Revalidate sources and join the latest quality labels without learning."""
    if not isinstance(session, str) or not session:
        raise ValueError('session required')
    with store.tx() as conn:
        state, version = _state(conn)
        ratings = feedback._ratings(conn)
        events = excluded = 0
        by_skill = {}
        for event_id, entry in state['events'].items():
            if not isinstance(entry, dict) or not isinstance(entry.get('binding'), dict):
                raise ValueError('invalid parity shadow entry')
            if entry['binding'].get('session_id') != session:
                continue
            try:
                if _event_snapshot(store, conn, session, event_id) != entry:
                    raise ValueError('stale observation')
                fact_corrected, fact_unverified = _has_current_fact_correction(store, conn, session, event_id)
            except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
                excluded += 1
                continue
            events += 1
            for candidate in entry['candidates']:
                row = by_skill.setdefault(candidate['name'], {'observations': 0, 'matches': 0,
                    'mismatches': 0, 'explicit_positive': 0, 'explicit_negative': 0,
                    'explicit_neutral': 0, 'implicit_rated': 0, 'fact_corrected': 0,
                    'positive_and_fact_corrected': 0, 'fact_source_unverified': 0})
                row['observations'] += 1
                row['matches' if candidate['route'] == entry['route_hint'] else 'mismatches'] += 1
                explicit = ratings.get((event_id, 'EXPLICIT_NOTE'))
                if explicit:
                    score = explicit['score']
                    label = 'explicit_positive' if score >= 6 else 'explicit_negative' if score <= 4 else 'explicit_neutral'
                    row[label] += 1
                if (event_id, 'IMPLICIT_CHAT') in ratings:
                    row['implicit_rated'] += 1
                if fact_corrected:
                    row['fact_corrected'] += 1
                    if explicit and explicit['score'] >= 6:
                        row['positive_and_fact_corrected'] += 1
                if fact_unverified:
                    row['fact_source_unverified'] += 1
        return {'mode': 'SHADOW', 'learning_authority': 0, 'version': version,
                'events': events, 'excluded': excluded, 'by_skill': by_skill,
                'claim_limit': 'Route agreement and current human ratings are not proof of skill correctness'}
