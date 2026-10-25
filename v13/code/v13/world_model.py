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
import hashlib
import json
import math
import sqlite3
import numpy as np
from .common import now

KEY='T8_WORLD_MODEL';REVISION='t8-world-model-sourcebound-v2'
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

def _finite_nonnegative(value):
    return type(value) in (int,float) and math.isfinite(value) and value >= 0


def _valid_observed_event_source(store, event_id):
    """Recheck live EventEnvelope source before treating an action as evidence.

    Production Store has read_source(), which checks deletion, source SHA,
    blob integrity and exact SourceRef bounds. Older minimal SQLite test
    doubles lack that API and retain their legacy *synthetic-only* semantics.
    Fitted-state source lineage is independently checked by load().
    """
    reader = getattr(store, 'read_source', None)
    if reader is None:
        return True  # compatibility for test doubles, never a production grant
    if not callable(reader):
        return False
    try:
        event = store.one("SELECT source_id,packet FROM events WHERE id=?", (event_id,))
        if not event:
            return False
        envelope = json.loads(event['packet'])
        if type(envelope) is not dict:
            return False
        ref = envelope.get('source_ref')
        provenance = envelope.get('provenance')
        if (type(ref) is not dict or ref.get('source_id') != event['source_id']
                or envelope.get('event_id') != event_id
                or envelope.get('kind') != 'USER_TEXT'
                or envelope.get('authority') != 'AUTHORITATIVE'
                or type(provenance) is not list or ref not in provenance):
            return False
        text = reader(ref)
        return isinstance(text, str) and bool(text)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, sqlite3.Error):
        return False


def transitions(store,limit=MAX_ROWS):
    """Only finite, nonnegative observed transitions may enter the world model.

    Malformed historical rows are excluded, not repaired or invented. This
    candidate does not assert that skipped rows are valid evidence.
    """
    rows=store.rows("SELECT a.id,a.event_id,a.status,a.expected,a.outcome,a.created FROM actions a WHERE a.outcome IS NOT NULL AND a.expected LIKE ? ORDER BY a.created DESC LIMIT ?",('%"forecast"%',limit))
    out=[]
    for r in rows:
        if not _valid_observed_event_source(store,r['event_id']):continue
        try:
            exp=json.loads(r['expected']);act=json.loads(r['outcome'] or '{}')
            if type(exp) is not dict or type(act) is not dict:continue
            fc=exp.get('forecast') or {}
            if type(fc) is not dict:continue
            if r['status']=='FINAL':
                profile=fc.get('profile')
                if type(profile) is not dict or type(profile.get('role')) is not str or profile['role']!=act.get('role'):continue
            created=r['created']
            if not _finite_nonnegative(created):continue
            sel=store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? AND created<=? ORDER BY created DESC,rowid DESC LIMIT 1",(r['event_id'],created))
            route=json.loads(sel['payload']).get('route_hint') if sel else None
            if route not in ACTIONS:continue
            chars=fc.get('input_chars');duration=act.get('action_duration_s')
            output_chars=act.get('characters')
            created=r['created']
            # Character counts are observed integers, not optional values to impute.
            # A missing/null/boolean/fractional count cannot become a fabricated zero target.
            if type(chars) is not int or type(output_chars) is not int or chars<0 or output_chars<0:continue
            if not all(_finite_nonnegative(v) for v in (duration,created)):continue
            hour=(created%86400)/3600
            state=state_vec(chars,fc.get('resource_state','NORMAL'),hour)
            if not all(math.isfinite(v) for v in state):continue
            lat=(fc.get('learned_latent_prediction') or {})
            lat=lat.get('latent') if type(lat) is dict else None
            if not (type(lat) is list and 0<len(lat)<=4096 and
                    all(type(v) in (int,float) and math.isfinite(v) for v in lat)):
                lat=None
            out.append({'action_id':r['id'],'s':state,'a':route,
                        'y':[math.log1p(duration),1. if r['status']=='FINAL' else 0.,math.log1p(output_chars)/8],
                        'latent':lat})
        except (ValueError,TypeError,KeyError,OverflowError,AttributeError):
            continue
    return list(reversed(out))

def ridge(X,Y,lam=RIDGE):
    X=np.asarray(X,float);Y=np.asarray(Y,float);A=X.T@X+lam*np.eye(X.shape[1])
    return np.linalg.solve(A,X.T@Y)

def _align_predict(Xtrain,Ytrain,Xtest,lam=1.):
    """Ridge prediction; dual form avoids a large latent-dimension Gram solve."""
    if Xtrain.shape[1] > Xtrain.shape[0]:
        gram=Xtrain@Xtrain.T+lam*np.eye(Xtrain.shape[0])
        return (Xtest@Xtrain.T)@np.linalg.solve(gram,Ytrain)
    return Xtest@ridge(Xtrain,Ytrain,lam)

def _split(n):
    """Deterministic hashed 1-in-4 hold-out (a plain i%4 split can align with periodic action patterns)."""
    test=[i for i in range(n) if ((i*2654435761)%2**32>>16)%4==3];return [i for i in range(n) if i not in set(test)],test

