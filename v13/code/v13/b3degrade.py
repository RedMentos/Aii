"""B3-H10 automatic degradation of LATENT authority + the B3-H11 :doctor fields it feeds (WP-N19).

Canon B3-H10 [LOCKED]: any of ten conditions can demote LATENT authority, along the path

    L4 -> L3 -> L2 -> L1 -> EXACT/SYMBOLIC -> NO_MESSAGE

and demotion requires no architectural rewrite. Here the level is plain persisted state per direction
(store state ``B3_DEGRADE``); every reader (callosum message fields, :doctor, a future latent path via
``allowed``) asks this module, so demoting is one state write.

Triggers, each read from evidence and never from intent. A trigger whose input was never measured reports
NOT_MEASURED: it neither fires nor counts as passed.

  HARD (straight to EXACT/SYMBOLIC; the bridge itself is invalid)
    RECEIVER_REVISION_CHANGED   receiver body model revision differs from the one the level was granted on
    RUNNER_REVISION_CHANGED     native runner binary differs (bin/llama-server content hash)
    CALIBRATION_EXPIRED         no calibration, or older than ``CAL_TTL_S``
    PROJECTOR_COLLAPSED         message effective rank / per-dimension std under the floor
  SOFT (one rung down per check)
    ROUTER_DRIFT                router KL now > max(2 x baseline, baseline + 0.01)
    EXPERT_FLIP_SPIKE           top-k expert flip rate now > max(2 x baseline, baseline + 0.02)
    RETENTION_REGRESSED         role/old-task drop now > baseline + 0.02
    MESSAGE_UTILITY_FELL        latent utility < best simpler channel (EXACT/CONTROL/SYMBOLIC/NO_MESSAGE);
                                on EXACT/SYMBOLIC: every message channel measured below NO_MESSAGE
    COST_OVER_BUDGET            latency over ``LATENCY_BUDGET_MS`` or §97.2 resource mode ORANGE/RED
                                (latent exchange needs both bodies resident; ORANGE allows one)
    ROLE_DIVERSITY_COLLAPSED    B1 and B2 offers on the same events say the same thing (word Jaccard)

Promotion is never automatic into a latent rung: ``promote`` needs the explicit human, a valid
calibration, unchanged revisions, the passed gate of the target rung in the bridge manifest, and moves one
rung. Between NO_MESSAGE and EXACT/SYMBOLIC the level follows the measured channel utilities (that is the
callosum policy's own job; nothing latent is involved).

All thresholds are BOOT values (no measurement yet). Today no bridge passes L1 (WP-J), so every direction
sits on EXACT_SYMBOLIC and LATENT authority stays 0; this module makes the demotion path real for when
one does.
"""
import hashlib
import json
from pathlib import Path
import re
import time
from .common import dumps

KEY='B3_DEGRADE';REVISION='b3-degrade-v1'
LADDER=('L4','L3','L2','L1','EXACT_SYMBOLIC','NO_MESSAGE')
LATENT=LADDER[:4];FALLBACK='EXACT_SYMBOLIC'
RECEIVER={'B1_TO_B2':'B2_GIST','B2_TO_B1':'B1_DETAIL'}
HARD=('RECEIVER_REVISION_CHANGED','RUNNER_REVISION_CHANGED','CALIBRATION_EXPIRED','PROJECTOR_COLLAPSED')
SOFT=('ROUTER_DRIFT','EXPERT_FLIP_SPIKE','RETENTION_REGRESSED','MESSAGE_UTILITY_FELL','COST_OVER_BUDGET','ROLE_DIVERSITY_COLLAPSED')
TRIGGERS=HARD+SOFT
# BOOT thresholds
CAL_TTL_S=7*86400.
DRIFT_FACTOR=2.;ROUTER_KL_ABS=.01;FLIP_ABS=.02;RETENTION_ABS=.02
RANK_FLOOR=1.5;RANK_SHARE=.25;STD_FLOOR=1e-3
LATENCY_BUDGET_MS=250.
DIVERSITY_JACCARD=.8;DIVERSITY_MIN_PAIRS=5;DIVERSITY_WINDOW=20
MIN_N=5;LOG=32
WORD=re.compile(r'\w+')

def empty():
    d=lambda:{'level':FALLBACK,'granted':None,'receiver_revision':None,'runner_revision':None,'baseline':{},'measured':{},'log':[],'last_fail':None}
    return {'revision':REVISION,'dirs':{k:d() for k in RECEIVER}}

def load(store):
    st,v=store.state(KEY,None)
    if st is None:st=empty()
    if st.get('revision')!=REVISION:raise ValueError('B3 degradation state revision mismatch')
    return st,v

