"""Read-only digital action/outcome World-JEPA SHADOW research bridge.

No runtime hook, no model weight persistence, no private row export, no Age authority.
The post-action packet is an observed *outcome*, not a future world state.
Prereg: docs/proofs/continuation-20261027/world-jepa-digital-shadow/PREREG.md.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import tempfile

import numpy as np
from v13 import world_model as wm
from v13 import world_jepa as wj

MIN_ROWS = 32
MAX_ROWS = wm.MAX_ROWS
SEEDS = (3, 7)
STEPS = 400
ENSEMBLE = 3
READOUT_LAMBDA = .1
BASELINE_LAMBDA = .01
NEGATIVE_GATES = {
    'LP1': 'NO_ATTRIBUTABLE_GAIN', 'LP2': 'ALIGNS_NO_GAIN',
    'BJ1': 'NO_SIGNAL', 'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
    'jepa_weight': 0, 'age_authority': 0, 'redmi_measured': False,
    'whole_system_complete': False,
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def _finite_vec(value, size):
    try:
        if (not isinstance(value, (list, tuple, np.ndarray))
                or np.asarray(value).shape != (size,)):
            return None
        raw = list(value)
        if any(isinstance(x, (bool, np.bool_)) or
               not isinstance(x, (int, float, np.integer, np.floating)) for x in raw):
            return None
        v = np.asarray(raw, dtype=np.float64)
        return v if np.isfinite(v).all() else None
    except (TypeError, ValueError, OverflowError):
        return None


def make_dataset(rows):
    """Strict observed action/outcome packet; return no raw source text or IDs."""
    if not isinstance(rows, (list, tuple)) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise ValueError('Invalid observed transition count')
    ids, source = [], []
    x, x2, a, y, action_index = [], [], [], [], []
    for row in rows:
        if type(row) is not dict:
            raise ValueError('Invalid observed transition row')
        rid = row.get('action_id')
        if (type(rid) not in (str, int) or
                (type(rid) is str and (not rid or len(rid) > 128))):
            raise ValueError('Invalid observed action identity')
        if rid in ids:
            raise ValueError('Duplicate observed action identity')
        state = _finite_vec(row.get('s'), 4)
        outcome = _finite_vec(row.get('y'), 3)
        route = row.get('a')
        if (state is None or outcome is None or type(route) is not str
                or route not in wm.ACTIONS):
            raise ValueError('Invalid observed state, route or outcome')
        if (state[0] < 0 or not 0 <= state[1] <= 1
                or np.any(np.abs(state[2:]) > 1.000001)
                or outcome[0] < 0 or outcome[1] not in (0., 1.)
                or outcome[2] < 0):
            raise ValueError('Out-of-domain observed transition')
        idx = wm.ACTIONS.index(route)
        pre = np.r_[state, np.zeros(4, dtype=float)]
        post = np.r_[state, outcome, [1.]]
        ids.append(rid)
        source.append({'id': rid, 's': state.tolist(), 'a': route, 'y': outcome.tolist()})
        x.append(pre)
        x2.append(post)
        a.append(np.eye(4)[idx])
        y.append(outcome)
        action_index.append(idx)
    X, X2, A, Y = (np.asarray(t, dtype=np.float64) for t in (x, x2, a, y))
    if X.shape != (len(rows), 8) or X2.shape != X.shape or A.shape != (len(rows), 4):
        raise ValueError('Invalid digital packet tensor shapes')
    train, test = wm._split(len(rows))
    if len(train) < 2 or len(test) < 2 or set(train) & set(test):
        raise ValueError('Invalid digital train/heldout split')
    return {
        'X': X, 'X2': X2, 'A': A, 'Y': Y,
        'action_index': np.asarray(action_index, dtype=np.int64),
        'train': np.asarray(train, dtype=np.int64),
        'heldout': np.asarray(test, dtype=np.int64),
        'source_sha256': _digest(source),
        'train_ids_sha256': _digest([ids[i] for i in train]),
        'heldout_ids_sha256': _digest([ids[i] for i in test]),
        'counts': {name: int(np.sum(np.asarray(action_index) == k))
                   for k, name in enumerate(wm.ACTIONS)},
    }


def _ridge(X, Y, lam):
    if (X.ndim != 2 or Y.ndim != 2 or X.shape[0] != Y.shape[0]
            or not np.isfinite(X).all() or not np.isfinite(Y).all()
            or not math.isfinite(lam) or lam <= 0):
        raise ValueError('Invalid readout inputs')
    weights = np.linalg.solve(X.T @ X + lam*np.eye(X.shape[1]), X.T @ Y)
    if not np.isfinite(weights).all():
        raise ValueError('Nonfinite readout')
    return weights


def _mae(pred, truth):
    if (pred.shape != truth.shape or pred.ndim != 2 or pred.shape[1] != 3
            or not np.isfinite(pred).all() or not np.isfinite(truth).all()):
        raise ValueError('Invalid heldout outcome prediction')
    values = np.mean(np.abs(pred-truth), axis=0)
    return {'duration': float(values[0]), 'success': float(values[1]),
            'output_chars': float(values[2]), 'pooled': float(values.mean())}


def score_fitted(model, data):
    """No heldout target is consumed until scoring; readout uses train targets only."""
    tr, te = data['train'], data['heldout']
    X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
    ztrain = model.latent(X2[tr], target=True)
    readout = _ridge(np.c_[np.ones(len(tr)), ztrain], Y[tr], READOUT_LAMBDA)
    mean, spread = model.predict(X[te], A[te])
    if (mean.shape != (len(te), wj.Z) or spread.shape != (len(te),)
            or not np.isfinite(mean).all() or not np.isfinite(spread).all()):
        raise ValueError('Invalid heldout JEPA prediction')
    pred = np.c_[np.ones(len(te)), mean] @ readout
    wrong = np.eye(len(wm.ACTIONS))[(data['action_index'][te]+1) % len(wm.ACTIONS)]
    wrong_mean = model.predict(X[te], wrong)[0]
    wrong_pred = np.c_[np.ones(len(te)), wrong_mean] @ readout
    return {'jepa_readout_mae': _mae(pred, Y[te]),
            'wrong_action_mae': _mae(wrong_pred, Y[te]),
            'heldout_mean_spread': float(np.mean(spread))}


def run_transitions(rows):
    data = make_dataset(rows)
    tr, te = data['train'], data['heldout']
    X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
    direct_x = np.c_[np.ones(len(X)), X[:, :4], A]
    direct_w = _ridge(direct_x[tr], Y[tr], BASELINE_LAMBDA)
    direct = _mae(direct_x[te] @ direct_w, Y[te])
    constant = _mae(np.tile(Y[tr].mean(0), (len(te), 1)), Y[te])
    results = []
    for seed in SEEDS:
        model = wj.WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(
            X[tr], A[tr], X2[tr], steps=STEPS)
        results.append({'seed': seed, **score_fitted(model, data)})
    return {
        'scope': 'OBSERVED_DIGITAL_OUTCOME_SHADOW_NOT_NEXT_WORLD_STATE',
        'evidence_level': 'RESEARCH_ONLY_NO_PRIVATE_STORE_PROOF',
        'source_sha256': data['source_sha256'],
        'train_ids_sha256': data['train_ids_sha256'],
        'heldout_ids_sha256': data['heldout_ids_sha256'],
        'n': len(rows), 'train_n': len(tr), 'heldout_n': len(te),
        'action_counts': data['counts'],
        'model_revision': wj.REVISION,
        'model_seeds': list(SEEDS), 'steps': STEPS, 'ensemble': ENSEMBLE,
        'readout_lambda': READOUT_LAMBDA, 'baseline_lambda': BASELINE_LAMBDA,
        'direct_ridge_mae': direct, 'train_mean_mae': constant,
        'per_seed': results,
        'utility_proven': False, 'runtime_wired': False,
        'model_weights_persisted': False,
        'negative_gates_unchanged': NEGATIVE_GATES,
    }


def run_store(store):
    """Read-only existing finalized action transitions; never persist predictions."""
    return run_transitions(wm.transitions(store))


def synthetic_fixture(n=64, seed=20261027):
    if n < MIN_ROWS or n > MAX_ROWS:
        raise ValueError('Invalid synthetic fixture size')
    rng = random.Random(seed)
    out = []
    for i in range(n):
        route = wm.ACTIONS[i % len(wm.ACTIONS)]
        s = [rng.uniform(.1, 1.5), rng.choice([0., .5, 1.]),
             math.sin(i * .12), math.cos(i * .12)]
        y = [max(0., .4 + .18*(i % 4) + rng.uniform(-.1, .1)),
             float((i % 5) != 0), max(0., .6 + .1*(i % 4) + rng.uniform(-.1, .1))]
        out.append({'action_id': 'synthetic-' + str(i), 's': s, 'a': route, 'y': y})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic-smoke', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.synthetic_smoke:
        raise ValueError('Only explicit --synthetic-smoke is allowed on public runner')
    if args.out.exists() or args.out.is_symlink():
        raise ValueError('Refusing to replace existing synthetic report')
    report = run_transitions(synthetic_fixture())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                     dir=args.out.parent, prefix='.digital-shadow-',
                                     delete=False) as f:
        json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
        temp_name = f.name
    os.replace(temp_name, args.out)
    dfd = os.open(args.out.parent, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    print(json.dumps({'scope': report['scope'], 'n': report['n'],
                      'seeds': report['model_seeds'], 'out': str(args.out)}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
