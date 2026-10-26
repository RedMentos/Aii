"""Run615 exploratory, source-bound native B1->B2 readout; never a body update.

Only consumes previously SHA-closed read-only Linux-native states. Posthoc to
both original cohorts. The trainable linear heads cannot inject into a receiver.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

PINS = {
    '608': {'states': 'c6e6a7a6521d14c90805a996e723e9cd7716cd6ba6d13577480eff30349625ca',
            'report': '51a7fb12170ea4580b1015076449765bb9ff5659a3335e9a68b543860a5dc8b9',
            'cohort': 'f452bdf80bb8d8a784c1909c98e310041d3157aa'},
    '614': {'states': 'cb535df87749c0cf5d698d26268e6b03f3d6f57690b95434aebc6c875a3ea189',
            'report': '42ac6d22ef6c9cc59622572f233b2e7b83094af7a9fdd227cfe2fff15e0666e4',
            'cohort': '7068267d41a1719abea3a54c84b1d0223444df1d'},
}
MODEL_SHA = {'B1_DETAIL': 'bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1',
             'B2_GIST': '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'}
GATES = {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL', 'Body_JEPA': 'UNAVAILABLE',
         'jepa_weight': 0, 'Redmi': 'UNMEASURED', 'V13': 'INCOMPLETE'}
FIELDS = {'x_b1', 'y_b2', 'prompt_ids', 'train_idx', 'test_idx'}
PROMPT = re.compile(r'^[a-z]+-[1-9][0-9]*-[AB]$')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def validate(x, y, ids, train, test):
    x, y = np.asarray(x), np.asarray(y)
    if x.shape != (80, 2048) or y.shape != (80, 1024):
        raise ValueError('native dimension/row mismatch')
    if x.dtype.kind != 'f' or y.dtype.kind != 'f' or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('nonfinite/nonfloat native states')
    if (np.linalg.norm(x, axis=1) < 1e-10).any() or (np.linalg.norm(y, axis=1) < 1e-10).any():
        raise ValueError('zero native states')
    if len(ids) != 80 or not all(isinstance(z, str) and PROMPT.fullmatch(z) for z in ids) or len(set(ids)) != 80:
        raise ValueError('invalid prompt IDs')
    train, test = np.asarray(train), np.asarray(test)
    if train.dtype.kind not in 'iu' or test.dtype.kind not in 'iu' or train.shape != (60,) or test.shape != (20,):
        raise ValueError('invalid train/test indices')
    if sorted([int(z) for z in np.r_[train, test]]) != list(range(80)):
        raise ValueError('train/test overlap or missing rows')
    groups = {z.rsplit('-', 1)[0] for z in ids}
    if len(groups) != 40 or any(sum(k.rsplit('-', 1)[0] == g for k in ids) != 2 for g in groups):
        raise ValueError('unpaired facts')
    if any((z[:-1] + ('B' if z.endswith('A') else 'A')) not in ids for z in ids):
        raise ValueError('missing opposite paraphrase')
    if any((ids[i].rsplit('-', 1)[0] in {ids[j].rsplit('-', 1)[0] for j in test}) for i in train):
        raise ValueError('fact leakage train/test')
    return x.astype(np.float64), y.astype(np.float64), list(ids), train, test


def load(folder, run):
    folder = Path(folder)
    a = folder / ('RUN' + run + '_STATES.npz')
    b = folder / ('RUN' + run + '_NATIVE_REPORT.json')
    if sha(a) != PINS[run]['states'] or sha(b) != PINS[run]['report']:
        raise ValueError('native artifact hash mismatch')
    report = json.loads(b.read_text())
    if (report.get('cohort_blob') != PINS[run]['cohort'] or report.get('gates') != GATES or
        report.get('evidence_level') != 'LINUX_NATIVE_PAIRED_READONLY' or
        report.get('can_latent_inject') is not False or report.get('no_weight_updates') is not True or
        report.get('canonical_architecture_complete') is not False or
        report.get('states_sha256') != PINS[run]['states'] or
        any(report['models'][role]['sha256'] != pin for role, pin in MODEL_SHA.items())):
        raise ValueError('native authority/cohort/model mismatch')
    with np.load(a, allow_pickle=False) as npz:
        if set(npz.files) != FIELDS:
            raise ValueError('unexpected NPZ fields')
        return validate(*(npz[k] for k in ('x_b1', 'y_b2', 'prompt_ids', 'train_idx', 'test_idx')))


def unit(x):
    x = np.asarray(x, dtype=np.float64)
    norm = np.linalg.norm(x, axis=1, keepdims=True)
    if not np.isfinite(x).all() or (norm < 1e-10).any():
        raise ValueError('invalid vector')
    return x / norm


def fit_ridge(x, y, alpha=1.0):
    x, y = unit(x), unit(y)
    mx, my = x.mean(0), y.mean(0)
    xc, yc = x - mx, y - my
    dual = np.linalg.solve(xc @ xc.T + alpha * np.eye(len(xc)), yc)
    return mx, my, xc.T @ dual


def predict_ridge(fit, x):
    mx, my, w = fit
    return unit((unit(x) - mx) @ w)


def fit_procrustes(x, y, rank=32):
    x, y = unit(x), unit(y)
    mx, my = x.mean(0), y.mean(0)
    xc, yc = x - mx, y - my
    _, _, vx = np.linalg.svd(xc, full_matrices=False)
    _, _, vy = np.linalg.svd(yc, full_matrices=False)
    px, py = vx[:rank].T, vy[:rank].T
    cross = (xc @ px).T @ (yc @ py) + 1e-3 * np.eye(rank)
    u, _, vt = np.linalg.svd(cross, full_matrices=False)
    return mx, my, px, py, u @ vt


def predict_procrustes(fit, x, y):
    mx, my, px, py, w = fit
    return unit((unit(x) - mx) @ px @ w), unit((unit(y) - my) @ py)


def score(query, candidates, ids):
    q, c = unit(query), unit(candidates)
    if len(ids) != len(q) or len(q) != len(c):
        raise ValueError('scoring shape mismatch')
    sim = q @ c.T
    hits, mrr = 0, 0.
    for i, pid in enumerate(ids):
        target = pid[:-1] + ('B' if pid.endswith('A') else 'A')
        j = ids.index(target)
        sim[i, i] = -np.inf
        order = np.argsort(-sim[i], kind='stable')
        rank = int(np.flatnonzero(order == j)[0]) + 1
        hits += rank == 1
        mrr += 1. / rank
    return {'top1': hits / len(ids), 'mrr': mrr / len(ids)}


def evaluate(training, testing, shuffles=50, seed=2026102615):
    tx, ty, _, tr, _ = training
    qx, qy, ids, _, te = testing
    trainx, trainy = tx[tr], ty[tr]
    query, target, test_ids = qx[te], qy[te], [ids[i] for i in te]
    rf = fit_ridge(trainx, trainy)
    ridge = score(predict_ridge(rf, query), unit(unit(target) - rf[1]), test_ids)
    pp = fit_procrustes(trainx, trainy)
    pred, tgt = predict_procrustes(pp, query, target)
    proc = score(pred, tgt, test_ids)
    rng = np.random.default_rng(seed)
    null_r, null_p = [], []
    for _ in range(shuffles):
        shuffled = trainy[rng.permutation(len(trainy))]
        null_r.append(score(predict_ridge(fit_ridge(trainx, shuffled), query), target, test_ids)['top1'])
        a, b = predict_procrustes(fit_procrustes(trainx, shuffled), query, target)
        null_p.append(score(a, b, test_ids)['top1'])
    return {'ridge': ridge, 'procrustes': proc,
            'shuffled': {'n': shuffles, 'ridge_mean': float(np.mean(null_r)), 'procrustes_mean': float(np.mean(null_p)),
                         'ridge_p': (1 + sum(z >= ridge['top1'] for z in null_r)) / (shuffles + 1),
                         'procrustes_p': (1 + sum(z >= proc['top1'] for z in null_p)) / (shuffles + 1)}}


def run(first, second):
    a, b = load(first, '608'), load(second, '614')
    if set(a[2]) & set(b[2]):
        raise ValueError('cross-cohort duplicate prompt IDs')
    te = b[4]
    baseline = {'b1_only': score(unit(unit(b[0][te]) - unit(b[0][b[3]]).mean(0)), unit(unit(b[0][te]) - unit(b[0][b[3]]).mean(0)), [b[2][i] for i in te]),
                'b2_only': score(unit(unit(b[1][te]) - unit(b[1][b[3]]).mean(0)), unit(unit(b[1][te]) - unit(b[1][b[3]]).mean(0)), [b[2][i] for i in te])}
    cross = evaluate(a, b)
    within = evaluate(b, b)
    best = baseline['b2_only']['top1']
    passed = max(cross['ridge']['top1'] if cross['shuffled']['ridge_p'] <= .05 else 0,
                 cross['procrustes']['top1'] if cross['shuffled']['procrustes_p'] <= .05 else 0) >= best + .10
    return {'schema': 'V13_RUN615_CROSSCOHORT_SHADOW_V1', 'status': 'EXPLORATORY_CROSS_BODY_PROXY_GAIN' if passed else 'NO_CROSS_BODY_GAIN',
            'posthoc': True, 'native_inference_new': False, 'native_body_training': False, 'receiver_injection': False,
            'source_artifacts': {'608': PINS['608'], '614': PINS['614']},
            'baseline': baseline, 'cross_cohort_train608_test614': cross, 'within_cohort_train614_test614': within,
            'gates': GATES, 'canonical_architecture_complete': False, 'user_full_scope_complete': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run608', required=True)
    p.add_argument('--run614', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    result = run(args.run608, args.run614)
    Path(args.out).write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(result['status'], result['baseline'], result['cross_cohort_train608_test614'])


if __name__ == '__main__':
    main()