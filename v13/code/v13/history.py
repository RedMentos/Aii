"""Source-valid native history; retained chat text alone is not new evidence."""
import json
from .common import dumps
from .inputs import looks_like_terminal_log


def native_history(store, session, event_id, turns):
    from .output_policy import validate_rules,QUERY_KIND,ANSWER_KIND
    with store.mutex:
        active=validate_rules(store,store.rules())
        approved={dumps(item['entry'][key]) for item in active for key in ('query_ref','answer_ref')}
    records=store.history(session,2*turns+2) if turns else []
    groups={}
    for row in records:
        if row['event_id']!=event_id and row['role'] in {'user','assistant'}:
            groups.setdefault(row['event_id'],[]).append(row)
    valid=[];dependencies={}
    for eid,rows in groups.items():
        if (len(rows)!=2 or [row['role'] for row in rows]!=['user','assistant'] or
                any(row['status']!='FINAL' or row['session_id']!=session for row in rows)):continue
        # Verify complete event history, not only the bounded tail. A third
        # row might be just outside the history() window.
        count=store.one("SELECT COUNT(*) AS n FROM messages WHERE event_id=? AND session_id=? AND role IN ('user','assistant')",(eid,session))
        if not count or count['n']!=2:continue
        try:
            event=store.one('SELECT packet,session_id FROM events WHERE id=?',(eid,))
            if not event or event['session_id']!=session:continue
            # WP-V5: pasted terminal logs are not carried into later model context.
            if any(row['role']=='user' and looks_like_terminal_log(row['text']) for row in rows):continue
            refs=[json.loads(event['packet'])['source_ref']]
            # Current Store.event writes user text and its source_ref together.
            # Retained chat text must match the verified source, not merely
            # point at some other valid source blob.
            user_ref=json.loads(rows[0]['metadata'])['source_ref']
            if dumps(user_ref)!=dumps(refs[0]) or store.read_source(refs[0])!=rows[0]['text']:
                raise ValueError('History user text/source lineage mismatch')
            for row in rows:
                if row['role']!='assistant':continue
                meta=json.loads(row['metadata'])
                if 'context_source_refs' in meta:refs.extend(meta['context_source_refs'])
                else:
                    old=store.one("SELECT payload FROM packets WHERE kind='OutputAdapterContext' AND event_id=? ORDER BY created DESC LIMIT 1",(eid,))
                    if old:refs.extend(json.loads(old['payload'])['provenance'])
                    elif not meta.get('direct_source_copy'):raise ValueError('Legacy answer has no recoverable input lineage')
            for ref in refs:
                store.read_source(ref)
                source=store.one('SELECT kind FROM sources WHERE id=?',(ref['source_id'],))
                if source['kind'] in {QUERY_KIND,ANSWER_KIND} and dumps(ref) not in approved:
                    raise ValueError('History depends on a removed or replaced fixed-answer source')
        except (ValueError,KeyError,TypeError,OSError):continue
        valid.extend(rows);dependencies[eid]=refs
    selected=valid[-2*turns:]
    # Keep complete pairs when the bounded query begins inside an old turn.
    selected=[row for row in selected if sum(x['event_id']==row['event_id'] for x in selected)==2]
    refs=list({dumps(ref):ref for row in selected for ref in dependencies[row['event_id']]}.values())
    return selected,refs
