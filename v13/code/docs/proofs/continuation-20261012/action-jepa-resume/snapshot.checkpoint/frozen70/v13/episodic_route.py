"""WP-U10 §9.1 Fast Episodic, "zweites Mal besser" for routes, without waiting for consolidation.

A single active human route correction (memories.kind='route') on a very similar earlier request is offered as the
route for the next request: relevance (memory.relevance, entity-aware: different named entities -> 0) at least
MIN_RELEVANCE, the newest best match wins. The suggestion carries its episode/source lineage (memory id, event id,
source id). Procedural consolidation (consolidation.route, >= 3 independent confirmations) still runs first and wins.
Mode: off | shadow (default: suggestion recorded in meta.route, scaffold route kept) | active (`:episodes route active`).
"""
from .common import dumps
from .memory import relevance

KEY='U10_EPISODIC_ROUTE';REVISION='u10-episodic-route-v1'
MIN_RELEVANCE=.6   # BOOT: "very similar" request
ROUTES=('simple','detail','gist','both')
LIMIT=256

def mode(store):return (store.state(KEY,None)[0] or {}).get('mode','shadow')

def set_mode(store,m):
    if m not in {'off','shadow','active'}:raise ValueError('off|shadow|active')
    st,v=store.state(KEY,None);st=st or {'revision':REVISION};st['mode']=m;store.set_state(KEY,st,expected=v)
    store.log('episodic_route_mode',None,{'mode':m});return m

def suggest(store,text,session):
    """Best matching active human route correction, or None."""
    best=None
    for m in store.rows("SELECT m.id,m.event_id,m.source_id,m.key_text,m.value,m.created FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.kind='route' AND m.active=1 AND s.deleted=0 AND (m.scope='global' OR m.session_id=?) ORDER BY m.created DESC LIMIT ?",(session,LIMIT)):
        if m['value'] not in ROUTES:continue
        rel=relevance(text,m['key_text'])
        if rel>=MIN_RELEVANCE and (best is None or rel>best['relevance']):
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
