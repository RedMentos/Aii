"""Source-bound, persisted SHADOW consumer for the review-only C5 ledger.

The review branch's rating writer can invoke this module when explicitly
enabled. It records only a derived evidence snapshot under its own state key;
it never changes C5 weights, the existing C5 aggregate, a model, or authority.
``capture_in_tx`` runs in the rating writer's transaction. Calling ``capture``
afterwards uses a separate transaction and requires retry/reconciliation after
a crash.
"""
import json

from . import actionlearn, c5_feedback_ledger_candidate as ledger
from .common import digest, dumps

KEY = 'C5_FEEDBACK_SHADOW_STORE_V1'
REVISION = 'c5-feedback-shadow-store-v1'
POLICY_KEY = 'C5_FEEDBACK_SHADOW_POLICY_V1'
POLICY_REVISION = 'c5-feedback-shadow-policy-v1'
RATINGS_KEY = 'ANSWER_RATINGS'
ORIGINS = ('EXPLICIT_NOTE', 'IMPLICIT_CHAT')
MAX_EVENTS = 4096


def capture_enabled_in_tx(conn):
    """Default off; read the policy inside the rating writer's transaction."""
    if not conn.in_transaction:
        raise ValueError('open Store transaction required')
    row = conn.execute('SELECT payload FROM states WHERE key=?', (POLICY_KEY,)).fetchone()
    if row is None:
        return False
    policy = json.loads(row['payload'])
    if (not isinstance(policy, dict) or set(policy) != {'revision', 'enabled'}
            or policy['revision'] != POLICY_REVISION or type(policy['enabled']) is not bool):
        raise ValueError('invalid shadow capture policy')
    return policy['enabled']


def capture_enabled(store):
    with store.tx() as conn:
        return capture_enabled_in_tx(conn)


def set_capture_enabled(store, enabled, authority='SYSTEM'):
    if type(enabled) is not bool:
        raise ValueError('enabled must be boolean')
    if enabled and authority != 'EXPLICIT_HUMAN':
        raise PermissionError('shadow capture requires explicit human choice')
    with store.tx() as conn:
        try:
            current = capture_enabled_in_tx(conn)
        except ValueError:
            if enabled:
                raise
            current = None  # A damaged policy can always be explicitly disabled.
        if current == enabled:
            return enabled
        row = conn.execute('SELECT version FROM states WHERE key=?', (POLICY_KEY,)).fetchone()
        version = row['version'] if row else 0
        conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                     (POLICY_KEY, version + 1, dumps({'revision': POLICY_REVISION, 'enabled': enabled})))
    return enabled


def _state(conn):
    row = conn.execute('SELECT version,payload FROM states WHERE key=?', (KEY,)).fetchone()
    if row is None:
        return {'revision': REVISION, 'mode': 'SHADOW', 'events': {}}, 0
    state = json.loads(row['payload'])
    if (not isinstance(state, dict) or set(state) != {'revision', 'mode', 'events'}
            or state['revision'] != REVISION or state['mode'] != 'SHADOW'
            or not isinstance(state['events'], dict) or len(state['events']) > MAX_EVENTS):
        raise ValueError('invalid shadow ledger state')
    for event_id, entry in state['events'].items():
        if (not isinstance(event_id, str) or not event_id or not isinstance(entry, dict)
                or set(entry) != {'binding', 'ratings'} or not isinstance(entry['binding'], dict)
                or not isinstance(entry['ratings'], dict) or not entry['ratings']
                or not set(entry['ratings']).issubset(ORIGINS)):
            raise ValueError('invalid shadow ledger entry')
        for rating in entry['ratings'].values():
            if (not isinstance(rating, dict) or set(rating) != {'score', 'sha256'}
                    or type(rating['score']) is not int or not 1 <= rating['score'] <= 10
                    or not isinstance(rating['sha256'], str) or len(rating['sha256']) != 64):
                raise ValueError('invalid shadow rating')
    return state, row['version']