def _mutate(store,fn):
    for attempt in (0,1):
        st,v=load(store);out=fn(st);dumps(st)
        try:store.set_state(KEY,st,expected=v);return out
        except ValueError:
            if attempt:raise

def level(store,direction):return load(store)[0]['dirs'][direction]['level']
def latent_level(store,direction):
    lv=level(store,direction);return lv if lv in LATENT else 'unavailable'
def allowed(store,direction,want):
    """Gate for any latent path: is rung ``want`` (or a lower latent rung) permitted right now?"""
    lv=level(store,direction)
    return lv in LATENT and LADDER.index(lv)<=LADDER.index(want)

def step_down(lv,hard=False):
    if hard:return FALLBACK if LADDER.index(lv)<LADDER.index(FALLBACK) else lv
    return LADDER[min(len(LADDER)-1,LADDER.index(lv)+1)]

# -- evidence ----------------------------------------------------------------------------------------------
_RUNNER_CACHE={}
def runner_revision(home):
    """Content hash of the native runner (cached by size+mtime); None without a runner."""
    p=Path(home)/'bin/llama-server'
    try:s=p.stat()
    except OSError:return None
    k=(str(p),s.st_size,s.st_mtime_ns)
    if k not in _RUNNER_CACHE:
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1<<20),b''):h.update(b)
        _RUNNER_CACHE[k]=h.hexdigest()[:16]
    return _RUNNER_CACHE[k]

def manifest(home,direction):
    p=Path(home)/'b3'/f'{direction}.json'
    if not p.exists():return None
    try:return json.loads(p.read_text())
    except Exception:return {'error':'UNREADABLE'}

def _find(d,key):
    """First value of ``key`` at the top level or one dict level down (manifests nest diversity/router reports)."""
    if not isinstance(d,dict):return None
    if d.get(key) is not None:return d[key]
    for v in d.values():
        if isinstance(v,dict) and v.get(key) is not None:return v[key]
    return None

def words(t):return set(WORD.findall((t or '').lower()))
def role_diversity(store,window=DIVERSITY_WINDOW):
    """Mean word Jaccard of B1 vs B2 offer summaries on the same events (latest per role and event)."""
    rows=store.rows("SELECT event_id,json_extract(payload,'$.role') AS role,json_extract(payload,'$.offer.summary') AS s FROM packets "
                    "WHERE kind='OfferPacket' AND json_extract(payload,'$.role') IN ('B1_DETAIL','B2_GIST') ORDER BY rowid DESC LIMIT ?",(window*6,))
    by={}
    for r in rows:by.setdefault(r['event_id'],{}).setdefault(r['role'],r['s'])
    sims=[]
    for x in by.values():
        if len(x)==2:
            a,b=words(x['B1_DETAIL']),words(x['B2_GIST'])
            if a or b:sims.append(len(a&b)/len(a|b))
        if len(sims)>=window:break
    return {'pairs':len(sims),'jaccard':round(sum(sims)/len(sims),4) if sims else None}

def evidence(r,direction,channel_utility=None,now=None):
    """Everything the triggers read, gathered from the runtime (fail-open per field: None = NOT_MEASURED)."""
    now=time.time() if now is None else now;home=Path(r.home);man=manifest(home,direction) or {}
    st=load(r.store)[0]['dirs'][direction];m=st['measured']
    try:rev=(r.revisions() or {}).get(RECEIVER[direction])
    except Exception:rev=None
    try:
        from .resource_modes import mode_of
        mode=mode_of(r.guard)
    except Exception:mode=None
    try:div=role_diversity(r.store)
    except Exception:div={'pairs':0,'jaccard':None}
    g=lambda k:m.get(k) if m.get(k) is not None else _find(man,k)
    return {'receiver_revision':None if rev in (None,'unavailable') else rev,'runner_revision':runner_revision(home),
            'calibrated':bool(man.get('calibrated')),'calibrated_at':man.get('created_wall_time') if man.get('calibrated') else None,'now':now,
            'message_rank':man.get('r'),'message_effective_rank':g('message_effective_rank'),'message_dim_std_min':g('message_dim_std_min'),
            'router_kl':g('router_kl'),'expert_flip':g('topk_flip_rate') if g('expert_flip') is None else g('expert_flip'),
            'retention_drop':g('role_drop') if g('retention_drop') is None else g('retention_drop'),
            'latent_utility':g('latent_utility'),'channel_utility':channel_utility or {},'latency_ms':g('latency_ms'),'resource_mode':mode,
            'role_diversity':div}

# -- triggers ----------------------------------------------------------------------------------------------
def _rise(now,base,factor,absolute):
    if now is None:return None
    if base is None:return False  # no baseline: cannot claim drift (reported, baseline set on grant)
    return now>max(factor*base,base+absolute)

