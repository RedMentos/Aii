"""WP-T8 §7.2.1 / §7.2.2 control-grounded world model with action coverage and counterfactual confidence.

A small CPU model over V13's own observed digital transitions (actions table + ActionSelection route):
  state s     log input length, resource pressure at selection, hour-of-day phase
  action a    the C5 route that was taken (simple|detail|gist|both)
  next y      log1p(duration), success (FINAL), log1p(output chars)
Four separate objectives (§7.2.1), each reported on a held-out split:
  forward     (s, a) -> y            ridge, bootstrap ensemble of ENSEMBLE fits (spread = model disagreement)
  inverse     (s, y) -> a            ridge one-vs-rest; a representation/control signal, NOT a causal claim
  state-align latent -> y            linear probe from the learned latent world prediction when one exists,
                                     else UNAVAILABLE (no invented latent)
  outcome     predicted y vs actual  mean absolute error per target
Coverage (§7.2.2) per query: samples for that action, OOD distance of s to that action's states (in units of
their median nearest-neighbour distance), ensemble spread, cause tag SELF_CAUSED (all digital actions are own),
and counterfactual confidence in [0,1]. Low coverage -> label SIMULATION_UNCERTAIN; a counterfactual is never REAL.
"""
import json
import math
import numpy as np
from .common import now
from .world import _unique_world_object

def _t8_source_object(raw):
    """Reject duplicate JSON keys without changing legacy optional-latent admission.

    Authoritative numeric forecast/outcome fields are checked by T8 below.
    An invalid optional latent may still be ignored while the observed
    action transition is retained, as required by existing T8 regressions.
    """
    obj=json.loads(raw,object_pairs_hook=_unique_world_object)
    if type(obj) is not dict:raise ValueError('T8 source object required')
    return obj

KEY='T8_WORLD_MODEL';REVISION='t8-world-model-v3'
SOURCE_ADMISSION='T8_JSON_UNIQUE_KEYS_V1'  # v1 leaked heldout support; v2 accepted provisional C5 predictions; refit required
ACTIONS=('simple','detail','gist','both')
TARGETS=('log_duration','success','log_chars')
RIDGE=1e-2;ENSEMBLE=5;MIN_FIT=8;MAX_ROWS=2048
COVER_N=8.        # BOOT: samples per action for ~63 % of the coverage term
SPREAD_REF=.25    # BOOT: ensemble spread that halves confidence
CF_MIN=.5         # BOOT: below this a counterfactual is SIMULATION_UNCERTAIN
OOD_SUPPORT=2.    # BOOT: nearest-neighbour distance (in median-NN units) still inside the action's support
PRESSURE={'NORMAL':0.,'RECOVERY':.5,'UNKNOWN':.5,'PRESSURE':1.,'CRITICAL':1.}

def state_vec(input_chars,resource_state='NORMAL',hour=12.):
    h=2*math.pi*float(hour)/24
    return [math.log1p(max(0,float(input_chars)))/8,PRESSURE.get(resource_state,.5),math.sin(h),math.cos(h)]
def onehot(a):return [1. if a==x else 0. for x in ACTIONS]

def _finite_nonnegative(v):
    return type(v) in (int,float) and math.isfinite(v) and v>=0

def _finite_vector(v,dim):
    if not isinstance(v,(list,tuple,np.ndarray)) or len(v)!=dim:return False
    for x in v:
        # NumPy complex scalars may silently discard their imaginary part on
        # float conversion; only finite real evidence may reach a model.
        if isinstance(x,(bool,np.bool_,complex,np.complexfloating)) or not isinstance(x,(int,float,np.number)):
            return False
        try:
            if not math.isfinite(float(x)):return False
        except (TypeError,ValueError,OverflowError):
            return False
    return True