def _ratings(conn):
    row = conn.execute('SELECT payload FROM states WHERE key=?', (RATINGS_KEY,)).fetchone()
    if row is None:
        return {}
    payload = json.loads(row['payload'])
    if not isinstance(payload, dict) or not isinstance(payload.get('ratings'), list):
        raise ValueError('invalid rating state')
    result = {}
    for rating in payload['ratings']:
        if not isinstance(rating, dict):
            raise ValueError('invalid rating row')
        event_id, origin, score = rating.get('event_id'), rating.get('origin'), rating.get('score')
        if (not isinstance(event_id, str) or not event_id or origin not in ORIGINS
                or type(score) is not int or not 1 <= score <= 10
                or rating.get('authority') != 'HUMAN_QUALITY_LABEL_NOT_FACT'):
            raise ValueError('invalid rating row')
        key = (event_id, origin)
        if key in result:
            raise ValueError('duplicate rating origin')
        # Keep no note or answer text in the derived state.
        result[key] = {'score': score, 'sha256': digest(dumps(rating))}
    return result


def _binding(store, conn, session_id, event_id):
    if not all(isinstance(x, str) and x for x in (session_id, event_id)):
        raise ValueError('session and event required')
    event = conn.execute('SELECT session_id,source_id,generation_id,packet FROM events WHERE id=?',
                         (event_id,)).fetchone()
    if event is None or event['session_id'] != session_id:
        raise ValueError('event not available in session')
    envelope = json.loads(event['packet'])
    if not isinstance(envelope, dict):
        raise ValueError('event envelope invalid')
    ref = envelope.get('source_ref')
    if (envelope.get('event_id') != event_id or envelope.get('authority') != 'AUTHORITATIVE'
            or envelope.get('brain_generation_id') != event['generation_id']
            or not isinstance(ref, dict) or ref.get('source_id') != event['source_id']):
        raise ValueError('event source binding invalid')
    # This also checks revocation, original content hash and span bounds.
    store.read_source(ref)
    rows = conn.execute("SELECT id,session_id,text,metadata FROM messages WHERE event_id=? "
                        "AND role='assistant' AND status='FINAL' ORDER BY id", (event_id,)).fetchall()
    if len(rows) != 1 or rows[0]['session_id'] != session_id:
        raise ValueError('unique final answer required')
    message = rows[0]
    metadata = json.loads(message['metadata'])
    if not isinstance(metadata, dict) or metadata.get('self_candidate_hash') != digest(message['text']):
        raise ValueError('answer content binding invalid')
    selection_id = metadata.get('action_selection')
    if not isinstance(selection_id, str) or not selection_id:
        raise ValueError('final answer has no action selection')
    context_refs = metadata.get('context_source_refs')
    if (not isinstance(context_refs, list) or not context_refs or ref not in context_refs
            or any(not isinstance(item, dict) for item in context_refs)):
        raise ValueError('final answer context sources unavailable')
    for context_ref in context_refs:
        store.read_source(context_ref)
    selection = conn.execute("SELECT event_id,generation_id,payload FROM packets "
                             "WHERE id=? AND kind='ActionSelection'", (selection_id,)).fetchone()
    if (selection is None or selection['event_id'] != event_id
            or selection['generation_id'] != event['generation_id']):
        raise ValueError('action selection binding invalid')
    packet = json.loads(selection['payload'])
    if not isinstance(packet, dict) or not isinstance(packet.get('provenance'), list):
        raise ValueError('action selection packet invalid')
    if (packet.get('packet_id') != selection_id or packet.get('event_id') != event_id
            or packet.get('brain_generation_id') != event['generation_id']
            or packet.get('producer_component') != 'C5_ACTION_GATE'
            or packet.get('stage') != 'COMMIT' or ref not in packet.get('provenance', [])):
        raise ValueError('action selection provenance invalid')
    selected = packet.get('selected')
    if not isinstance(selected, dict):
        raise ValueError('action selection missing')
    action = selected.get('action_id')
    learning = packet.get('learning')
    context = (learning.get('context') if isinstance(learning, dict) else None) or actionlearn.context(packet.get('route_hint'))
    # Reuse the existing ledger's identity/score validation without persisting it.
    ledger.record(ledger.empty(), event_id, context, action, 1)
    return {'session_id': session_id, 'event_sha256': digest(event['packet']),
            'source_ref': ref, 'context_source_refs': context_refs, 'message_id': message['id'],
            'message_sha256': digest(message['text']), 'message_metadata_sha256': digest(message['metadata']),
            'selection_id': selection_id,
            'selection_sha256': digest(selection['payload']), 'context': context,
            'action_id': action}


