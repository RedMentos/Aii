"""V13 WP-T8 Run37: isolated replay of the Run28 counterfactual outcome-domain check.

This is a test seam, not a replacement for the full world-model implementation.
"""
import math
import numpy as np

ACTIONS=('simple','detail','gist','both')
TARGETS=('log_duration','success','log_chars')
ENSEMBLE=5
COVER_N=8.
SPREAD_REF=.25
CF_MIN=.5
OOD_SUPPORT=2.

def onehot(a):return [1. if a==x else 0. for x in ACTIONS]

def coverage(st,s,a):
    pts=np.array(st['states'].get(a) or [],float);n=len(pts)
    if n==0:return {'samples':0,'ood_distance':None,'in_support':False}
    d=np.sqrt(((pts-np.array(s))**2).sum(1));nearest=float(d.min())
    if n>=2:
        dd=np.sqrt(((pts[:,None,:]-pts[None,:,:])**2).sum(2));np.fill_diagonal(dd,np.inf);scale=float(np.median(dd.min(1)))
    else:scale=0.
    ood=nearest/max(scale,1e-3)
    return {'samples':n,'ood_distance':round(ood,4),'in_support':ood<=OOD_SUPPORT}

def counterfactual(s,a,st,guarded=False):
    if a not in ACTIONS:raise ValueError('unknown action')
    def uncertain(reason):
        return {'action':a,'prediction':None,'confidence':0.,'label':'SIMULATION_UNCERTAIN',
                'reason':reason,'cause':'SELF_CAUSED','authority':'HYPOTHESIS'}
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
        # Run37 candidate: log1p(nonnegative) targets cannot be negative;
        # success regression is not calibrated, but must lie within [0,1]
        # before a prediction is shown as supported. Never clamp/invent.
        if guarded and (mean[0]<0 or not 0<=mean[1]<=1 or mean[2]<0):
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
