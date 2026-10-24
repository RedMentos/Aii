"""WP-U1 JEF learns control from outcomes (§3.3.8: distilled packet targets) and the experience lifecycle (§14.6, §24.32).

Outcome labels: after a FINAL turn the fast heads get the action the outcome supports, for their stored decision:
  wake    which bodies' offers actually reached the coalition (none / detail / gist / both), only when bodies were woken
  memory  recalled memories reached the coalition -> recall; none did -> skip; a second (attended) recall did -> deep
  skill   a skill-routed turn that held -> skill; a later route correction that disagrees flips it to none
Authority OUTCOME_SELF_LABEL sits below explicit human labels (evidence hierarchy): it never overrides a human label for
the same context and enters :learn only after `:fastpolicy outcomes learn` (default record). Agreement with human labels
is measured where both exist, so the user sees whether self-labels are trustworthy before allowing them.

Lifecycle L0-L11: a read model per experience from existing traces (no new authority, no writes).
"""
import json

KEY='JEF_OUTCOME_LABELS';MAX=1024;MODES=('record','learn');AUTHORITY='OUTCOME_SELF_LABEL'

def _decision(store,eid,component):
    row=store.one("SELECT payload FROM packets WHERE kind='ExecutiveDecision' AND event_id=? AND json_extract(payload,'$.component')=? ORDER BY rowid DESC LIMIT 1",(eid,component))
    return json.loads(row['payload']) if row else None

def _mutate(store,fn):
    for attempt in (0,1):
        st,v=store.state(KEY);st=st or {'mode':'record','labels':[]};out=fn(st)
        try:store.set_state(KEY,st,expected=v);return out
        except ValueError:
            if attempt:raise

def mode(store):return (store.state(KEY)[0] or {}).get('mode','record')

def set_mode(store,m):
    if m not in MODES:raise ValueError(':fastpolicy outcomes record|learn')
    _mutate(store,lambda st:st.__setitem__('mode',m));return m

def targets(meta,coalition,memory_ids):
    """Pure derivation of outcome targets from one turn (component -> value)."""
    out={};roles={x.get('source_kind') for x in coalition}
    woken=(meta.get('wake_decision') or {}).get('action')
    if woken and woken!='none':
        b1,b2='B1_DETAIL' in roles,'B2_GIST' in roles
        out['wake']={(False,False):'none',(True,False):'detail',(False,True):'gist',(True,True):'both'}[(b1,b2)]
    if memory_ids:
        mem=[x['item_id'] for x in coalition if x.get('source_kind')=='MEMORY']
        out['memory']='deep' if any(m not in memory_ids for m in mem) else ('recall' if mem else 'skip')
    if (meta.get('skill') or {}).get('name') and not (meta.get('skill') or {}).get('vetoed_by'):out['skill']='skill'
    return out

def after_turn(r,e,meta,status,focal_run):
    """Record outcome labels for the head decisions of a FINAL turn (never changes the answer)."""
    if status!='FINAL' or not focal_run:return {}
    try:
        t=targets(meta,focal_run.get('coalition') or [],meta.get('memory_ids') or [])
        retained=(r.store.state(KEY)[0] or {}).get('labels',[])
        seen={(x['event_id'],x['component']) for x in retained}
        rows=[]
        for comp,value in t.items():
            if (e['event_id'],comp) in seen:continue  # no duplicate source creation on normal replay
            d=_decision(r.store,e['event_id'],comp)
            if not d:continue
            ref=r.store.source(value,AUTHORITY)
            rows.append({'event_id':e['event_id'],'component':comp,'value':value,'baseline':d['baseline'],'decision_packet_id':d['packet_id'],
                         'context_sha256':d['context_ref']['sha256'],'context_revision':d['context_revision'],'source_id':ref['source_id']})
        if not rows:return {}
        def f(st):
            existing={(x['event_id'],x['component']) for x in st['labels']}
            fresh=[x for x in rows if (x['event_id'],x['component']) not in existing]
            if fresh:st['labels']=(st['labels']+fresh)[-MAX:]
            return fresh
        committed=_mutate(r.store,f)  # CAS recheck also handles concurrent FINAL callbacks
        if committed:r.store.log('jef_outcome_labels',e['event_id'],{'n':len(committed)})
        return {x['component']:x['value'] for x in committed}
    except Exception as exc:
        r.store.log('jef_outcome_unavailable',e['event_id'],{'error':type(exc).__name__});return {}