def _action_binding(store, action_id):
    """Stable digest of action, selected route and still-readable source."""
    if type(action_id) is not str or not action_id:
        return None
    try:
        row = store.one(
            "SELECT id,event_id,status,expected,outcome,created FROM actions WHERE id=?",
            (action_id,))
        if not row or row['status'] != 'FINAL':
            return None
        if not _valid_observed_event_source(store, row['event_id']):
            return None
        selection = store.one(
            "SELECT payload,created FROM packets WHERE kind='ActionSelection' "
            "AND event_id=? AND created<=? ORDER BY created DESC,rowid DESC LIMIT 1",
            (row['event_id'],row['created']))
        if not selection or json.loads(selection['payload']).get('route_hint') not in ACTIONS:
            return None
        fields = ([row[k] for k in ('id','event_id','status','expected','outcome','created')]
                  + [selection['payload'],selection['created']])
        raw = json.dumps(fields, ensure_ascii=False, separators=(',',':'),
                         allow_nan=False).encode('utf-8')
        return {'action_id': action_id, 'event_id': row['event_id'],
                'action_sha256': hashlib.sha256(raw).hexdigest()}
    except (ValueError, TypeError, KeyError, AttributeError, OSError, sqlite3.Error):
        return None


def _state_digest(st):
    """Hash the entire fitted payload except its own digest field."""
    content = {k:v for k,v in st.items() if k != 'model_sha256'}
    raw = json.dumps(content, sort_keys=True, ensure_ascii=False,
                     separators=(',',':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _state_integrity(st):
    try:
        return (type(st) is dict and type(st.get('model_sha256')) is str
                and st['model_sha256'] == _state_digest(st))
    except (TypeError, ValueError, OverflowError):
        return False


def _bindings_valid(store, st):
    """Fail closed for actual Store; no synthetic fixture is production evidence."""
    reader = getattr(store, 'read_source', None)
    if reader is None:
        return st.get('evidence_scope') == 'SYNTHETIC_TEST_ONLY'
    if not callable(reader) or st.get('evidence_scope') != 'SOURCE_BOUND_STORE':
        return False
    bindings = st.get('training_bindings')
    n = st.get('n')
    if (type(bindings) is not list or type(n) is not int or n < MIN_FIT
            or len(bindings) != n):
        return False
    ids = set()
    for binding in bindings:
        if type(binding) is not dict or set(binding) != {'action_id','event_id','action_sha256'}:
            return False
        aid = binding.get('action_id')
        if type(aid) is not str or aid in ids:
            return False
        ids.add(aid)
        if _action_binding(store, aid) != binding:
            return False
    return True


def fit(store,rng_seed=0):
    """Fit all four objectives from stored transitions; persist parameters + held-out metrics."""
    T=transitions(store);n=len(T)
    st={'revision':REVISION,'fitted':now(),'n':n,'counts':{a:sum(t['a']==a for t in T) for a in ACTIONS},'status':'TOO_FEW_TRANSITIONS'}
    if n<MIN_FIT:store.set_state(KEY,st);return st
    reader = getattr(store, 'read_source', None)
    actual_store = reader is not None
    if actual_store:
        if not callable(reader):
            return dict(st, status='SOURCE_UNVERIFIED')
        bindings = [_action_binding(store, t.get('action_id')) for t in T]
        if any(b is None for b in bindings):
            return dict(st, status='SOURCE_UNVERIFIED')
    else:
        bindings = []  # legacy synthetic SQLite test double; not production
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
        try:
            Xl=np.hstack([np.ones((n,1)),np.array(L,float)])
            with np.errstate(over='raise',invalid='raise',divide='raise'):
                prediction=_align_predict(Xl[tr],Y[tr],Xl[te],1.)
                if not np.isfinite(prediction).all():raise FloatingPointError('nonfinite latent prediction')
                res=((prediction-Y[te])**2).sum(0)
                tot=((Y[te]-Y[tr].mean(0))**2).sum(0)+1e-12
                r2=1.-res/tot
                if not np.isfinite(r2).all():raise FloatingPointError('nonfinite state-align R2')
            align={'status':'MEASURED','r2':dict(zip(TARGETS,[round(float(v),4) for v in r2]))}
        except (FloatingPointError,np.linalg.LinAlgError,ValueError,OverflowError):
            align={'status':'UNAVAILABLE','reason':'NUMERIC_UNSTABLE_LATENT'}
    st.update(status='FITTED',forward=[W.tolist() for W in fw],inverse=Wi.tolist(),
              states={a:[t['s'] for t in T if t['a']==a][-256:] for a in ACTIONS},
              metrics={'forward_mae':dict(zip(TARGETS,np.round(mae,4).tolist())),'forward_baseline_mae':dict(zip(TARGETS,np.round(base,4).tolist())),
                       'inverse_accuracy':None if inv_acc is None else round(inv_acc,4),'inverse_majority_baseline':round(major,4),
                       'inverse_note':'representation/control signal, not a causal claim','state_align':align,'held_out':len(te)})
    st['evidence_scope'] = 'SOURCE_BOUND_STORE' if actual_store else 'SYNTHETIC_TEST_ONLY'
    st['training_bindings'] = bindings
    st['model_sha256'] = _state_digest(st)
    # Recheck after training; any revocation during fit must block persistence.
    if actual_store and not _bindings_valid(store, st):
        return dict(st, status='SOURCE_CHANGED_DURING_FIT')
    store.set_state(KEY,st);store.log('world_model_fit',None,{'n':n,'status':'FITTED'})
    return st

def load(store):
    st=store.state(KEY,None)[0]
    if (not st or st.get('revision')!=REVISION or st.get('status')!='FITTED'
            or not _state_integrity(st) or not _bindings_valid(store,st)):
        return None
    return st

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
    """Predicted consequence of action a, never a real outcome or authority."""
    explicit_state = st is not None
    st=st or load(store)
    if a not in ACTIONS:raise ValueError('Aktion '+'|'.join(ACTIONS))
    cov=None
    def uncertain(reason):
        out={'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN',
             'reason':reason,'cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
        # An invalid extrapolation is still uncertain, but preserve a finite
        # observed-support diagnostic when coverage was already measured.
        if isinstance(cov,dict):
            distance=cov.get('ood_distance')
            if distance is None or (type(distance) in (int,float) and math.isfinite(distance)):
                out['coverage']=cov
        return out
    if explicit_state and callable(getattr(store, 'read_source', None)):
        if not _state_integrity(st) or not _bindings_valid(store, st):
            return uncertain('TRAINING_SOURCE_UNVERIFIED')
    if not st or st.get('status')!='FITTED':return uncertain('NO_WORLD_MODEL')
    try:
        x=np.asarray([1.]+list(s)+onehot(a),dtype=float)
        if x.shape!=(9,) or not np.isfinite(x).all():return uncertain('INVALID_STATE')
        W=np.asarray(st['forward'],dtype=float)
        if W.shape!=(ENSEMBLE,9,3) or not np.isfinite(W).all():
            return uncertain('INVALID_MODEL_STATE')
        preds=np.array([x@w for w in W])
        mean=preds.mean(0);spread=float(preds.std(0).mean())
        cov=coverage(st,s,a)
        ood=cov['ood_distance'] if cov['ood_distance'] is not None else 1e9
        if not np.isfinite(mean).all() or not math.isfinite(spread) or not math.isfinite(ood):
            return uncertain('NONFINITE_PREDICTION')
        # The training targets are log1p(nonnegative duration/chars) and
        # binary success. A ridge extrapolation outside their physical
        # domains is not a supported simulation; never clamp/invent values.
        if mean[0]<0 or not 0<=mean[1]<=1 or mean[2]<0:
            return uncertain('IMPOSSIBLE_PREDICTED_OUTCOME')
        conf=(1-math.exp(-cov['samples']/COVER_N))*math.exp(-max(0.,ood-OOD_SUPPORT))/(1+spread/SPREAD_REF)
        duration=math.expm1(float(mean[0]))
        if not math.isfinite(conf) or not math.isfinite(duration):
            return uncertain('NONFINITE_PREDICTION')
    except (ValueError,TypeError,KeyError,OverflowError,AttributeError,IndexError):
        return uncertain('INVALID_MODEL_STATE')
    conf=round(max(0.,min(1.,conf)),4)
    return {'action':a,'prediction':dict(zip(TARGETS,np.round(mean,4).tolist()))|{'duration_s':round(duration,3)},
            'coverage':cov,'model_spread':round(spread,4),'confidence':conf,'cause':'SELF_CAUSED','authority':'HYPOTHESIS',
            'label':'SIMULATION_SUPPORTED' if conf>=CF_MIN and cov['in_support'] else 'SIMULATION_UNCERTAIN'}

def for_event(store,event_id,a):
    """Route alternative for a valid stored own state; malformed state is not simulated."""
    row=store.one("SELECT expected,created FROM actions WHERE event_id=? AND expected LIKE ? ORDER BY created DESC LIMIT 1",(event_id,'%"forecast"%'))
    if not row:return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN','reason':'NO_OBSERVED_STATE','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    if not _valid_observed_event_source(store,event_id):
        return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN',
                'reason':'INVALID_EVENT_SOURCE','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    try:
        exp=json.loads(row['expected']);fc=exp.get('forecast') or {}
        if type(fc) is not dict or type(fc.get('input_chars')) is not int or fc['input_chars']<0 or not _finite_nonnegative(row['created']):
            raise ValueError('invalid observed state')
        s=state_vec(fc['input_chars'],fc.get('resource_state','NORMAL'),(row['created']%86400)/3600)
        if not all(math.isfinite(v) for v in s):raise ValueError('nonfinite observed state')
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
        return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN',
                'reason':'INVALID_OBSERVED_STATE','cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
    return counterfactual(store,s,a)

def report(store):
    st=load(store)
    if not st:return {'revision':REVISION,'status':'NOT_FITTED'}
    return {k:st.get(k) for k in ('revision','status','n','counts','fitted','metrics')}|{'claim_limit':'Own digital transitions only; prediction is not causality; counterfactuals stay simulations'}
