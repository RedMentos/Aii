"""Offline frozen-Needle embedding route-head experiment; never a live C2 route.

Train only on disjoint train64 fit48. Validation16 and transfer64 are never
used for optimization/hyperparameter selection. Original English96 stays frozen.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import threading
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ('simple','detail','gist','both')
TRAIN_BLOB = 'e944d33e544ff828adee8c9be3feb5e078726e99'
TRAIN_SHA = 'fd715d8491fd673eabc1b62f30633fce2410ee554773336e584cf48ec364b75c'
TRANSFER_BLOB = 'e9aaae43f3313fbdc8e4b2fc870f2712a5557a66'
TRANSFER_SHA = '12863402ffecef7565d23d1162fa061a1983ee92b46332c60adcfb3cd37ca9af'
ORIGINAL_BLOB = '758c5a7dea93bfb178bc3778428ee262178b6a58'
ORIGINAL_SHA = '54f3da390fb79c3f966edd61d3390d94dc59d850987174c644ef45ef531a54e6'
CATALOG_BLOB = '7af05962af41d0bc3f7dd18ef01d4eba55eabf99'
CONTROL_BLOB = '954a3f468f10195fbce12d27f68585ee7edee2c9'
MODEL_SHA = 'c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38'
LR = 0.5
L2 = 0.01
STEPS = 400
MAX_GRAD_NORM = 1.0
SEED = 13


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def _registered(path, blob, sha, schema, count):
    raw=Path(path).read_bytes()
    if git_blob(raw)!=blob:raise ValueError('Registered Git blob drift: '+str(path))
    d=json.loads(raw)
    if d.get('schema')!=schema or d.get('items_sha256')!=sha:raise ValueError('Registered cohort metadata drift')
    items=d.get('items')
    if not isinstance(items,list) or len(items)!=count:raise ValueError('Registered cohort row count')
    if digest(json.dumps(items,ensure_ascii=False,sort_keys=True).encode())!=sha:raise ValueError('Registered cohort items SHA256')
    return items


def cohorts(root=ROOT):
    train=_registered(root/'specs/c2-bilingual-routehead-train64-20261028.json',TRAIN_BLOB,TRAIN_SHA,
                      'v13.c2.bilingual_routehead_train64.v1',64)
    transfer=_registered(root/'specs/c2-bilingual-transfer64-20261028.json',TRANSFER_BLOB,TRANSFER_SHA,
                         'v13.c2.bilingual_transfer64.v1',64)
    original=_registered(root/'specs/c2-benchmark.json',ORIGINAL_BLOB,ORIGINAL_SHA,'c2-benchmark-v1',96)
    expected_train=[f'train-{route}-{lang}-{i:02d}' for route in ROUTES for lang in ('en','de') for i in range(8)]
    expected_transfer=[f'{route}-{lang}-{i:02d}' for route in ROUTES for lang in ('en','de') for i in range(8)]
    if [r.get('id') for r in train]!=expected_train or [r.get('id') for r in transfer]!=expected_transfer:
        raise ValueError('Registered row IDs/order changed')
    for i,row in enumerate(train):
        expected_split='fit' if i%8<6 else 'validation'
        if row.get('split')!=expected_split or row.get('label') not in ROUTES or row.get('lang') not in ('en','de'):
            raise ValueError('Train split/route/lang drift')
    for row in transfer:
        if row.get('label') not in ROUTES or row.get('lang') not in ('en','de'):
            raise ValueError('Transfer route/lang drift')
    texts=[str(x.get('text','')).strip().casefold() for x in train+transfer+original]
    if not all(texts) or len(set(texts))!=len(texts):
        raise ValueError('Training/evaluation prompt overlap or blank')
    if Counter((r['label'],r['lang']) for r in train)!=Counter({(a,b):8 for a in ROUTES for b in ('en','de')}):
        raise ValueError('Train imbalance')
    if Counter((r['label'],r['lang']) for r in transfer)!=Counter({(a,b):8 for a in ROUTES for b in ('en','de')}):
        raise ValueError('Transfer imbalance')
    return train,transfer


def normalize(x):
    a=np.asarray(x,dtype=np.float64)
    if a.ndim!=2 or a.shape[0]<1 or a.shape[1]<2 or not np.isfinite(a).all():
        raise ValueError('Finite matrix embeddings required')
    return a/np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-9)


def loss_grad(x,y,w,b):
    if x.ndim!=2 or w.shape!=(x.shape[1],4) or b.shape!=(4,) or y.shape!=(len(x),):
        raise ValueError('Route-head shape mismatch')
    z=x@w+b
    z=z-z.max(axis=1,keepdims=True)
    exp=np.exp(z);p=exp/exp.sum(axis=1,keepdims=True)
    target=np.eye(4)[y]
    loss=float(-np.log(np.maximum(p[np.arange(len(y)),y],1e-12)).mean()+0.5*L2*(w*w).sum())
    grad=(p-target)/len(y)
    return loss, x.T@grad+L2*w, grad.sum(axis=0)


def fit(x,y):
    if x.shape[0]!=48 or y.shape!=(48,) or not np.issubdtype(y.dtype,np.integer) or np.any((y<0)|(y>3)):
        raise ValueError('Fit only registered 48 route labels')
    np.random.seed(SEED)  # no stochastic updates; explicit registered seed
    w=np.zeros((x.shape[1],4),dtype=np.float64)
    b=np.zeros(4,dtype=np.float64)
    losses=[];max_applied_norm=0.0
    for step in range(STEPS):
        loss,gw,gb=loss_grad(x,y,w,b)
        norm=float(np.sqrt(np.square(gw).sum()+np.square(gb).sum()))
        if not math.isfinite(loss) or not math.isfinite(norm):raise ValueError('Nonfinite optimizer')
        scale=min(1.0,MAX_GRAD_NORM/max(norm,1e-12))
        applied=norm*scale
        max_applied_norm=max(max_applied_norm,applied)
        w-=LR*scale*gw;b-=LR*scale*gb
        if not np.isfinite(w).all() or not np.isfinite(b).all():raise ValueError('Nonfinite head')
        losses.append(loss)
    return w,b,{'loss_start':losses[0],'loss_end':losses[-1],
                'steps':STEPS,'max_applied_gradient_norm':max_applied_norm,
                'learning_rate':LR,'l2':L2,'seed':SEED,'trainable_parameter_count':int(w.size+b.size)}


def predict(x,w,b):
    return np.argmax(x@w+b,axis=1)


def evaluate(rows,x,w,b,indices):
    from scripts.c2_benchmark import summarize
    ix=list(indices)
    t0=time.perf_counter();pred=predict(x[ix],w,b);overhead=(time.perf_counter()-t0)/max(1,len(ix))
    out=[{'id':rows[i]['id'],'label':rows[i]['label'],'pred':ROUTES[int(p)],'latency_s':overhead}
         for i,p in zip(ix,pred)]
    per_lang={lang:summarize([r for r in out if r['id'].split('-')[-2]==lang]) for lang in ('en','de')}
    return {'overall':summarize(out),'per_language':per_lang,'head_inference_seconds_per_row':overhead}


def native_preflight(home):
    from v13.models import ModelManager
    from v13.common import file_hash
    if platform.system()!='Linux' or platform.machine().lower() not in ('x86_64','amd64') or os.environ.get('ANDROID_ROOT'):
        raise ValueError('Linux x86_64 only; Redmi separate')
    for path,blob in [('specs/models.json',CATALOG_BLOB),('specs/control_tools.json',CONTROL_BLOB)]:
        if git_blob((ROOT/path).read_bytes())!=blob:raise ValueError('Source blob drift '+path)
    cfg=json.loads((Path(home)/'config/settings.json').read_text())
    if (cfg.get('seed')!=SEED or cfg.get('learning_mode')!='RECORD_ONLY'
        or cfg.get('system_stage')!=0 or cfg.get('jepa_weight',0)!=0 or cfg.get('latents_enabled',False)):
        raise ValueError('Age0 seed/authority drift')
    m=ModelManager(home)
    verified=m.verify(deep=True)
    if not verified.get('needle',{}).get('ok') or not verified['needle'].get('hash_checked'):
        raise ValueError('Needle deep model verification failed')
    if file_hash(m.path_for('C2_CONTROL'))!=MODEL_SHA:raise ValueError('Needle model hash mismatch')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT.parents[1],text=True).strip()


def embed_native(home,items):
    from v13.runtime import Runtime
    r=Runtime(home);cancel=threading.Event();vectors=[];times=[]
    try:
        r.needle.load(cancel,time.monotonic()+120)
        for item in items:
            t0=time.perf_counter();v=r.needle.embed(item['text'],cancel,time.monotonic()+60)
            elapsed=time.perf_counter()-t0
            arr=np.asarray(v,dtype=np.float64)
            if arr.ndim!=1 or arr.size<2 or not np.isfinite(arr).all() or elapsed<0:
                raise ValueError('Invalid native Needle embedding')
            vectors.append(arr);times.append(elapsed)
        if len({v.size for v in vectors})!=1:raise ValueError('Embedding dimension changed')
        return np.stack(vectors),times
    finally:
        r.close()


def save_json_new(path,data):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(data,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n');f.flush();os.fsync(f.fileno())


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--home',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(argv)
    train,transfer=cohorts()
    source=native_preflight(args.home)
    args.out.mkdir(parents=True,exist_ok=False)
    train_x,train_times=embed_native(args.home,train)
    np.savez(args.out/'train_embeddings.npz',vectors=train_x,ids=np.asarray([r['id'] for r in train]))
    transfer_x,transfer_times=embed_native(args.home,transfer)
    np.savez(args.out/'transfer_embeddings.npz',vectors=transfer_x,ids=np.asarray([r['id'] for r in transfer]))
    x=normalize(train_x);tx=normalize(transfer_x)
    if x.shape[1]!=tx.shape[1]:raise ValueError('Embedding dimension mismatch')
    fit_ids=[i for i,r in enumerate(train) if r['split']=='fit']
    val_ids=[i for i,r in enumerate(train) if r['split']=='validation']
    if len(fit_ids)!=48 or len(val_ids)!=16:raise ValueError('Split mismatch')
    labels=np.asarray([ROUTES.index(r['label']) for r in train],dtype=np.int64)
    w,b,stats=fit(x[fit_ids],labels[fit_ids])
    w2,b2,_=fit(x[fit_ids],labels[fit_ids])
    repeat_ok=bool(np.array_equal(w,w2) and np.array_equal(b,b2))
    if not repeat_ok:raise ValueError('Deterministic repeat failed')
    np.savez(args.out/'route_head_shadow.npz',weights=w,bias=b,format=np.asarray('v13-c2-routehead-shadow-v1'))
    with np.load(args.out/'route_head_shadow.npz',allow_pickle=False) as loaded:
        reload_ok=bool(np.array_equal(loaded['weights'],w) and np.array_equal(loaded['bias'],b)
                       and str(loaded['format'])=='v13-c2-routehead-shadow-v1')
    if not reload_ok:raise ValueError('Checkpoint reload failed')
    result={'schema':'v13.c2.bilingual_routehead_shadow.v1','source_commit':source,
            'evidence_kind':'LINUX_NATIVE_NEEDLE_EMBEDDING_PLUS_OFFLINE_LINEAR_SHADOW',
            'train_fixture_git_blob':TRAIN_BLOB,'train_items_sha256':TRAIN_SHA,
            'transfer_fixture_git_blob':TRANSFER_BLOB,'transfer_items_sha256':TRANSFER_SHA,
            'original96_items_sha256':ORIGINAL_SHA,'model_sha256':MODEL_SHA,
            'fit_rows':48,'validation_rows':16,'transfer_test_rows':64,
            'embedding_dim':int(w.shape[0]),'embedding_seconds_mean_train':float(np.mean(train_times)),
            'embedding_seconds_mean_transfer':float(np.mean(transfer_times)),
            'train':evaluate(train,x,w,b,fit_ids),'validation':evaluate(train,x,w,b,val_ids),
            'transfer_test':evaluate(transfer,tx,w,b,range(64)),
            'fit_stats':stats,'deterministic_repeat':repeat_ok,'checkpoint_reload':reload_ok,
            'head_sha256':digest((args.out/'route_head_shadow.npz').read_bytes()),
            'training_on_original96_or_transfer64':False,'native_base_weights_modified':False,
            'semantic_truth_authority':False,'jef_route_activation':False,
            'age0_learning_mode':'RECORD_ONLY','jepa_weight':0,'step2_utility':'FAIL','b3_l1':'FAIL',
            'body_jepa':'UNAVAILABLE','lp3_heldout':'FAIL','phone_measured':False,
            'whole_system_complete':False,
            'claim_limit':'Single offline 48-fit/16-val/64-test author-label shadow head; no live routing or Age promotion'}
    save_json_new(args.out/'report.json',result)
    print(json.dumps({'train':result['train']['overall']['accuracy'],
                      'validation':result['validation']['overall']['accuracy'],
                      'transfer_test':result['transfer_test']['overall']['accuracy'],
                      'no_promotion':True},sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())