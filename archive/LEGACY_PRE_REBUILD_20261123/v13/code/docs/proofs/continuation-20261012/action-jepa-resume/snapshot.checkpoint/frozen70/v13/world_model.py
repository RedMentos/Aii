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

KEY='T8_WORLD_MODEL';REVISION='t8-world-model-v1'
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

def transitions(store,limit=MAX_ROWS):
    """Observed own transitions with a forecast and an outcome; the route comes from the committed ActionSelection."""
    rows=store.rows("SELECT a.id,a.event_id,a.status,a.expected,a.outcome,a.created FROM actions a WHERE a.outcome IS NOT NULL AND a.expected LIKE ? ORDER BY a.created DESC LIMIT ?",('%"forecast"%',limit))
    out=[]
    for r in rows:
        exp=json.loads(r['expected']);fc=exp.get('forecast') or {};act=json.loads(r['outcome'] or '{}')
        sel=store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1",(r['event_id'],))
        route=json.loads(sel['payload']).get('route_hint') if sel else None
        if route not in ACTIONS or not isinstance(fc.get('input_chars'),(int,float)) or not isinstance(act.get('action_duration_s'),(int,float)):continue
        hour=(r['created']%86400)/3600
        lat=(fc.get('learned_latent_prediction') or {}).get('latent')
        out.append({'action_id':r['id'],'s':state_vec(fc['input_chars'],fc.get('resource_state','NORMAL'),hour),'a':route,
                    'y':[math.log1p(act['action_duration_s']),1. if r['status']=='FINAL' else 0.,math.log1p(act.get('characters') or 0)/8],
                    'latent':lat if isinstance(lat,list) and lat and all(isinstance(v,(int,float)) for v in lat) else None})
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
    st={'revision':REVISION,'fitted':now(),'n':n,'counts':{a:sum(t['a']==a for t in T) for a in ACTIONS},'status':'TOO_FEW_TRANSITIONS'}
    if n<MIN_FIT:store.set_state(KEY,st);return st
    S=np.array([t['s'] for t in T]);A=np.array([onehot(t['a']) for t in T]);Y=np.array([t['y'] for t in T])
    Xf=np.hstack([np.ones((n,1)),S,A]);tr,te=_split(n);rng=np.random.default_rng(rng_seed)
    fw=[ridge(Xf[idx],Y[idx]) for idx in (rng.choice(tr,len(tr)) for _ in range(ENSEMBLE))]
    pred=np.mean([Xf[te]@W for W in fw],0);mae=np.abs(pred-Y[te]).mean(0)
    base=np.abs(Y[tr].mean(0)-Y[te]).mean(0)
    Xi=np.hstack([np.ones((n,1)),S,Y]);Wi=ridge(Xi[tr],A[tr])
    inv_acc=float((np.argmax(Xi[te]@Wi,1)==np.argmax(A[te],1)).mean()) if te else None
    major=max(st['counts'].values())/n
    align={'status':'UNAVAILABLE','reason':'no learned latent world prediction stored with these actions'}
    L=[t['latent'] for t in T];dims={len(l) for l in L if l}
    if all(l is not None for l in L) and len(dims)==1:
        Xl=np.hstack([np.ones((n,1)),np.array(L,float)]);Wl=ridge(Xl[tr],Y[tr],1.)
        res=((Xl[te]@Wl-Y[te])**2).sum(0);tot=((Y[te]-Y[tr].mean(0))**2).sum(0)+1e-12
        align={'status':'MEASURED','r2':dict(zip(TARGETS,[round(float(1-a/b),4) for a,b in zip(res,tot)]))}
    st.update(status='FITTED',forward=[W.tolist() for W in fw],inverse=Wi.tolist(),
              states={a:[t['s'] for t in T if t['a']==a][-256:] for a in ACTIONS},
              metrics={'forward_mae':dict(zip(TARGETS,np.round(mae,4).tolist())),'forward_baseline_mae':dict(zip(TARGETS,np.round(base,4).tolist())),
                       'inverse_accuracy':None if inv_acc is None else round(inv_acc,4),'inverse_majority_baseline':round(major,4),
                       'inverse_note':'representation/control signal, not a causal claim','state_align':align,'held_out':len(te)})
    store.set_state(KEY,st);store.log('world_model_fit',None,{'n':n,'status':'FITTED'})
    return st

def load(store):
    st=store.state(KEY,None)[0]
    return st if st and st.get('revision')==REVISION else None

def coverage(st,s,a):
    pts=np.array(st['states'].get(a) or [],float);n=len(pts)
    if n==0:return {'samples':0,'ood_distance':None,'in_support':False}
    d=np.sqrt(((pts-np.array(s))**2).sum(1));nearest=float(d.min())
    if n>=2:
        dd=np.sqrt(((pts[:,None,:]-pts[None,:,:])**2).sum(2));np.fill_diagonal(dd,np.inf);scale=float(np.median(dd.min(1)))
    else:scale=0.
    ood=nearest/max(scale,1e-3)
    return {'samples':n,'ood_distance':round(ood,4),'in_support':ood<=OOD_SUPPORT}

def counterfactual(store,s,a,st=None):
    """Predicted consequence of action a in state s, with coverage, model disagreement and a confidence label."""
    st=st or load(store)
    if a not in ACTIONS:raise ValueError('Aktion '+'|'.join(ACTIONS))
    if not st or st.get('status')!='FITTED':
        return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN','reason':'NO_WORLD_MODEL','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    x=np.array([1.]+list(s)+onehot(a));preds=np.array([x@np.array(W) for W in st['forward']])
    mean=preds.mean(0);spread=float(preds.std(0).mean());cov=coverage(st,s,a)
    ood=cov['ood_distance'] if cov['ood_distance'] is not None else 1e9
    conf=(1-math.exp(-cov['samples']/COVER_N))*math.exp(-max(0.,ood-OOD_SUPPORT))/(1+spread/SPREAD_REF)
    conf=round(max(0.,min(1.,conf)),4)
    return {'action':a,'prediction':dict(zip(TARGETS,np.round(mean,4).tolist()))|{'duration_s':round(math.expm1(float(mean[0])),3)},
            'coverage':cov,'model_spread':round(spread,4),'confidence':conf,'cause':'SELF_CAUSED','authority':'HYPOTHESIS',
            'label':'SIMULATION_SUPPORTED' if conf>=CF_MIN and cov['in_support'] else 'SIMULATION_UNCERTAIN'}

def for_event(store,event_id,a):
    """Counterfactual for a stored event's own state under another action (used by Sleep B route alternatives)."""
    row=store.one("SELECT expected,created FROM actions WHERE event_id=? AND expected LIKE ? ORDER BY created DESC LIMIT 1",(event_id,'%"forecast"%'))
    if not row:return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN','reason':'NO_OBSERVED_STATE','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    fc=json.loads(row['expected']).get('forecast') or {}
    return counterfactual(store,state_vec(fc.get('input_chars',0),fc.get('resource_state','NORMAL'),(row['created']%86400)/3600),a)

def report(store):
    st=load(store)
    if not st:return {'revision':REVISION,'status':'NOT_FITTED'}
    return {k:st.get(k) for k in ('revision','status','n','counts','fitted','metrics')}|{'claim_limit':'Own digital transitions only; prediction is not causality; counterfactuals stay simulations'}
