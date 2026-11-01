"""WP-U8 L3-B4 workspace stability loop: the workspace learns which slots are worth holding, not knowledge.

Observed per finished turn (focal.Workspace.save), per source kind (B1_DETAIL, B2_GIST, MEMORY):
  refresh   a slot carried over from an earlier turn (turns_retained >= 1) ends ACTIVE again -> useful hold (1),
            carried over but not admitted -> wasted hold (0); EMA v_refresh
  restore   a freshly admitted slot whose payload had been dropped from the workspace before -> restore loss (1),
            other fresh admissions (0); EMA r_restore
  loss      a stored slot whose source can no longer be read is counted as SOURCE_LOSS and never kept
            (L_B4_SOURCE_LOSS locked high: provenance beats stability)
Hold multiplier per kind after MIN_N observations:
  m = 1 + L_B4_REFRESH x (v_refresh - .5) + L_B4_ADMISSION x r_restore, bounded to [MULT_MIN, MULT_MAX]
In ACTIVE (`:workspace active`, explicit human) Workspace.load multiplies the per-turn decay of that kind by m
(capped at 1); SHADOW only records it. L_B4_BINDING has no learned use here (not claimed).
"""
from .common import dumps

KEY='B4_WORKSPACE_LEARN';REVISION='b4-workspace-learn-v1'
L={'admission':.5,'refresh':.5,'source_loss':1.}  # BOOT ENG: blueprint marks L_B4_* [TUNE] without values; source loss LOCKED high
RATE=.1;MIN_N=10;MULT_MIN=.5;MULT_MAX=1.5;DROPPED_MAX=64

def empty():return {'revision':REVISION,'mode':'SHADOW','kinds':{},'dropped':[],'source_loss':0}

def _load(store):
    st,v=store.state(KEY,None)
    return (st if st and st.get('revision')==REVISION else empty()),v

def _kind(st,k):return st['kinds'].setdefault(k,{'n_retained':0,'n_fresh':0,'v_refresh':.5,'r_restore':0.,'used':0,'restored':0})

def multiplier(q):
    if q is None or q['n_retained']+q['n_fresh']<MIN_N:return 1.
    m=1+L['refresh']*(q['v_refresh']-.5)+L['admission']*q['r_restore']
    return round(min(MULT_MAX,max(MULT_MIN,m)),4)

def observe(store,active,rest,kept,old_slots):
    """One turn. active/rest: focal items of this turn; kept: slots saved now; old_slots: slots saved last turn."""
    st,v=_load(store);dropped={d['ref'] for d in st['dropped']}
    for x in active+rest:
        q=_kind(st,x['source_kind']);on=x['state_type']=='ACTIVE'
        if x.get('turns_retained',0)>=1:
            q['n_retained']+=1;q['used']+=int(on);q['v_refresh']=round(q['v_refresh']+RATE*((1. if on else 0.)-q['v_refresh']),6)
        elif on:
            hit=x['payload_ref'] in dropped
            q['n_fresh']+=1;q['restored']+=int(hit);q['r_restore']=round(q['r_restore']+RATE*((1. if hit else 0.)-q['r_restore']),6)
    keep={s['payload_ref'] for s in kept}
    st['dropped']=([d for d in st['dropped'] if d['ref'] not in keep]+[{'ref':s['payload_ref'],'kind':s['source_kind']} for s in old_slots if s['payload_ref'] not in keep])[-DROPPED_MAX:]
    store.set_state(KEY,st,expected=v)
    return {k:multiplier(q) for k,q in st['kinds'].items()}

def source_loss(store):
    st,v=_load(store);st['source_loss']+=1;store.set_state(KEY,st,expected=v)

def decay_factor(store,kind):
    """Multiplier for one kind's per-turn decay; 1.0 in SHADOW."""
    st,_=_load(store)
    return multiplier(st['kinds'].get(kind)) if st['mode']=='ACTIVE' else 1.

def set_mode(store,mode,authority='SYSTEM'):
    if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
    if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
    st,v=_load(store);st['mode']=mode;store.set_state(KEY,st,expected=v);store.log('workspace_learn_mode',None,{'mode':mode,'authority':authority});return mode

def report(store):
    st,_=_load(store)
    return {'revision':REVISION,'mode':st['mode'],'kinds':{k:dict(q,multiplier=multiplier(q)) for k,q in st['kinds'].items()},
            'dropped_tracked':len(st['dropped']),'source_loss':st['source_loss'],'weights':L,
            'claim_limit':'Learns how long workspace slots are held per source kind; never content, truth or source binding'}

def operator_command(r,args):
    """:workspace [status|shadow|active]"""
    if not args or args==['status']:return dumps(report(r.store))
    if args==['shadow']:return dumps({'mode':set_mode(r.store,'SHADOW')})
    if args==['active']:return dumps({'mode':set_mode(r.store,'ACTIVE','EXPLICIT_HUMAN')})
    raise ValueError(':workspace [status|shadow|active]')
