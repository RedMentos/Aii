"""Run621: retrospective train-only B2 native diagonal retrieval readout.

Exploratory SHADOW/offline readout. No native inference, body weight update,
JEPA, receiver injection, or automatic activation.
"""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from scripts.run615_crosscohort_shadow import load, GATES, PINS

SEED = 2026102621
CONTROLS = 200
ALPHA = 0.4
W_MIN, W_MAX = 0.5, 2.0


def unit(a):
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError('nonfinite/nonmatrix native states')
    n = np.linalg.norm(a, axis=1, keepdims=True)
    if not np.isfinite(n).all() or (n < 1e-10).any():
        raise ValueError('zero/overflow native states')
    return a / n


def fit(a, b):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if a.shape != b.shape or a.shape != (30, 1024) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('train pairs changed')
    signal = np.mean(a*b, axis=0) - np.mean(a*np.roll(b, 1, axis=0), axis=0)
    z = (signal - signal.mean()) / (signal.std() + 1e-12)
    weights = np.clip(np.exp(np.clip(ALPHA*z, -20, 20)), W_MIN, W_MAX)
    weights /= weights.mean()
    if weights.shape != (1024,) or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError('invalid learned weights')
    return weights


def score(x, target):
    if x.shape != (20, 1024) or len(target) != 20:
        raise ValueError('heldout shape changed')
    sim = x @ x.T
    ranks = []
    for i, t in enumerate(target):
        order = sorted((j for j in range(20) if j != i), key=lambda j: (-float(sim[i,j]), j))
        ranks.append(order.index(t) + 1)
    return {'top1':sum(r == 1 for r in ranks)/20,
            'mrr':sum(1/r for r in ranks)/20}


def paired_indices(ids, train):
    train = [int(i) for i in train]
    mapping = {ids[i]:i for i in train}
    a = sorted((i for i in train if ids[i].endswith('-A')))
    if len(a) != 30:
        raise ValueError('train A/B count changed')
    b = []
    for i in a:
        key = ids[i][:-1]+'B'
        if key not in mapping:
            raise ValueError('train pair missing')
        b.append(mapping[key])
    if len(set(a+b)) != 60:
        raise ValueError('train pair duplication')
    return a,b


def evaluate(y, ids, train, test):
    y = unit(y)
    if y.shape != (80, 1024) or len(ids) != 80 or len(train) != 60 or len(test) != 20:
        raise ValueError('original native cohort shape changed')
    test = [int(i) for i in test]
    if len(set(test)) != 20:
        raise ValueError('heldout indices duplicated')
    names = [ids[i] for i in test]
    target = [names.index(ids[i][:-1]+('B' if ids[i].endswith('A') else 'A')) for i in test]
    a_idx,b_idx = paired_indices(ids, train)
    a,b = y[a_idx],y[b_idx]
    w = fit(a,b)
    weighted = unit(y[test] * np.sqrt(w)[None,:])
    centered = unit(y[test] - y[[int(i) for i in train]].mean(axis=0))
    baseline = {'raw':score(y[test],target), 'train_centered':score(centered,target)}
    learned = score(weighted,target)
    rng = np.random.default_rng(SEED)
    null=[]
    for _ in range(CONTROLS):
        perm = rng.permutation(30)
        wc = fit(a,b[perm])
        null.append(score(unit(y[test]*np.sqrt(wc)[None,:]),target)['top1'])
    p=(1+sum(n>=learned['top1'] for n in null))/(CONTROLS+1)
    best=max(v['top1'] for v in baseline.values())
    gain=learned['top1']-best
    positive=(gain>=.10-1e-12 and p<=.05)
    return {'baseline':baseline,'learned':learned,'gain_vs_best_baseline':gain,
            'null_mean_top1':float(np.mean(null)),'null_top1':null,'empirical_p':p,
            'controls':CONTROLS,'seed':SEED,'alpha':ALPHA,
            'weight_range':[float(w.min()),float(w.max())],
            'scoped_exploratory_gain':bool(positive),'train_pairs':30,'test_prompts':20},w


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(native, report_path, weights_path):
    native, report_path, weights_path=Path(native),Path(report_path),Path(weights_path)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    weights_path.parent.mkdir(parents=True,exist_ok=True)
    report={'schema':'V13_RUN621_B2_DIAGONAL_READOUT_V1','status':'INCOMPLETE',
            'evidence_level':'RETROSPECTIVE_PRIOR_LINUX_NATIVE_STATES_OFFLINE_HEAD_ONLY',
            'original_states_sha256':PINS['614']['states'],
            'original_report_sha256':PINS['614']['report'],
            'native_inference_new':False,'native_body_training':False,
            'receiver_injection_authority':0,'head_activation_authority':0,
            'jepa_weight':0,'gates':GATES,
            'canonical_architecture_complete':False,'user_full_scope_complete':False}
    def save():
        tmp=report_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        os.replace(tmp,report_path)
    save()
    try:
        x,y,ids,train,test=load(native,'614')
        result,w=evaluate(y,ids,train,test)
        with tempfile.NamedTemporaryFile(dir=weights_path.parent,suffix='.npz',delete=False) as f:
            tmp=Path(f.name)
            np.savez_compressed(f,weights=w)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,weights_path)
        report.update(result,weights_sha256=sha(weights_path),
                      weights_bytes=weights_path.stat().st_size,
                      status='SCOPED_EXPLORATORY_B2_GAIN' if result['scoped_exploratory_gain'] else 'NO_B2_READOUT_GAIN')
        save()
        return report
    except BaseException as exc:
        report.update(status='ERROR',error_type=type(exc).__name__,error=str(exc)[:300])
        save()
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--native',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--weights',required=True)
    a=p.parse_args()
    report=run(a.native,a.out,a.weights)
    print(json.dumps({'status':report['status'],'baseline':report['baseline'],
                      'learned':report['learned'],'empirical_p':report['empirical_p']}))