def transitions(store,limit=MAX_ROWS):
    """Observed own transitions; malformed or nonfinite legacy rows cannot poison a fit."""
    rows=store.rows("SELECT a.id,a.event_id,a.status,a.expected,a.outcome,a.created,e.generation_id FROM actions a JOIN events e ON e.id=a.event_id WHERE a.outcome IS NOT NULL AND a.expected LIKE ? ORDER BY a.created DESC LIMIT ?",('%"forecast"%',limit))
    out=[]
    for r in rows:
        try:
            exp=_t8_source_object(r['expected']);act=_t8_source_object(r['outcome'])
            if type(exp) is not dict or type(act) is not dict:continue
            fc=exp.get('forecast')
            if type(fc) is not dict:continue
            chars=act.get('characters')
            chars=0 if chars is None else chars
            if (not _finite_nonnegative(fc.get('input_chars'))
                    or not _finite_nonnegative(act.get('action_duration_s'))
                    or not _finite_nonnegative(chars)
                    or not _finite_nonnegative(r['created'])):continue
            resource=fc.get('resource_state','NORMAL')
            if type(resource) is not str:continue
            # C5 can emit provisional PREDICTION packets before its COMMIT.
            # Only a unique committed (or legacy unstaged) selection may label
            # an actual action. Preserve the dispatch-time and generation
            # binding; reject saturated scans rather than hiding an ambiguity.
            sel=store.rows("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? AND generation_id=? AND created<=? ORDER BY created DESC LIMIT 17",
                           (r['event_id'],r['generation_id'],r['created']))
            if len(sel)>=17:continue
            committed=[]
            for candidate in sel:
                selected=_t8_source_object(candidate['payload'])
                if (type(selected) is not dict
                        or selected.get('event_id')!=r['event_id']
                        or selected.get('brain_generation_id')!=r['generation_id']):
                    raise ValueError('INVALID_ACTION_SELECTION_SOURCE')
                stage=selected.get('stage')
                if stage not in (None,'PREDICTION','COMMIT'):
                    raise ValueError('UNKNOWN_ACTION_SELECTION_STAGE')
                if stage!='PREDICTION':
                    committed.append(selected)
            if len(committed)!=1:continue
            payload=committed[0]
            route=payload.get('route_hint')
            if route not in ACTIONS:continue
            hour=(r['created']%86400)/3600
            lat=(fc.get('learned_latent_prediction') or {})
            lat=lat.get('latent') if type(lat) is dict else None
            if not isinstance(lat,list) or not lat or not _finite_vector(lat,len(lat)):lat=None
            out.append({'action_id':r['id'],'s':state_vec(fc['input_chars'],resource,hour),'a':route,
                        'y':[math.log1p(act['action_duration_s']),1. if r['status']=='FINAL' else 0.,math.log1p(chars)/8],
                        'latent':lat})
        except (ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError):
            # Corrupt/legacy observations are not training evidence.
            continue
    return list(reversed(out))

def ridge(X,Y,lam=RIDGE):
    X=np.asarray(X,float);Y=np.asarray(Y,float);A=X.T@X+lam*np.eye(X.shape[1])
    return np.linalg.solve(A,X.T@Y)

def _split(n):
    """Deterministic hashed 1-in-4 hold-out (a plain i%4 split can align with periodic action patterns)."""
    test=[i for i in range(n) if ((i*2654435761)%2**32>>16)%4==3];return [i for i in range(n) if i not in set(test)],test