def capture_in_tx(store, conn, session_id, event_id, origin):
    """Capture current stored ratings in the caller's open Store transaction.

    The rating writer updates ANSWER_RATINGS then calls this function before
    the same transaction commits when capture has been explicitly enabled.
    """
    if conn is not store.db or not conn.in_transaction:
        raise ValueError('open Store transaction required')
    if origin not in ORIGINS:
        raise ValueError('unsupported rating origin')
    binding = _binding(store, conn, session_id, event_id)
    rating_index = _ratings(conn)
    current = {o: rating_index[(event_id, o)] for o in ORIGINS if (event_id, o) in rating_index}
    if origin not in current:
        raise ValueError('persisted rating not found')
    state, version = _state(conn)
    previous = state['events'].get(event_id)
    if previous is not None and previous['binding'] != binding:
        raise ValueError('stored event binding changed')
    entry = {'binding': binding, 'ratings': current}
    if previous == entry:
        return {'status': 'UNCHANGED', 'mode': 'SHADOW', 'learning_authority': 0, 'version': version}
    if previous is None and len(state['events']) >= MAX_EVENTS:
        raise ValueError('shadow ledger capacity exhausted')
    state['events'][event_id] = entry
    conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)', (KEY, version + 1, dumps(state)))
    return {'status': 'RECORDED', 'mode': 'SHADOW', 'learning_authority': 0, 'version': version + 1}


def capture(store, session_id, event_id, origin):
    """Reconcile a stored rating in a new atomic transaction; no live update."""
    with store.tx() as conn:
        return capture_in_tx(store, conn, session_id, event_id, origin)


def view(store, session_id):
    """Return source-current per-action feedback for one session, SHADOW only.

    Stale, revoked, changed or missing inputs are omitted.  An explicit rating
    has precedence over an implicit chat heuristic for the same event.  The
    raw source state and historical C5 means are never modified.
    """
    if not isinstance(session_id, str) or not session_id:
        raise ValueError('session required')
    with store.tx() as conn:
        state, version = _state(conn)
        rating_index = _ratings(conn)
        effective = ledger.empty()
        origins = {origin: ledger.empty() for origin in ORIGINS}
        excluded = 0
        for event_id, entry in state['events'].items():
            saved = entry['binding']
            if saved.get('session_id') != session_id:
                continue
            current = {o: rating_index[(event_id, o)] for o in ORIGINS if (event_id, o) in rating_index}
            try:
                if current != entry['ratings'] or _binding(store, conn, session_id, event_id) != saved:
                    raise ValueError('stale evidence')
            except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
                excluded += 1
                continue
            origin = 'EXPLICIT_NOTE' if 'EXPLICIT_NOTE' in current else 'IMPLICIT_CHAT'
            effective['ratings'][event_id] = {'context': saved['context'], 'action_id': saved['action_id'],
                                               'score': current[origin]['score']}
            for source_origin, rating in current.items():
                origins[source_origin]['ratings'][event_id] = {
                    'context': saved['context'], 'action_id': saved['action_id'], 'score': rating['score']}
        return {'mode': 'SHADOW', 'learning_authority': 0, 'version': version,
                'events': len(effective['ratings']), 'excluded': excluded,
                'by_action': ledger.aggregate(effective),
                'origin_counts': {origin: len(value['ratings']) for origin, value in origins.items()},
                'by_origin': {origin: ledger.aggregate(value) for origin, value in origins.items()},
                'claim_limit': 'Current feedback evidence only; not a factual truth or a live C5 update'}
