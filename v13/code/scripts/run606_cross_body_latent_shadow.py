#!/usr/bin/env python3
"""Run606: real paired native B1/B2 read-only states, SHADOW ridge alignment only.

Never installs a bridge, changes model weights, or promotes B3/STEP2/JEPA.
Cohort and held-out split were committed before this script.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import time

import numpy as np

from v13.common import APP, atomic_write, dumps
from v13.config import DEFAULTS
from v13.runners import LlamaRunner, TAP_SPECS

COHORT = APP / 'docs/proofs/continuation-20261026/run606-cross-body-latent-shadow/RUN606_COHORT.json'
COHORT_BLOB = 'c0c2a2f74ab8a487563df2449d5faad79fab738f'
B1_SHA = 'bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1'
B2_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
ARCHIVE_SHA = '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
SEED = 20261026
ALPHA = 1.0
CONTROLS = 100
GATES = {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
         'jepa_weight':0,'Redmi':'UNMEASURED','V13':'INCOMPLETE'}


def file_sha(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):
            h.update(part)
    return h.hexdigest()


def git_blob_sha(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\\0'+b).hexdigest()


def load_cohort(path=COHORT):
    path=Path(path)
    if git_blob_sha(path)!=COHORT_BLOB:
        raise ValueError('RUN606 frozen cohort blob differs')
    d=json.loads(path.read_text(encoding='utf-8'))
    if d.get('schema')!='V13_RUN606_COHORT_V1' or d.get('seed')!=SEED:
        raise ValueError('RUN606 cohort schema/seed mismatch')
    train=set(d['train_topics']);test=set(d['test_topics'])
    rows=d['prompts']
    if (len(rows)!=40 or len(train)!=6 or len(test)!=2 or train&test
            or len({r['id'] for r in rows})!=40 or len({r['text'] for r in rows})!=40
            or {r['topic'] for r in rows}!=train|test
            or any(sum(r['topic']==t for r in rows)!=5 for t in train|test)):
        raise ValueError('RUN606 cohort/split malformed')
    return d


def normalize(x):
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=2 or not np.isfinite(x).all():
        raise ValueError('nonfinite or nonmatrix latent rows')
    n=np.linalg.norm(x,axis=1,keepdims=True)
    if np.any(n<=1e-12):raise ValueError('zero latent row')
    return x/n


def evaluate(x,y,train,test,seed=SEED,alpha=ALPHA,controls=CONTROLS):
    x,y=normalize(x),normalize(y)
    train=np.asarray(train,dtype=int);test=np.asarray(test,dtype=int)
    if (len(train)<4 or len(test)<2 or set(train)&set(test)
            or len(set(train))!=len(train) or len(set(test))!=len(test)
            or np.any(train<0) or np.any(test<0)
            or np.any(train>=len(x)) or np.any(test>=len(x))
            or len(x)!=len(y) or x.shape[1]!=2048 or y.shape[1]!=1024):
        raise ValueError('paired dimension/split mismatch')
    xm=x[train].mean(axis=0);ym=y[train].mean(axis=0)
    xt=normalize(x[train]-xm);xv=normalize(x[test]-xm)
    yt=normalize(y[train]-ym);yv=normalize(y[test]-ym)
    gram=xt@xt.T;cross=xv@xt.T
    inv=np.linalg.solve(gram+alpha*np.eye(len(train)),np.eye(len(train)))
    def metric(targets):
        pred=normalize(cross@inv@targets)
        sims=pred@yv.T
        return {'top1':float(np.mean(np.argmax(sims,axis=1)==np.arange(len(test)))),
                'matched_cosine':float(np.mean(np.diag(sims)))}
    observed=metric(yt)
    rng=np.random.default_rng(seed)
    shuffled=[metric(yt[rng.permutation(len(train))]) for _ in range(controls)]
    top=[r['top1'] for r in shuffled];cos=[r['matched_cosine'] for r in shuffled]
    p=(1+sum(t>=observed['top1'] for t in top))/(controls+1)
    mean_raw=normalize(np.repeat(y[train].mean(axis=0,keepdims=True),len(test),axis=0))
    mean_cos=float(np.mean(np.sum(mean_raw*y[test],axis=1)))
    signal=observed['top1']>=.3 and p<=.05
    return {'observed':observed,'shuffled':{'n':controls,'mean_top1':float(np.mean(top)),
            'p95_top1':float(np.percentile(top,95)),'max_top1':max(top),
            'mean_matched_cosine':float(np.mean(cos))},
            'mean_predictor_matched_cosine':mean_cos,'empirical_p_top1':p,
            'exploratory_signal':bool(signal),'heldout_chance_top1':1/len(test),
            'alpha':alpha,'seed':seed,'train_n':len(train),'test_n':len(test),
            'claim':'Paired native last-token representation alignment only, no semantic/B3 utility'}


def capture(model,server,role,tap_key,rows,workdir):
    expected_id,dim=TAP_SPECS[tap_key]
    cfg=dict(DEFAULTS,context_tokens=1024,threads=2,native_cache_ram_mb=0,native_ctx_checkpoints=0)
    home=Path(workdir);home.mkdir(parents=True,exist_ok=True);(home/'logs').mkdir(exist_ok=True)
    runner=LlamaRunner(home,role,model,cfg,purpose='tap')
    runner.binary=str(server);runner.tap_id,runner.tap_dim=expected_id,dim
    states=[];receipts=[]
    try:
        for row in rows:
            item=runner.tap(row['text'],threading.Event(),time.monotonic()+120,max_tokens=64)
            ids=item['token_ids'];vectors=item['vectors'];metrics=item['metrics']
            if (not 1<=len(ids)<=64 or len(vectors)!=len(ids)
                    or metrics.get('role')!=role or metrics.get('tap_id')!=expected_id
                    or metrics.get('embedding_dim')!=dim
                    or metrics.get('CAN_LATENT_TAP') is not True
                    or metrics.get('CAN_LATENT_INJECT') is not False
                    or metrics.get('CAN_TRAIN_BODY') is not False):
                raise ValueError('native tap authority/source/token mismatch: '+row['id'])
            v=np.asarray(vectors[-1],dtype=np.float64)
            if v.shape!=(dim,) or not np.isfinite(v).all() or np.linalg.norm(v)<=1e-12:
                raise ValueError('native last-token vector invalid: '+row['id'])
            states.append(v)
            receipts.append({'id':row['id'],'prompt_sha256':hashlib.sha256(row['text'].encode()).hexdigest(),
                             'token_count':len(ids),'last_token_id':int(ids[-1]),
                             'tap_id':expected_id,'dimension':dim})
    finally:
        runner.unload()
    return np.stack(states),receipts


def run(home,out,states_path):
    home,out,states_path=Path(home),Path(out),Path(states_path)
    out.parent.mkdir(parents=True,exist_ok=True);states_path.parent.mkdir(parents=True,exist_ok=True)
    report={'schema':'V13_RUN606_CROSS_BODY_NATIVE_SHADOW_V1','status':'INCOMPLETE',
            'evidence_level':'LINUX_NATIVE_PAIRED_READONLY','gates':dict(GATES),
            'cohort_blob':COHORT_BLOB,'seed':SEED,'no_weight_updates':True,
            'can_latent_inject':False,'redmi_measured':False,'b3_promoted':False}
    def save():atomic_write(out,(dumps(report)+'\\n').encode())
    save()
    try:
        cohort=load_cohort();rows=cohort['prompts']
        specs=json.loads((APP/'specs/models.json').read_text())
        if specs['runner']['linux_binaries']['linux-x86_64']['sha256']!=ARCHIVE_SHA:
            raise ValueError('runner archive pin mismatch')
        models=[('B1_DETAIL','body',B1_SHA,2048),
                ('B2_GIST','gist',B2_SHA,1024)]
        arrays=[];receipts={}
        server=home/'bin/llama-server'
        if not server.is_file():raise ValueError('pinned native server missing')
        report['runner_sha256']=file_sha(server)
        with tempfile.TemporaryDirectory(prefix='v13-run606-') as td:
            for role,key,expected,dim in models:
                spec=specs['models'][key]
                model=home/'models'/key/spec['main_file']
                if file_sha(model)!=expected or spec['files'][0]['sha256']!=expected:
                    raise ValueError('pinned '+role+' model hash mismatch')
                if TAP_SPECS[key][1]!=dim:raise ValueError('tap dimension changed')
                v,rc=capture(model,server,role,key,rows,Path(td)/key)
                arrays.append(v);receipts[role]=rc
                report.setdefault('models',{})[role]={'model_id':spec['model_id'],
                    'revision':spec['revision'],'sha256':expected,'tap_id':TAP_SPECS[key][0],
                    'dimension':dim,'rows':len(v)}
                report.setdefault('receipts',{})[role]=rc
                save()
        train=[i for i,r in enumerate(rows) if r['topic'] in cohort['train_topics']]
        test=[i for i,r in enumerate(rows) if r['topic'] in cohort['test_topics']]
        metrics=evaluate(arrays[0],arrays[1],train,test)
        with tempfile.NamedTemporaryFile(dir=states_path.parent,suffix='.npz',delete=False) as tmp:
            tmp_path=Path(tmp.name)
            np.savez_compressed(tmp,x_b1=arrays[0],y_b2=arrays[1],
                prompt_ids=np.array([r['id'] for r in rows]),
                train_idx=np.array(train),test_idx=np.array(test))
            tmp.flush();os.fsync(tmp.fileno())
        os.replace(tmp_path,states_path)
        report.update(metrics=metrics,states_sha256=file_sha(states_path),
            states_bytes=states_path.stat().st_size,
            status='EXPLORATORY_SIGNAL' if metrics['exploratory_signal'] else 'NO_EXPLORATORY_SIGNAL')
        save()
        return report
    except BaseException as exc:
        report.update(status='ERROR',error_type=type(exc).__name__,error=str(exc)[:300])
        save()
        raise


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--home',required=True);p.add_argument('--out',required=True)
    p.add_argument('--states',required=True)
    a=p.parse_args()
    result=run(a.home,a.out,a.states)
    print(dumps({'status':result['status'],'metrics':result['metrics'],
        'states_sha256':result['states_sha256']}))


if __name__=='__main__':
    main()
