"""Run40: non-integrated, bounded read-only Store history adapter for Run39.

Never creates Store, writes state, reads an oracle, runs a model, or grants
source/answer authority. The caller owns an already-open Store and current
EventEnvelope. A later consumer MUST revalidate selected sources at use time.
"""
from __future__ import annotations

import json

from scripts import run39_b2_rule_span_candidate as selector

MAX_SQL_ROWS = 256
MAX_HISTORY = 32


def _source_ref(value):
    return (type(value) is dict and type(value.get('source_id')) is str and
            type(value.get('sha256')) is str and
            type(value.get('char_start')) is int and
            type(value.get('char_end')) is int and
            value.get('modality') == 'text')


def collect_history(store, current_event, session, generation, model_revision, limit=32):
    """Return past B2 offers as source-verified, immutable-origin SHADOW inputs."""
    if (type(limit) is not int or not 1 <= limit <= MAX_HISTORY or
            type(current_event) is not dict or
            type(current_event.get('event_id')) is not str or
            type(session) is not str or type(generation) is not str or
            type(model_revision) is not str or
            not _source_ref(current_event.get('source_ref'))):
        raise ValueError('RUN40_INPUT_OR_BOUNDS')
    current = store.one(
        'SELECT rowid AS seq,created,generation_id,source_id,packet '
        'FROM events WHERE id=? AND session_id=?',
        (current_event['event_id'], session))
    if not current or current['generation_id'] != generation:
        raise ValueError('RUN40_CURRENT_EVENT_SCOPE')
    try:
        current_packet = json.loads(current['packet'])
    except (ValueError, TypeError) as exc:
        raise ValueError('RUN40_CURRENT_EVENT_PACKET') from exc
    ref = current_event['source_ref']
    if (type(current_packet) is not dict or
            current_packet.get('source_ref') != ref or
            current['source_id'] != ref['source_id'] or
            current_event.get('brain_generation_id') != generation):
        raise ValueError('RUN40_CURRENT_EVENT_SOURCE')
    store.read_source(ref)  # fail closed on a deleted/tampered current input
    rows = store.rows(
        'SELECT p.id AS offer_id,p.payload AS offer_payload,p.event_id AS offer_event_id,'
        'p.created AS offer_created,e.id AS event_id,e.session_id AS session_id,'
        'e.generation_id AS event_generation,e.source_id AS event_source_id,'
        'e.packet AS event_packet,e.rowid AS event_seq '
        'FROM packets p JOIN events e ON e.id=p.event_id '
        'WHERE p.kind=? AND e.session_id=? AND e.rowid<? AND p.created<=? '
        'ORDER BY e.rowid DESC,p.created DESC LIMIT ?',
        ('OfferPacket', session, current['seq'], current['created'], MAX_SQL_ROWS))
    if type(rows) is not list or len(rows) > MAX_SQL_ROWS:
        raise ValueError('RUN40_UNBOUNDED_SQL')
    result = []
    seen = set()
    for row in rows:
        if len(result) >= limit:
            break
        try:
            p = json.loads(row['offer_payload'])
            event = json.loads(row['event_packet'])
            src = event['source_ref']
            if (type(p) is not dict or type(event) is not dict or
                    p.get('packet_id') != row['offer_id'] or
                    p.get('event_id') != row['event_id'] or
                    row['offer_event_id'] != row['event_id'] or
                    p.get('role') != 'B2_GIST' or
                    p.get('brain_generation_id') != generation or
                    row['event_generation'] != generation or
                    p.get('model_revision') != model_revision or
                    row['session_id'] != session or
                    row['event_id'] in seen or
                    not _source_ref(src) or
                    src['source_id'] != row['event_source_id'] or
                    not isinstance(p.get('offer'), dict)):
                continue
            store.read_source(src)  # tombstone/hash check; no trust in offer summary
        except (KeyError, ValueError, TypeError, OSError):
            continue
        seen.add(row['event_id'])
        result.append({'offer_id': row['offer_id'], 'event_id': row['event_id'],
                       'role': 'B2_GIST', 'session': session,
                       'generation': generation, 'model_revision': model_revision,
                       'source_ref': src,
                       'hypothesis': p['offer'].get('summary', '')})
    return result


def select_from_store(store, current_event, session, generation, model_revision,
                      *, scan_limit=32, cap=768, slots=4, excerpt_chars=240):
    history = collect_history(store, current_event, session, generation,
                              model_revision, limit=scan_limit)
    text = store.read_source(current_event['source_ref'])
    return selector.select_rule_span(
        text, current_event['event_id'], session, generation, model_revision,
        history, store.read_source, scan_limit=scan_limit, cap=cap,
        slots=slots, excerpt_chars=excerpt_chars)