def triggers(st,ev,lv):
    """{trigger: True|False|None(NOT_MEASURED)} for one direction at level ``lv``."""
    b=st['baseline'];out={}
    rr,gr=ev['receiver_revision'],st.get('receiver_revision')
    out['RECEIVER_REVISION_CHANGED']=None if rr is None else (gr is not None and rr!=gr)
    nr,gn=ev['runner_revision'],st.get('runner_revision')
    out['RUNNER_REVISION_CHANGED']=None if nr is None else (gn is not None and nr!=gn)
    if lv in LATENT:out['CALIBRATION_EXPIRED']=not ev['calibrated'] or ev['calibrated_at'] is None or ev['now']-ev['calibrated_at']>CAL_TTL_S
    else:out['CALIBRATION_EXPIRED']=None if not ev['calibrated'] else ev['now']-(ev['calibrated_at'] or 0)>CAL_TTL_S
    er,sd=ev['message_effective_rank'],ev['message_dim_std_min']
    if er is None and sd is None:out['PROJECTOR_COLLAPSED']=None
    else:
        floor=max(RANK_FLOOR,RANK_SHARE*(ev['message_rank'] or 0))
        out['PROJECTOR_COLLAPSED']=(er is not None and er<floor) or (sd is not None and sd<STD_FLOOR)
    out['ROUTER_DRIFT']=_rise(ev['router_kl'],b.get('router_kl'),DRIFT_FACTOR,ROUTER_KL_ABS)
    out['EXPERT_FLIP_SPIKE']=_rise(ev['expert_flip'],b.get('expert_flip'),DRIFT_FACTOR,FLIP_ABS)
    rd=ev['retention_drop'];out['RETENTION_REGRESSED']=None if rd is None else rd>(b.get('retention_drop') or 0.)+RETENTION_ABS
    cu={c:x for c,x in (ev['channel_utility'] or {}).items() if x is not None}
    if lv in LATENT:out['MESSAGE_UTILITY_FELL']=None if ev['latent_utility'] is None or not cu else ev['latent_utility']<max(cu.values())
    else:
        msg=[cu[c] for c in ('SOURCE_EXACT','CONTROL','SYMBOLIC') if c in cu]
        out['MESSAGE_UTILITY_FELL']=None if 'NO_MESSAGE' not in cu or not msg else max(msg)<cu['NO_MESSAGE']
    lat,mode=ev['latency_ms'],ev['resource_mode']
    if lat is None and mode is None:out['COST_OVER_BUDGET']=None
    else:out['COST_OVER_BUDGET']=(lat is not None and lat>LATENCY_BUDGET_MS) or mode in ('ORANGE','RED')
    dv=ev['role_diversity'] or {}
    out['ROLE_DIVERSITY_COLLAPSED']=None if (dv.get('pairs') or 0)<DIVERSITY_MIN_PAIRS or dv.get('jaccard') is None else dv['jaccard']>=DIVERSITY_JACCARD
    return out

def decide(lv,fired):
    """Next rung from the fired triggers. Non-latent rungs: only the utility trigger moves EXACT/SYMBOLIC <-> NO_MESSAGE."""
    if lv in LATENT:
        if any(t in HARD for t in fired):return FALLBACK
        return step_down(lv) if fired else lv
    if lv==FALLBACK and 'MESSAGE_UTILITY_FELL' in fired:return 'NO_MESSAGE'
    return lv

def check(r,channel_utility=None,now=None,log=True):
    """Evaluate every direction, apply demotions, persist. Returns the per-direction report for :doctor."""
    evs={d:evidence(r,d,(channel_utility or {}).get(d),now) for d in RECEIVER};out={}
    def fn(st):
        for d,ev in evs.items():
            x=st['dirs'][d];lv=x['level'];tr=triggers(x,ev,lv);fired=[t for t in TRIGGERS if tr[t]]
            new=decide(lv,fired)
            if lv=='NO_MESSAGE' and tr['MESSAGE_UTILITY_FELL'] is False:new=FALLBACK  # a message channel beats NO_MESSAGE again
            fail=lv in LATENT and tr['CALIBRATION_EXPIRED']
            if fail:x['last_fail']={'wall_time':ev['now'],'level':lv,'reason':'LATENT_ACTIVE_WITHOUT_VALID_CALIBRATION'}
            if new!=lv:x['log']=(x['log']+[{'wall_time':ev['now'],'from':lv,'to':new,'triggers':fired}])[-LOG:]
            if new not in LATENT:x['granted']=None
            x['level']=new
            if x['receiver_revision'] is None or new not in LATENT:x['receiver_revision']=ev['receiver_revision']
            if x['runner_revision'] is None or new not in LATENT:x['runner_revision']=ev['runner_revision']
            out[d]={'level':new,'previous':lv,'fired':fired,'triggers':{t:('NOT_MEASURED' if v is None else bool(v)) for t,v in tr.items()},
                    'status':'FAIL' if fail else 'PASS','calibration_valid':tr['CALIBRATION_EXPIRED'] is False if ev['calibrated'] else False,
                    'receiver_revision':ev['receiver_revision'],'runner_revision':ev['runner_revision'],'resource_mode':ev['resource_mode'],
                    'router_kl':{'baseline':x['baseline'].get('router_kl'),'current':ev['router_kl']},
                    'expert_flip':{'baseline':x['baseline'].get('expert_flip'),'current':ev['expert_flip']},
                    'role_diversity':ev['role_diversity'],'last_fail':x['last_fail'],'demotions':x['log'][-5:]}
    _mutate(r.store,fn)
    if log:
        for d,x in out.items():
            if x['level']!=x['previous']:r.store.log('b3_degraded',None,{'direction':d,'level_from':x['previous'],'level_to':x['level'],'triggers':x['fired']})
    return out