def fit(store,rng_seed=0):
    """Fit all four objectives from stored transitions; persist parameters + held-out metrics."""
    T=transitions(store);n=len(T)
    st={'revision':REVISION,'source_admission':SOURCE_ADMISSION,'fitted':now(),'n':n,'counts':{a:sum(t['a']==a for t in T) for a in ACTIONS},'status':'TOO_FEW_TRANSITIONS'}
    if n<MIN_FIT:store.set_state(KEY,st);return st
    S=np.array([t['s'] for t in T]);A=np.array([onehot(t['a']) for t in T]);Y=np.array([t['y'] for t in T])
    Xf=np.hstack([np.ones((n,1)),S,A]);tr,te=_split(n);rng=np.random.default_rng(rng_seed)
    fw=[ridge(Xf[idx],Y[idx]) for idx in (rng.choice(tr,len(tr)) for _ in range(ENSEMBLE))]
    pred=np.mean([Xf[te]@W for W in fw],0);mae=np.abs(pred-Y[te]).mean(0)
    base=np.abs(Y[tr].mean(0)-Y[te]).mean(0)
    Xi=np.hstack([np.ones((n,1)),S,Y]);Wi=ridge(Xi[tr],A[tr])
    inv_acc=float((np.argmax(Xi[te]@Wi,1)==np.argmax(A[te],1)).mean()) if te else None
    # Freeze the majority action using training labels only, then score that
    # one fixed classifier on held-out actions. The all-row frequency leaks
    # held-out labels into the baseline and is not comparable to inv_acc.
    train_majority=max(ACTIONS,key=lambda a:sum(T[i]['a']==a for i in tr))
    major=sum(T[i]['a']==train_majority for i in te)/len(te)
    align={'status':'UNAVAILABLE','reason':'no learned latent world prediction stored with these actions'}
    L=[t['latent'] for t in T];dims={len(l) for l in L if l}
    if all(l is not None for l in L) and len(dims)==1:
        Xl=np.hstack([np.ones((n,1)),np.array(L,float)]);Wl=ridge(Xl[tr],Y[tr],1.)
        res=((Xl[te]@Wl-Y[te])**2).sum(0);tot=((Y[te]-Y[tr].mean(0))**2).sum(0)+1e-12
        align={'status':'MEASURED','r2':dict(zip(TARGETS,[round(float(1-a/b),4) for a,b in zip(res,tot)]))}
    st.update(status='FITTED',forward=[W.tolist() for W in fw],inverse=Wi.tolist(),
              # Coverage is fit on training observations ONLY; held-out rows must
              # not manufacture support for their own action or reduce OOD distance.
              states={a:[T[i]['s'] for i in tr if T[i]['a']==a][-256:] for a in ACTIONS},
              support_counts={a:min(256,sum(T[i]['a']==a for i in tr)) for a in ACTIONS},
              train_counts={a:sum(T[i]['a']==a for i in tr) for a in ACTIONS},
              support_scope='TRAIN_SPLIT_ONLY_HELDOUT_EXCLUDED',
              metrics={'forward_mae':dict(zip(TARGETS,np.round(mae,4).tolist())),'forward_baseline_mae':dict(zip(TARGETS,np.round(base,4).tolist())),
                       'inverse_accuracy':None if inv_acc is None else round(inv_acc,4),'inverse_majority_baseline':round(major,4),
                       'inverse_note':'representation/control signal, not a causal claim','state_align':align,'held_out':len(te)})
    store.set_state(KEY,st);store.log('world_model_fit',None,{'n':n,'status':'FITTED'})
    return st

def load(store):
    st=store.state(KEY,None)[0]
    return st if st and st.get('revision')==REVISION and st.get('source_admission')==SOURCE_ADMISSION else None

def coverage(st,s,a):
    if not _finite_vector(s,4):return {'samples':0,'ood_distance':None,'in_support':False,'invalid':True}
    raw=st.get('states',{}).get(a) if type(st.get('states')) is dict else None
    if not isinstance(raw,list) or any(not _finite_vector(p,4) for p in raw):
        return {'samples':0,'ood_distance':None,'in_support':False,'invalid':True}
    pts=np.asarray(raw,float);n=len(raw)
    if n==0:return {'samples':0,'ood_distance':None,'in_support':False}
    d=np.sqrt(((pts-np.asarray(s,float))**2).sum(1));nearest=float(d.min())
    if n>=2:
        dd=np.sqrt(((pts[:,None,:]-pts[None,:,:])**2).sum(2));np.fill_diagonal(dd,np.inf);scale=float(np.median(dd.min(1)))
    else:scale=0.
    ood=nearest/max(scale,1e-3)
    if not math.isfinite(ood):
        return {'samples':0,'ood_distance':None,'in_support':False,'invalid':True}
    return {'samples':n,'ood_distance':round(ood,4),'in_support':ood<=OOD_SUPPORT}

def _invalid_numeric(a):
    return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN',
            'reason':'INVALID_NUMERIC_EVIDENCE','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}