def on_route_correction(store,event_id,value):
    """A disagreeing route correction on a skill turn turns its skill outcome label into 'none'."""
    from .agi.live import _load
    if not _load(store,event_id).get('skill'):return 0
    def f(st):
        n=0
        for x in st['labels']:
            if x['event_id']==event_id and x['component']=='skill' and x['value']=='skill':
                x['value']='none';x['source_id']=store.source('none',AUTHORITY)['source_id'];n+=1
        return n
    return _mutate(store,f)

def training_rows(store,component,revision,human_keys):
    """Outcome rows for learning.shadow_readout: lower than any human decision."""
    st=store.state(KEY)[0] or {}
    if st.get('mode','record')!='learn':return []
    from .learning import POLICY_LABELS
    allowed=POLICY_LABELS.get(component)
    if not allowed:return []  # no self-label authority for unknown heads
    candidates=[]
    for x in st.get('labels',[]):
        if not isinstance(x,dict) or x.get('component')!=component or x.get('context_revision')!=revision:
            continue
        if x.get('value') not in allowed:continue  # source hashes alone cannot type an action
        if not isinstance(x.get('context_sha256'),str) or x['context_sha256'] in human_keys:
            continue
        candidates.append(x)
    from .jef_human_veto import blocked_human_contexts
    blocked=blocked_human_contexts(store,component,revision,[x['context_sha256'] for x in candidates])
    out={}
    for x in candidates:
        if x['context_sha256'] in blocked:continue
        source_id=x.get('source_id')
        if type(source_id) is not str:continue
        source=store.one('SELECT hash,chars,kind FROM sources WHERE id=? AND deleted=0',(source_id,))
        if not source or source['kind']!=AUTHORITY:continue
        try:
            ref={'source_id':source_id,'sha256':source['hash'],'char_start':0,
                 'char_end':source['chars'],'modality':'text'}
            if store.read_source(ref)!=x.get('value'):continue
        except (ValueError,TypeError,KeyError,OSError,UnicodeError):
            continue
        row=store.one("SELECT payload FROM packets WHERE kind='ExecutiveDecision' AND id=?",(x.get('decision_packet_id'),))
        if not row:continue
        try:
            p=json.loads(row['payload'])
            if not isinstance(p,dict) or p.get('event_id')!=x.get('event_id') or p.get('component')!=component or p.get('context_revision')!=revision or p.get('context_ref',{}).get('sha256')!=x['context_sha256']:
                continue
            context_ref=p.get('context_ref')
            if type(context_ref) is not dict or context_ref not in (p.get('provenance') or []):
                continue
            event=store.one('SELECT packet FROM events WHERE id=?',(x['event_id'],))
            if not event or json.loads(event['packet']).get('source_ref')!=context_ref:
                continue  # fast-head context is the original user event, not a same-hash substitute
            store.read_source(context_ref)  # includes source deletion, blob digest and full extent
            out[x['context_sha256']]=({'value':x['value'],'source_id':x['source_id'],'event_id':x['event_id'],'permission':'learn','authority':AUTHORITY},p)
        except (ValueError,TypeError,KeyError,AttributeError,OSError,UnicodeError):
            continue
    return [(k,row,p) for k,(row,p) in out.items()]