def gate_passed(man,lv):
    """Highest-rung evidence in the bridge manifest: l1_gate, l2_gate, ... with verdict PASS."""
    return bool(((man or {}).get(lv.lower()+'_gate') or {}).get('verdict')=='PASS')

def promote(r,direction,authority='SYSTEM',now=None):
    """One rung up into the latent ladder, only with explicit human authority and all evidence present."""
    if authority!='EXPLICIT_HUMAN':raise PermissionError('LATENT nur per expliziter Nutzerfreigabe (Age 0, B3-H12)')
    ev=evidence(r,direction,now=now);man=manifest(r.home,direction)
    def fn(st):
        x=st['dirs'][direction];lv=x['level']
        if lv=='NO_MESSAGE':raise ValueError('erst EXACT/SYMBOLIC (Nachrichtenkanal schlägt NO_MESSAGE nicht)')
        if lv=='L4':raise ValueError('bereits L4')
        want=LADDER[LADDER.index(lv)-1]
        missing=[k for k,ok in (('CALIBRATION',ev['calibrated'] and ev['calibrated_at'] is not None and ev['now']-ev['calibrated_at']<=CAL_TTL_S),
                                ('RECEIVER_REVISION',ev['receiver_revision'] is not None and (man or {}).get('receiver_revision')==ev['receiver_revision']),
                                ('GATE_'+want,gate_passed(man,want))) if not ok]
        tr=triggers(x,ev,want);fired=[t for t in TRIGGERS if tr[t]]
        if missing or fired:raise ValueError('Beförderung abgelehnt: '+', '.join(missing+fired))
        x.update(level=want,granted={'wall_time':ev['now'],'authority':authority,'level':want},receiver_revision=ev['receiver_revision'],runner_revision=ev['runner_revision'])
        x['baseline']={k:ev[k] for k in ('router_kl','expert_flip','retention_drop') if ev[k] is not None}
        x['log']=(x['log']+[{'wall_time':ev['now'],'from':lv,'to':want,'triggers':['PROMOTED_EXPLICIT_HUMAN']}])[-LOG:]
        return want
    out=_mutate(r.store,fn);r.store.log('b3_promoted',None,{'direction':direction,'level_to':out});return out

def record(store,direction,**metrics):
    """Benches/monitors push measured values (router_kl, expert_flip, retention_drop, latent_utility, latency_ms,
    message_effective_rank, message_dim_std_min); they override the manifest until replaced."""
    ok={'router_kl','expert_flip','retention_drop','latent_utility','latency_ms','message_effective_rank','message_dim_std_min'}
    bad=set(metrics)-ok
    if bad:raise ValueError('unbekannte Messwerte: '+', '.join(sorted(bad)))
    def fn(st):st['dirs'][direction]['measured'].update({k:(None if v is None else float(v)) for k,v in metrics.items()})
    _mutate(store,fn)

def on_receiver_revision(store,direction,revision):
    """Immediate HARD demotion from the message path (callosum.choose) when the receiver revision changes."""
    if revision in (None,'unavailable'):return None
    def fn(st):
        x=st['dirs'][direction];old=x.get('receiver_revision')
        if old is None or old==revision:x['receiver_revision']=revision;return None
        lv=x['level'];x['receiver_revision']=revision
        if lv not in LATENT:return None
        x.update(level=FALLBACK,granted=None);x['log']=(x['log']+[{'wall_time':time.time(),'from':lv,'to':FALLBACK,'triggers':['RECEIVER_REVISION_CHANGED']}])[-LOG:]
        return lv
    lv=_mutate(store,fn)
    if lv:store.log('b3_degraded',None,{'direction':direction,'level_from':lv,'level_to':FALLBACK,'triggers':['RECEIVER_REVISION_CHANGED']})
    return lv
