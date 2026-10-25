"""WP-U10 §9.1 Fast Episodic, "zweites Mal besser" for routes, without waiting for consolidation.

A single active human route correction (memories.kind='route') on a very similar earlier request is offered as the
route for the next request: relevance (memory.relevance, entity-aware: different named entities -> 0) at least
MIN_RELEVANCE, the newest best match wins. The suggestion carries its episode/source lineage (memory id, event id,
source id). Procedural consolidation (consolidation.route, >= 3 independent confirmations) still runs first and wins.
Mode: off | shadow (default: suggestion recorded in meta.route, scaffold route kept) | active (`:episodes route active`).
"""
import json
from .common import dumps
from .memory import Memory, relevance

KEY='U10_EPISODIC_ROUTE';REVISION='u10-episodic-route-v1'
MIN_RELEVANCE=.6   # BOOT: "very similar" request
ROUTES=('simple','detail','gist','both')
LIMIT=256

def mode(store):return (store.state(KEY,None)[0] or {}).get('mode','shadow')

def set_mode(store,m):
    if m not in {'off','shadow','active'}:raise ValueError('off|shadow|active')
    st,v=store.state(KEY,None);st=st or {'revision':REVISION};st['mode']=m;store.set_state(KEY,st,expected=v)
    store.log('episodic_route_mode',None,{'mode':m});return m

def _source_bound(store, m):
    """Read-only proof that a route still matches its human decision and original event.

    Mutable SQLite memory rows are hints, not independent route authority. This
    detects stale/partial corruption, not a fully malicious rewrite of every DB
    row and blob. Do not create MEMORY_KEY sources while evaluating a suggestion.
    """
    try:
        records = store.rows(
            "SELECT payload FROM packets WHERE kind='MemoryRecord' "
            "AND json_extract(payload,'$.memory_id')=? LIMIT 2", (m['id'],))
        if len(records) != 1:
            return False
        record = json.loads(records[0]['payload'])
        if (record.get('memory_id') != m['id']
                or record.get('event_id') != m['event_id']
                or record.get('kind') != 'route'
                or record.get('scope') != m['scope']
                or record.get('key') != m['key_text']):
            return False

        ref = record.get('source_ref')
        src = store.one("SELECT hash,chars,deleted FROM sources WHERE id=?", (m['source_id'],))
        if (not isinstance(ref, dict) or not src or src['deleted']
                or ref.get('source_id') != m['source_id']
                or ref.get('sha256') != src['hash']
                or ref.get('char_start') != 0
                or ref.get('char_end') != src['chars']
                or ref.get('modality') != 'text'
                or store.read_source(ref) != m['value']):
            return False

        origin = store.one("SELECT session_id,source_id,packet FROM events WHERE id=?", (m['event_id'],))
        if not origin or origin['session_id'] != m['session_id']:
            return False
        event = json.loads(origin['packet'])
        event_ref = event.get('source_ref')
        if (event.get('event_id') != m['event_id']
                or event.get('authority') != 'AUTHORITATIVE'
                or not isinstance(event_ref, dict)
                or event_ref.get('source_id') != origin['source_id']):
            return False
        store.read_source(event_ref)

        decisions = store.rows(
            "SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? "
            "AND json_extract(payload,'$.source_ref.source_id')=? "
            "AND json_extract(payload,'$.kind')='route' LIMIT 2",
            (m['event_id'], m['source_id']))
        if len(decisions) != 1:
            return False
        decision = json.loads(decisions[0]['payload'])
        return (decision.get('event_id') == m['event_id']
                and decision.get('value') == m['value']
                and decision.get('source_ref') == ref)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError):
        return False


def suggest(store,text,session):
    """Best matching active human route correction, or None."""
    best=None
    rows=store.rows("SELECT m.id,m.event_id,m.source_id,m.session_id,m.kind,m.scope,m.key_text,m.value,m.created,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.kind='route' AND m.active=1 AND s.deleted=0 AND (m.scope='global' OR m.session_id=?) ORDER BY m.created DESC LIMIT ?",(session,LIMIT))
    # A MemoryRecord + a plausible HumanDecision is not enough: the F5
    # feedback and its original human source must still be live. Batch-check
    # before any fast episodic suggestion (including ACTIVE route bypass).
    # Keep the existing route-specific source/event checks as a second guard.
    for m in Memory(store,{})._verified_rows(rows):
        if m['value'] not in ROUTES:continue
        rel=relevance(text,m['key_text'])
        if rel>=MIN_RELEVANCE and (best is None or rel>best['relevance']):
            if not _source_bound(store,m):
                store.log('episodic_route_source_refused',None,{'reason':'SOURCE_LINEAGE_UNVERIFIED'})
                continue
            best={'route':m['value'],'relevance':round(rel,4),'memory_id':m['id'],'event_id':m['event_id'],'source_id':m['source_id'],'source':'FAST_EPISODIC_ROUTE'}
    return best

def for_turn(store,text,session):
    """(route or None, info). route is set only in active mode."""
    md=mode(store)
    if md=='off':return None,None
    s=suggest(store,text,session)
    if not s:return None,None
    s['mode']=md;s['applied']=md=='active'
    return (s['route'] if s['applied'] else None),s
