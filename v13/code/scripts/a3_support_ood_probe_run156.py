"""Run156: bounded deterministic A3 OOD stress probe, read-only, no authority.

Synthetic vectors are diagnostic controls, not learned teacher embeddings.
Never select a support threshold from held-out ID/OOD examples.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.a3_trainonly_support_floor_run152 import train_only_floor

SEED=15625
GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
       'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}


def unit(x):
    return x/np.linalg.norm(x,axis=1,keepdims=True)


def score(train, id_holdout, ood_holdout):
    """Compute threshold on training vectors only; audit held-out acceptance."""
    t=np.asarray(train,dtype=np.float64)
    h=np.asarray(id_holdout,dtype=np.float64)
    o=np.asarray(ood_holdout,dtype=np.float64)
    if t.ndim!=2 or h.ndim!=2 or o.ndim!=2 or t.shape[1:]!=(512,) or h.shape[1:]!=(512,) or o.shape[1:]!=(512,):
        raise ValueError('shape')
    if len(h)<1 or len(o)<1 or not all(np.isfinite(x).all() for x in (t,h,o)):
        raise ValueError('nonfinite_or_empty')
    if any(np.any(np.linalg.norm(x,axis=1)<1e-8) for x in (t,h,o)):
        raise ValueError('zero_vector')
    stats=train_only_floor(t)
    tn=unit(t);hs=unit(h)@tn.T;os=unit(o)@tn.T
    floor=stats['support_floor']
    id_scores=hs.max(axis=1);ood_scores=os.max(axis=1)
    return {'support_floor':floor,'train_loo_p05':stats['train_loo_p05'],
            'floor_clamped_min':floor==.5,'id_count':len(h),'ood_count':len(o),
            'id_accepted':int(np.count_nonzero(id_scores>=floor)),
            'ood_accepted':int(np.count_nonzero(ood_scores>=floor)),
            'id_accept_rate':float(np.mean(id_scores>=floor)),
            'ood_false_accept_rate':float(np.mean(ood_scores>=floor)),
            'id_score_min':float(id_scores.min()),'id_score_max':float(id_scores.max()),
            'ood_score_min':float(ood_scores.min()),'ood_score_max':float(ood_scores.max()),
            'threshold_uses_heldout':False}


def cohorts(seed=SEED):
    rng=np.random.default_rng(seed)
    center=unit(rng.normal(size=(1,512)))
    train_cluster=unit(center+rng.normal(scale=.015,size=(64,512)))
    id_cluster=unit(center+rng.normal(scale=.015,size=(64,512)))
    ood_cluster=unit(rng.normal(size=(64,512)))
    train_uniform=unit(rng.normal(size=(64,512)))
    id_uniform=unit(rng.normal(size=(64,512)))
    ood_uniform=unit(rng.normal(size=(64,512)))
    return {'clustered':(train_cluster,id_cluster,ood_cluster),
            'uniform':(train_uniform,id_uniform,ood_uniform)}


def probe(seed=SEED):
    cases=cohorts(seed)
    results={k:score(*v) for k,v in cases.items()}
    definition={'seed':seed,'n_train':64,'n_id':64,'n_ood':64,'raw_dim':512,
                'regimes':['clustered','uniform'],'cluster_noise':.015}
    return {'schema':'V13_RUN156_A3_TRAIN_ONLY_OOD_DIAGNOSTIC_V1',
            'cohort_definition_sha256':hashlib.sha256(json.dumps(definition,sort_keys=True).encode()).hexdigest(),
            'definition':definition,'results':results,
            'evidence_class':'SYNTHETIC_NUMPY_ONLY_NO_TEACHER_OR_NATIVE',
            'authority':'SHADOW_DIAGNOSTIC_NOT_ACTIVE',
            'gate':'UNVERIFIED','gates':GATES,
            'limitations':['synthetic cosine regimes are not measured A3 teacher features',
                           'no real source-group OOD or held-out teacher truth',
                           'the 0.5 clamp can reject all unrelated in-domain vectors',
                           'no frozen worker, Runtime, native model, JEPA or Redmi changes']}


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();report=probe()
    with a.output.open('x',encoding='utf-8') as f:
        f.write(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('RUN156_A3_OOD',report['evidence_class'],report['gate'])

if __name__=='__main__':main()
