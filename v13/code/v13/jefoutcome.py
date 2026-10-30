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
    """Record each FINAL event/component self-label once; retries preserve later corrections."""
    if status!='FINAL' or not focal_run:return {}
    try:
        t=targets(meta,focal_run.get('coalition') or [],meta.get('memory_ids') or [])
        candidates=[]
        for comp,value in t.items():
            d=_decision(r.store,e['event_id'],comp)
            if not d:continue
            # No source allocation until a missing label has been identified.
            candidates.append({'event_id':e['event_id'],'component':comp,'value':value,
                               'baseline':d['baseline'],'decision_packet_id':d['packet_id'],
                               'context_sha256':d['context_ref']['sha256'],
                               'context_revision':d['context_revision']})
        if not candidates:return {}
        wanted={x['component'] for x in candidates}
        for attempt in (0,1):
            st,v=r.store.state(KEY)
            st=st or {'mode':'record','labels':[]}
            existing={x['component']:x for x in st.get('labels',[])
                      if x['event_id']==e['event_id'] and x['component'] in wanted}
            fresh=[x for x in candidates if x['component'] not in existing]
            if not fresh:
                return {k:x['value'] for k,x in existing.items()}
            # Optimistic CAS prevents duplicate retained labels. In a rare CAS
            # collision an unused source may remain, never an extra label.
            for x in fresh:
                x['source_id']=r.store.source(x['value'],AUTHORITY)['source_id']
            st['labels']=(st.get('labels',[])+fresh)[-MAX:]
            try:r.store.set_state(KEY,st,expected=v)
            except ValueError:
                if attempt:raise
                continue
            r.store.log('jef_outcome_labels',e['event_id'],{'n':len(fresh)})
            existing.update({x['component']:x for x in fresh})
            return {k:x['value'] for k,x in existing.items()}
    except Exception as exc:
        r.store.log('jef_outcome_unavailable',e['event_id'],{'error':type(exc).__name__})
        return {}

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

def _valid_human_receipt(store, feedback, human, decision):
    """Only a live, byte-exact explicit human receipt can outrank a self label.

    Shared with learning.shadow_readout: a matching source_id alone does not
    establish the human value, permission, source kind or decision/event.
    """
    if not isinstance(human, dict) or not isinstance(decision, dict):
        return False
    try:
        if (human.get('kind') != feedback['kind']
                or human.get('value') != feedback['value']
                or human.get('learning_permission') != feedback['permission']
                or human.get('event_id') != feedback['event_id']
                or decision.get('event_id') != feedback['event_id']
                or decision.get('component') != feedback['kind']
                or human.get('decision_packet_id') != decision.get('packet_id')):
            return False
        ref = human.get('source_ref')
        if not isinstance(ref, dict) or ref.get('source_id') != feedback['source_id']:
            return False
        src = store.one('SELECT hash,chars,kind,deleted FROM sources WHERE id=?',
                        (feedback['source_id'],))
        if (not src or src['deleted'] or src['kind'] != 'HUMAN_DECISION'
                or ref.get('sha256') != src['hash']
                or type(ref.get('char_start')) is not int or ref['char_start'] != 0
                or type(ref.get('char_end')) is not int or ref['char_end'] != src['chars']
                or ref.get('modality') != 'text'):
            return False
        return store.read_source(ref) == feedback['value']
    except (ValueError, KeyError, TypeError, OSError, UnicodeError):
        return False


def _human_label_exists(store,component,revision,context_sha256):
    """Require an exact active human receipt, even outside recent-row limits."""
    candidates = store.rows(
        "SELECT f.*, h.payload AS human_payload, d.payload AS decision_payload "
        "FROM feedback f "
        "JOIN sources s ON s.id=f.source_id AND s.deleted=0 "
        " AND s.kind='HUMAN_DECISION' "
        "JOIN packets h ON h.kind='HumanDecision' AND h.event_id=f.event_id "
        " AND json_extract(h.payload,'$.source_ref.source_id')=f.source_id "
        "JOIN packets d ON d.kind='ExecutiveDecision' "
        " AND d.id=json_extract(h.payload,'$.decision_packet_id') "
        " AND d.event_id=f.event_id "
        "WHERE f.kind=? AND json_extract(d.payload,'$.component')=? "
        "AND json_extract(d.payload,'$.context_revision')=? "
        "AND json_extract(d.payload,'$.context_ref.sha256')=? "
        "ORDER BY f.created DESC",
        (component,component,revision,context_sha256))
    for row in candidates:
        try:
            human=json.loads(row['human_payload'])
            decision=json.loads(row['decision_payload'])
        except (TypeError,ValueError):
            continue
        if _valid_human_receipt(store,row,human,decision):
            return True
    return False

