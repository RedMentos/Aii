"""Run152: A3 train-only support threshold candidate (no held-out leakage).

Existing frozen student_worker.train() currently computes its support_floor
from raw[vi] @ raw[ti].T, which uses held-out sources to tune a threshold.
This standalone candidate computes leave-one-out train nearest-neighbour
similarity only. No worker/weights/teacher model or runtime is modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
       'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}


def train_only_floor(train,quantile=.05,margin=.02):
    a=np.asarray(train,dtype=np.float64)
    if a.ndim!=2 or a.shape[0]<20 or a.shape[1]!=512 or a.shape[0]>512:
        raise ValueError('train_shape')
    if not np.isfinite(a).all():raise ValueError('nonfinite_train')
    norms=np.linalg.norm(a,axis=1)
    if np.any(norms<1e-8):raise ValueError('zero_train_vector')
    x=a/norms[:,None]
    if np.unique(x,axis=0).shape[0]!=len(x):raise ValueError('duplicate_train_vectors')
    sim=x@x.T
    np.fill_diagonal(sim,-np.inf)
    nearest=sim.max(axis=1)
    q=float(np.quantile(nearest,quantile))
    return {'support_floor':float(max(.5,min(.99,q-margin))),
            'train_loo_p05':q,'train_loo_min':float(nearest.min()),
            'train_loo_max':float(nearest.max()),'train_sources':len(x),
            'threshold_uses_heldout':False,'method':'TRAIN_LEAVE_ONE_OUT_P05_MINUS_002_V1'}


def run(raw):
    if len(raw)>1_000_000:raise ValueError('input_too_large')
    data=json.loads(raw)
    texts=data['texts'];groups=data['source_groups']
    if not isinstance(texts,list) or not isinstance(groups,list) or len(texts)!=len(groups) or not 32<=len(texts)<=512:
        raise ValueError('source_count')
    if any(not isinstance(t,str) or not 1<=len(t.encode())<=4096 for t in texts):raise ValueError('invalid_text')
    if any(not isinstance(g,str) or not 1<=len(g)<=128 for g in groups):raise ValueError('invalid_source_group')
    from v13.student_worker import raw_features,split
    ti,vi=split(groups)
    train=np.stack([raw_features(texts[i]) for i in ti])  # never read held-out text into features
    stats=train_only_floor(train)
    return {'schema':'V13_RUN152_A3_TRAIN_ONLY_SUPPORT_V1',
            'input_sha256':hashlib.sha256(raw).hexdigest(),
            'source_count':len(texts),'heldout_sources':len(vi),
            'train_sources':len(ti),'threshold':stats,
            'authority':'SHADOW_CANDIDATE_NOT_ACTIVE',
            'teacher_parameter_updates':0,'student_parameter_updates':0,
            'gate':'UNVERIFIED','gates':GATES,
            'limitations':['not integrated with frozen student_worker',
                           'threshold not calibrated on fresh OOD native teacher data',
                           'no Redmi/Body-JEPA evidence; no weights updated']}


def publish_exclusive(out,data):
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.a3-trainonly-',dir=out.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.link(tmp,out)
        dfd=os.open(out.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:os.unlink(tmp)


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();raw=a.input.read_bytes();report=run(raw)
    publish_exclusive(a.output,(json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
    print('RUN152_A3_TRAIN_ONLY_CANDIDATE',report['threshold']['support_floor'],'NO_GATE_PROMOTION')

if __name__=='__main__':main()