def report(r):
    st=r.store.state(KEY)[0] or {'mode':'record','labels':[]};out={'mode':st.get('mode','record'),'heads':{}}
    for comp in ('wake','memory','skill'):
        labels=[x for x in st.get('labels',[]) if x['component']==comp];agree_h=n_h=0
        for x in labels:
            h=r.store.one("SELECT f.value FROM feedback f JOIN packets p ON p.kind='HumanDecision' AND p.event_id=f.event_id AND json_extract(p.payload,'$.decision_packet_id')=? WHERE f.kind=? ORDER BY f.created DESC LIMIT 1",(x['decision_packet_id'],comp))
            if h:n_h+=1;agree_h+=int(h['value']==x['value'])
        counts={}
        for x in labels:counts[x['value']]=counts.get(x['value'],0)+1
        out['heads'][comp]={'labels':len(labels),'by_value':counts,'differs_from_scaffold':sum(x['value']!=x['baseline'] for x in labels),
                            'human_overlap':n_h,'human_agreement':round(agree_h/n_h,4) if n_h else None}
    out['claim_limit']='Self labels from outcomes, below human labels; used for :learn only in learn mode and only where no human label exists'
    return out

# -- §14.6 experience lifecycle (read model) -------------------------------------------------------------------
STAGES=('L0_CAPTURE','L1_SEGMENT_TAG','L2_COMPARE','L3_CREDIT','L4_UPDATE_PROPOSAL','L5_SHADOW_LEARN','L7_VALIDATE','L9_PROMOTE','L11_REOPEN')

def lifecycle(r,event_id):
    s=r.store;ev=s.one('SELECT id,source_id FROM events WHERE id=?',(event_id,))
    if not ev:raise ValueError('Unbekanntes Ereignis')
    has=lambda kind:bool(s.one('SELECT 1 FROM packets WHERE kind=? AND event_id=? LIMIT 1',(kind,event_id)))
    reached={'L0_CAPTURE':has('ExperienceRecord')}
    reached['L1_SEGMENT_TAG']=reached['L0_CAPTURE'] and bool(s.one("SELECT 1 FROM telemetry WHERE kind IN ('episode_boundary','episode_observed') AND event_id=? LIMIT 1",(event_id,)))
    labels=[x for x in (s.state(KEY)[0] or {}).get('labels',[]) if x['event_id']==event_id]
    reached['L2_COMPARE']=bool(s.one('SELECT 1 FROM feedback WHERE event_id=? LIMIT 1',(event_id,))) or bool(labels) or has('StudentEvaluation')
    reached['L3_CREDIT']=has('LearningTrace') or has('ModulatorPacket')
    srcs=[r_['source_id'] for r_ in s.rows('SELECT source_id FROM feedback WHERE event_id=?',(event_id,))]+[x['source_id'] for x in labels]
    from .jef_lifecycle_sources import matching_updates
    ups=matching_updates(s.rows('SELECT id,status,manifest FROM updates'),srcs) if srcs else []
    reached['L4_UPDATE_PROPOSAL']=bool(ups)
    reached['L5_SHADOW_LEARN']=any(u['status']!='ABORTED' for u in ups)
    reached['L7_VALIDATE']=any(u['status'] in ('PENDING_APPROVAL','EVALUATED_FAIL','APPROVED','ACTIVE','COMMITTED','REJECTED') for u in ups)
    active={v.get('update_id') for v in s.components().values() if isinstance(v,dict)}
    reached['L9_PROMOTE']=any(u['id'] in active for u in ups)
    reached['L11_REOPEN']=any(u['status'] in ('EVALUATED_FAIL','REJECTED','ROLLED_BACK') for u in ups)
    current=next((st for st in reversed(STAGES) if reached.get(st)),None)
    return {'event_id':event_id,'stage':current,'reached':reached,'updates':[{'id':u['id'],'status':u['status']} for u in ups],
            'note':'L6 replay/counterfactual, L8 canary and L10 consolidate have no per-experience trace yet'}

def lifecycle_summary(r,limit=200):
    rows=r.store.rows("SELECT event_id FROM packets WHERE kind='ExperienceRecord' ORDER BY rowid DESC LIMIT ?",(limit,));counts={}
    for x in rows:
        st=lifecycle(r,x['event_id'])['stage'];counts[st]=counts.get(st,0)+1
    return {'experiences':len(rows),'by_stage':counts}