def training_rows(store,component,revision,human_keys):
    """Outcome rows for learning.shadow_readout: only in 'learn' mode, only contexts without a human label."""
    st=store.state(KEY)[0] or {}
    if st.get('mode','record')!='learn':return []
    out={};human_cache={}
    for x in st.get('labels',[]):
        if x['component']!=component or x['context_revision']!=revision or x['context_sha256'] in human_keys:continue
        key=x['context_sha256']
        # At most MAX retained self labels are checked. A human RECORD older
        # than the caller's recent 512 rows still vetoes self-label learning.
        if key not in human_cache:
            human_cache[key]=_human_label_exists(store,component,revision,key)
        if human_cache[key]:continue
        # A retained outcome state entry is not training authority by itself.
        # Source revocation or substitution must not reach the optimizer and
        # abort otherwise valid batches at its later read_source check.
        source=store.one("SELECT hash,chars,kind,deleted FROM sources WHERE id=?",
                         (x.get('source_id'),))
        if (not source or source['deleted'] or source['kind']!=AUTHORITY
                or not isinstance(x.get('value'),str)):continue
        ref={'source_id':x['source_id'],'sha256':source['hash'],
             'char_start':0,'char_end':source['chars'],'modality':'text'}
        try:
            if store.read_source(ref)!=x['value']:continue
        except (ValueError,KeyError,TypeError,OSError):continue
        row=store.one("SELECT payload FROM packets WHERE kind='ExecutiveDecision' AND id=?",
                      (x.get('decision_packet_id'),))
        if not row:continue
        try:p=json.loads(row['payload'])
        except (TypeError,ValueError):continue
        context=p.get('context_ref') if isinstance(p,dict) else None
        if (not isinstance(context,dict)
                or p.get('packet_id')!=x.get('decision_packet_id')
                or p.get('event_id')!=x.get('event_id')
                or p.get('component')!=component
                or p.get('context_revision')!=revision
                or context.get('sha256')!=key
                or p.get('baseline')!=x.get('baseline')):continue
        out[key]=({'value':x['value'],'source_id':x['source_id'],
                   'event_id':x['event_id'],'permission':'learn',
                   'authority':AUTHORITY},p)
    return [(k,row,p) for k,(row,p) in out.items()]

def report(r):
    st=r.store.state(KEY)[0] or {'mode':'record','labels':[]};out={'mode':st.get('mode','record'),'heads':{}}
    for comp in ('wake','memory','skill'):
        labels=[x for x in st.get('labels',[]) if x['component']==comp];agree_h=n_h=0
        for x in labels:
            h=r.store.one(
                "SELECT f.value FROM feedback f "
                "JOIN sources src ON src.id=f.source_id AND src.deleted=0 AND src.kind='HUMAN_DECISION' "
                "JOIN packets p ON p.kind='HumanDecision' AND p.event_id=f.event_id "
                "AND json_extract(p.payload,'$.decision_packet_id')=? "
                "AND json_extract(p.payload,'$.source_ref.source_id')=f.source_id "
                "AND json_extract(p.payload,'$.source_ref.sha256')=src.hash "
                "AND json_extract(p.payload,'$.kind')=f.kind "
                "AND json_extract(p.payload,'$.value')=f.value "
                "AND json_extract(p.payload,'$.learning_permission')=f.permission "
                "WHERE f.kind=? ORDER BY f.created DESC LIMIT 1",
                (x['decision_packet_id'],comp))
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
    s=r.store;ev=s.one('SELECT id,source_id FROM events WHERE id=? AND session_id=?',(event_id,r.session))
    if not ev:raise ValueError('CURRENT_SESSION_EVENT_REQUIRED')
    has=lambda kind:bool(s.one('SELECT 1 FROM packets WHERE kind=? AND event_id=? LIMIT 1',(kind,event_id)))
    reached={'L0_CAPTURE':has('ExperienceRecord')}
    reached['L1_SEGMENT_TAG']=reached['L0_CAPTURE'] and bool(s.one("SELECT 1 FROM telemetry WHERE kind IN ('episode_boundary','episode_observed') AND event_id=? LIMIT 1",(event_id,)))
    labels=[x for x in (s.state(KEY)[0] or {}).get('labels',[]) if x['event_id']==event_id]
    reached['L2_COMPARE']=bool(s.one('SELECT 1 FROM feedback WHERE event_id=? LIMIT 1',(event_id,))) or bool(labels) or has('StudentEvaluation')
    reached['L3_CREDIT']=has('LearningTrace') or has('ModulatorPacket')
    srcs=[r_['source_id'] for r_ in s.rows('SELECT source_id FROM feedback WHERE event_id=?',(event_id,))]+[x['source_id'] for x in labels]
    # Update lineage is a typed source-id set, not arbitrary text in a JSON
    # manifest. Free-text notes and longer IDs cannot promote an experience.
    def linked(u):
        try:manifest=json.loads(u['manifest'])
        except (TypeError,ValueError):return False
        ids=manifest.get('source_ids') if isinstance(manifest,dict) else None
        return isinstance(ids,list) and any(isinstance(sid,str) and sid in srcs for sid in ids)
    ups=[u for u in s.rows('SELECT id,status,manifest FROM updates') if linked(u)] if srcs else []
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
    rows=r.store.rows("SELECT p.event_id FROM packets p JOIN events e ON e.id=p.event_id WHERE p.kind='ExperienceRecord' AND e.session_id=? ORDER BY p.rowid DESC LIMIT ?",(r.session,limit));counts={}
    for x in rows:
        st=lifecycle(r,x['event_id'])['stage'];counts[st]=counts.get(st,0)+1
    return {'experiences':len(rows),'by_stage':counts}