def counterfactual(store,s,a,st=None):
    """Predicted consequence of action a in state s; invalid evidence cannot create confidence."""
    st=st or load(store)
    if a not in ACTIONS:raise ValueError('Aktion '+'|'.join(ACTIONS))
    if not st or st.get('revision')!=REVISION or st.get('source_admission')!=SOURCE_ADMISSION or st.get('status')!='FITTED':
        return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN','reason':'NO_WORLD_MODEL','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    if not _finite_vector(s,4) or st.get('support_scope')!='TRAIN_SPLIT_ONLY_HELDOUT_EXCLUDED':
        return _invalid_numeric(a)
    try:
        weights=np.asarray(st.get('forward'),float)
    except (ValueError,TypeError,OverflowError):
        return _invalid_numeric(a)
    if weights.shape!=(ENSEMBLE,1+4+len(ACTIONS),len(TARGETS)) or not np.isfinite(weights).all():
        return _invalid_numeric(a)
    cov=coverage(st,s,a)
    support=st.get('support_counts')
    if cov.get('invalid') or type(support) is not dict or support.get(a)!=cov['samples']:
        return _invalid_numeric(a)
    x=np.asarray([1.]+list(s)+onehot(a),float)
    preds=np.asarray([x@W for W in weights])
    if not np.isfinite(preds).all():return _invalid_numeric(a)
    mean=preds.mean(0);spread=float(preds.std(0).mean())
    if not np.isfinite(mean).all() or not math.isfinite(spread):return _invalid_numeric(a)
    # Training targets are log1p(nonnegative duration/chars) and binary success.
    # A finite ridge extrapolation outside that domain is not a valid forecast.
    if mean[0]<0 or mean[2]<0 or not 0<=mean[1]<=1:
        # Preserve the measured train-only support diagnostic even when the
        # extrapolated outcome is impossible; no predicted values gain authority.
        return _invalid_numeric(a)|{'coverage':cov}
    ood=cov['ood_distance'] if cov['ood_distance'] is not None else 1e9
    conf=(1-math.exp(-cov['samples']/COVER_N))*math.exp(-max(0.,ood-OOD_SUPPORT))/(1+spread/SPREAD_REF)
    if not math.isfinite(conf):return _invalid_numeric(a)
    try:duration=math.expm1(float(mean[0]))
    except OverflowError:return _invalid_numeric(a)
    if not math.isfinite(duration):return _invalid_numeric(a)
    conf=round(max(0.,min(1.,conf)),4)
    return {'action':a,'prediction':dict(zip(TARGETS,np.round(mean,4).tolist()))|{'duration_s':round(duration,3)},
            'coverage':cov,'model_spread':round(spread,4),'confidence':conf,'cause':'SELF_CAUSED','authority':'HYPOTHESIS',
            'label':'SIMULATION_SUPPORTED' if conf>=CF_MIN and cov['in_support'] else 'SIMULATION_UNCERTAIN'}

def for_event(store,event_id,a):
    """Counterfactual for a stored event; never invent an observed state from corrupt input."""
    row=store.one("SELECT expected,created FROM actions WHERE event_id=? AND expected LIKE ? ORDER BY created DESC LIMIT 1",(event_id,'%"forecast"%'))
    if not row:return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN','reason':'NO_OBSERVED_STATE','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    try:
        expected=_t8_source_object(row['expected'])
        fc=expected.get('forecast') if type(expected) is dict else None
        if (type(fc) is not dict or not _finite_nonnegative(fc.get('input_chars'))
                or not _finite_nonnegative(row['created'])):
            raise ValueError('invalid recorded forecast')
        resource=fc.get('resource_state','NORMAL')
        if type(resource) is not str:raise ValueError('invalid resource state')
        s=state_vec(fc['input_chars'],resource,(row['created']%86400)/3600)
    except (ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError):
        return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN',
                'reason':'INVALID_OBSERVED_STATE','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    return counterfactual(store,s,a)

def report(store):
    st=load(store)
    if not st:return {'revision':REVISION,'status':'NOT_FITTED'}
    return {k:st.get(k) for k in ('revision','status','n','counts','fitted','metrics')}|{'claim_limit':'Own digital transitions only; prediction is not causality; counterfactuals stay simulations'}
