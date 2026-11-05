"""Opt-in, isolated feedback pagination candidate; it has NO runtime consumers.

Call ``process_page(store)`` explicitly. The only write is a dedicated SQLite
``states`` entry. Neither the existing BP7_RECON state, facts, recall ordering,
nor training permissions are changed. No existing state is silently migrated.

Rows are scanned in SQLite insertion order, not event-time order. The cursor is
advanced past invalid rows; when a sweep finishes it resets to the start. A
durable set of feedback IDs prevents re-processing after restart and also lets
later inserts with old timestamps or recycled/lower rowids be found on the next
sweep. A repaired invalid row can likewise be picked up on a later sweep.

The store transaction atomically commits the ledger and the page cursor. It
prevents concurrent store writers from interleaving a page. Feedback IDs must
not be reused for a different logical decision. Late records may be handled on
the next sweep rather than in chronological order. The JSON ledger grows with
the number of decisions; this proof-of-correctness implementation is not yet a
bounded production index, does not implement unlearning/reconciliation, and is
not an activation or utility result. ``record`` versus ``learn`` is preserved
as data; this does not decide either permission's authorization for learning.
"""

import json
import math

from v13.common import dumps


KEY = 'BP7_RECON_PAGINATION_CANDIDATE'
REVISION = 'bp7-recon-pagination-candidate-v1'
MAX_PAGE_SIZE = 1024


def _empty():
    return {'revision': REVISION, 'cursor': None, 'sweeps': 0, 'events': []}


def _extract(store, feedback):
    """Return a source-checked event or None for an invalid/orphaned row.

    This does not convert a recorded decision into permission to train. Reads
    and source validation occur while the caller owns the Store transaction.
    Unexpected failures propagate, causing the whole candidate page to roll back.
    """
    try:
        if feedback['value'] not in ('relevant', 'irrelevant'):
            return None
        if feedback['permission'] not in ('record', 'learn'):
            return None
        if not math.isfinite(feedback['created']):
            return None
        decisions = store.rows(
            "SELECT payload FROM packets WHERE event_id=? AND kind='HumanDecision' "
            "AND json_valid(payload) AND json_extract(payload,'$.source_ref.source_id')=? LIMIT 2",
            (feedback['event_id'], feedback['source_id']))
        if len(decisions) != 1:
            return None
        decision = json.loads(decisions[0]['payload'])
        if (decision.get('kind') != 'retrieval'
                or decision.get('value') != feedback['value']
                or decision.get('learning_permission') != feedback['permission']
                or store.read_source(decision['source_ref']) != feedback['value']):
            return None
        selection = decision['selection']
        memory_id = selection['memory_id']
        if not isinstance(memory_id, str) or not memory_id:
            return None
        event = store.one('SELECT packet,session_id FROM events WHERE id=?', (feedback['event_id'],))
        if event is None:
            return None
        envelope = json.loads(event['packet'])
        if (envelope.get('authority') != 'AUTHORITATIVE'
                or selection['query_ref'] != envelope['source_ref']):
            return None
        store.read_source(selection['query_ref'])
        memory = store.one(
            "SELECT m.value,m.key_text,m.source_id,s.hash,s.chars FROM memories m "
            "JOIN sources s ON s.id=m.source_id WHERE m.id=? AND m.active=1 AND s.deleted=0 "
            "AND (m.session_id=? OR m.scope='global')", (memory_id, event['session_id']))
        if memory is None:
            return None
        memory_ref = {'source_id': memory['source_id'], 'sha256': memory['hash'],
                      'char_start': 0, 'char_end': memory['chars'], 'modality': 'text'}
        if (selection['memory_ref'] != memory_ref
                or store.read_source(memory_ref) != memory['value']
                or store.read_source(selection['key_ref']) != memory['key_text']):
            return None
        return {'feedback_id': feedback['id'], 'memory_id': memory_id,
                'event_id': feedback['event_id'], 'sign': 1 if feedback['value'] == 'relevant' else -1,
                'created': feedback['created'], 'permission': feedback['permission'],
                'source_rowid': feedback['source_rowid']}
    except (KeyError, TypeError, ValueError, OSError, OverflowError):
        return None


def process_page(store, page_size=128):
    """Process at most one insertion-ordered page, atomically and explicitly.

    ``complete`` means this sweep reached its end, not that no future event can
    arrive. Call again for a new sweep, including to pick up repaired rows.
    Returned counts contain no source text or model-generated content.
    """
    if type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError('page_size must be an integer between 1 and %d' % MAX_PAGE_SIZE)
    with store.tx() as db:
        old = db.execute('SELECT version,payload FROM states WHERE key=?', (KEY,)).fetchone()
        state = json.loads(old['payload']) if old else _empty()
        if (not isinstance(state, dict) or state.get('revision') != REVISION
                or not isinstance(state.get('events'), list)
                or (state.get('cursor') is not None and type(state['cursor']) is not int)
                or type(state.get('sweeps')) is not int or state['sweeps'] < 0):
            raise ValueError('Invalid or incompatible candidate state')
        ids = [event['feedback_id'] for event in state['events']]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate feedback IDs in candidate state')
        seen = set(ids)
        cursor = state['cursor']
        sql = "SELECT rowid AS source_rowid,* FROM feedback WHERE kind='retrieval'"
        args = []
        if cursor is not None:
            sql += ' AND rowid>?'
            args.append(cursor)
        sql += ' ORDER BY rowid LIMIT ?'
        args.append(page_size)
        rows = [dict(row) for row in db.execute(sql, args).fetchall()]
        added = invalid = 0
        for feedback in rows:
            if feedback['id'] not in seen:
                candidate = _extract(store, feedback)
                if candidate is None:
                    invalid += 1
                else:
                    state['events'].append(candidate)
                    seen.add(feedback['id'])
                    added += 1
            state['cursor'] = feedback['source_rowid']
        complete = len(rows) < page_size
        if complete:
            state['cursor'] = None
            state['sweeps'] += 1
        version = old['version'] if old else 0
        db.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                   (KEY, version + 1, dumps(state)))
        return {'scanned': len(rows), 'added': added, 'invalid': invalid,
                'complete': complete, 'cursor': state['cursor'],
                'sweeps': state['sweeps'], 'total': len(state['events'])}
