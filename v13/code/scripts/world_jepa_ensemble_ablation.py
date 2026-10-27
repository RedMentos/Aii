"""Preregistered synthetic World-JEPA primary-vs-ensemble-mean ablation.

No native/model downloads, no checkpoint activation, no registered cohort changes.
See docs/proofs/continuation-20261027/world-jepa-ensemble-ablation/PLAN.md.
"""
import json
import math
import time
import numpy as np
from v13 import world_jepa as wj

TRAIN_SEED=20261027
HOLDOUT_SEED=20261028
TRAIN_N=512
HOLDOUT_N=192
STEPS=500
ENSEMBLE=3


def cohort(n,seed):
    rng=np.random.default_rng(seed)
    x=np.concatenate((rng.integers(0,2,(n,4)).astype(float),rng.normal(size=(n,4))),axis=1)
    act=rng.integers(0,4,n)
    a=np.eye(4)[act]
    y=x.copy()
    y[np.arange(n),act]=1-x[np.arange(n),act]
    y[:,4:]=rng.normal(size=(n,4))
    return x,a,y


def run():
    x,a,y=cohort(TRAIN_N,TRAIN_SEED)
    hx,ha,hy=cohort(HOLDOUT_N,HOLDOUT_SEED)
    start=time.monotonic()
    m=wj.WorldJEPA(seed=TRAIN_SEED,ensemble=ENSEMBLE).fit(x,a,y,steps=STEPS)
    z=m.latent(hx,target=False)
    target=m.latent(hy,target=True)
    predictions=np.stack([wj.predict(p,z,ha)[0] for p in m.preds])
    primary=predictions[0]
    mean=predictions.mean(0)
    public,spread=m.predict(hx,ha)
    if not np.array_equal(primary,public):
        raise AssertionError('Frozen source no longer uses primary predictor: update preregistration')
    no_action=wj.predict(m.preds[0],z,np.zeros_like(ha))[0]
    shuffled=wj.predict(m.preds[0],z,np.roll(ha,1,axis=0))[0]
    mse=lambda pred:float(np.mean((pred-target)**2))
    metrics={'revision':wj.REVISION,'cohort':'SYNTHETIC_ACTION_FLIP_FRESH_NUISANCE',
             'train_seed':TRAIN_SEED,'holdout_seed':HOLDOUT_SEED,'train_rows':TRAIN_N,'heldout_rows':HOLDOUT_N,
             'steps':STEPS,'ensemble':ENSEMBLE,'primary_mse':mse(primary),'ensemble_mean_mse':mse(mean),
             'no_action_primary_mse':mse(no_action),'shuffled_action_primary_mse':mse(shuffled),
             'ensemble_spread_mean':float(spread.mean()),
             'mean_over_primary_mse_ratio':float(mse(mean)/max(mse(primary),1e-12)),
             'noncollapse':m.collapse_stats(hy),'duration_s':round(time.monotonic()-start,3),
             'source_prediction_matches_primary':True,'training_source':'NEW_SYNTHETIC_ONLY',
             'claim_limit':'Ablation of a frozen World-JEPA synthetic latent predictor; no causal utility, native, phone, retention, Age or production promotion'}
    finite=[v for k,v in metrics.items() if k.endswith('_mse') or k in ('ensemble_spread_mean','mean_over_primary_mse_ratio')]
    if not all(math.isfinite(v) and v>=0 for v in finite):
        raise AssertionError('Nonfinite or negative metric')
    if len(predictions)!=ENSEMBLE or not np.isfinite(predictions).all():
        raise AssertionError('Invalid ensemble predictions')
    print(json.dumps(metrics,sort_keys=True,allow_nan=False))
    return metrics


if __name__=='__main__':
    run()
