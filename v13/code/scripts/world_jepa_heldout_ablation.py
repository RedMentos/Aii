"""Preregistered WP-Z12b heldout World-JEPA ensemble/action controls.

Research-only synthetic readout, not runtime-wired or Age-authorized.
See docs/proofs/continuation-20261027/world-jepa-heldout/PREREG.md.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile

import numpy as np
from v13 import world_jepa as wj

TRAIN_N, TRAIN_SEED = 1000, 20261027
TEST_N, TEST_SEED = 240, 20261107
TRAIN_SHA = '317410989c41a3e75032dfd02692da7d126596ab2ff350996e7b1b383a055822'
TEST_SHA = '011f122f4290f5b14cae8699841ae477cfcc0837958a0bc30c95e3e1af06b20b'
MODEL_SEEDS = (3, 7, 11)
STEPS = 1000
ENSEMBLE = 3
NEGATIVE_GATES = {
    'LP1': 'NO_ATTRIBUTABLE_GAIN', 'LP2': 'ALIGNS_NO_GAIN',
    'BJ1': 'NO_SIGNAL', 'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
    'jepa_weight': 0, 'age_authority': 0, 'redmi_measured': False,
    'whole_system_complete': False
}


def make_rows(n, seed):
    """Fixed integer-only Python RNG order; never train on heldout rows."""
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        bits = [rng.randrange(2) for _ in range(4)]
        noise = [rng.randrange(-2000, 2001) for _ in range(4)]
        action = rng.randrange(4)
        next_noise = [rng.randrange(-2000, 2001) for _ in range(4)]
        rows.append({'bits': bits, 'noise': noise, 'action': action, 'next_noise': next_noise})
    return rows


def raw_hash(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_rows(rows, n, expected):
    if len(rows) != n or raw_hash(rows) != expected:
        raise ValueError('Preregistered World-JEPA cohort SHA/size mismatch')
    if len({json.dumps(r, sort_keys=True, separators=(',', ':')) for r in rows}) != n:
        raise ValueError('Duplicate World-JEPA source row')
    return True


def arrays(rows):
    n = len(rows)
    bits = np.asarray([r['bits'] for r in rows], dtype=np.float64)
    noise = np.asarray([r['noise'] for r in rows], dtype=np.float64)/1000.
    action = np.asarray([r['action'] for r in rows], dtype=np.int64)
    next_noise = np.asarray([r['next_noise'] for r in rows], dtype=np.float64)/1000.
    X = np.concatenate([bits, noise], axis=1)
    X2 = X.copy()
    X2[np.arange(n), action] = 1. - X[np.arange(n), action]
    X2[:, 4:] = next_noise
    return X, np.eye(4, dtype=np.float64)[action], X2, action


def _mse(predicted, target, train_scale):
    if (predicted.shape != target.shape or train_scale.shape != (predicted.shape[1],)
            or not np.isfinite(predicted).all() or not np.isfinite(target).all()
            or not np.isfinite(train_scale).all() or (train_scale <= 0).any()):
        raise ValueError('Invalid heldout latent score inputs')
    return float(np.mean(((predicted-target)/train_scale)**2))


def score_model(model, X, A, X2, action):
    # Validate indices before NumPy one-hot indexing: -1 otherwise aliases action 3.
    if (not isinstance(action, np.ndarray) or action.ndim != 1
            or action.shape != (len(X),) or action.dtype.kind not in ('i', 'u')
            or (action < 0).any() or (action >= 4).any()):
        raise ValueError('Invalid heldout action indices')
    if (X.ndim != 2 or X.shape[1] != 8 or X2.shape != X.shape
            or A.shape != (len(X), 4) or action.shape != (len(X),)
            or not np.isfinite(X).all() or not np.isfinite(X2).all()
            or not np.array_equal(A, np.eye(4)[action])):
        raise ValueError('Invalid heldout World-JEPA evaluation tensors')
    target = model.latent(X2, target=True)
    z = model.latent(X, target=False)
    mean, spread = model.predict(X, A)
    first = wj.predict(model.preds[0], z, A)[0]
    wrong_action = np.eye(4)[(action+1) % 4]
    wrong_mean = model.predict(X, wrong_action)[0]
    scores = {
        'ensemble_mean_mse': _mse(mean, target, model.zsd),
        'first_member_mse': _mse(first, target, model.zsd),
        'wrong_action_mse': _mse(wrong_mean, target, model.zsd),
        'persistence_mse': _mse(z, target, model.zsd)
    }
    conf, labels = model.confidence(X, A, counts=None)
    if (conf.shape != (len(X),) or not np.isfinite(conf).all()
            or (conf < 0).any() or (conf > 1).any()
            or any(v not in ('MODEL_SIMULATION', 'SIMULATION_UNCERTAIN') for v in labels)):
        raise ValueError('Nonfinite/unbounded heldout confidence')
    if not np.isfinite(spread).all():
        raise ValueError('Nonfinite ensemble disagreement')
    scores['confidence_mean'] = float(conf.mean())
    scores['uncertain_fraction'] = float(labels.count('SIMULATION_UNCERTAIN')/len(labels))
    return scores


def summarize(per_seed):
    if len(per_seed) != len(MODEL_SEEDS) or [r['seed'] for r in per_seed] != list(MODEL_SEEDS):
        raise ValueError('Incomplete/altered registered model seed set')
    keys = ('ensemble_mean_mse', 'first_member_mse', 'wrong_action_mse', 'persistence_mse')
    pooled = {k: float(np.mean([r[k] for r in per_seed])) for k in keys}
    if not all(np.isfinite(v) and v >= 0 for v in pooled.values()):
        raise ValueError('Nonfinite/negative pooled score')
    mean, first, wrong, persistence = (pooled[k] for k in keys)
    ensemble_gate = bool(mean <= .95*first and sum(
        r['ensemble_mean_mse'] < r['first_member_mse'] for r in per_seed) >= 2)
    action_gate = bool(mean <= .90*wrong and mean <= .90*persistence)
    return {
        'pooled': pooled,
        'ensemble_mean_gain_criterion': 'PASS' if ensemble_gate else 'FAIL',
        'synthetic_action_signal_criterion': 'PASS' if action_gate else 'FAIL',
        'gates_are_synthetic_only': True
    }


def run():
    train = make_rows(TRAIN_N, TRAIN_SEED)
    heldout = make_rows(TEST_N, TEST_SEED)
    verify_rows(train, TRAIN_N, TRAIN_SHA)
    verify_rows(heldout, TEST_N, TEST_SHA)
    if set(map(lambda r: json.dumps(r, sort_keys=True, separators=(',', ':')), train)) & set(
            map(lambda r: json.dumps(r, sort_keys=True, separators=(',', ':')), heldout)):
        raise ValueError('Training and heldout source rows overlap')
    X, A, X2, _ = arrays(train)
    Xe, Ae, X2e, acte = arrays(heldout)
    result = []
    for seed in MODEL_SEEDS:
        model = wj.WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(X, A, X2, steps=STEPS)
        result.append({'seed': seed, **score_model(model, Xe, Ae, X2e, acte)})
    return {
        'scope': 'SYNTHETIC_WORLD_JEPA_HELDOUT_ONLY',
        'revision': wj.REVISION,
        'numpy': np.__version__,
        'cohort': {'train_sha256': TRAIN_SHA, 'heldout_sha256': TEST_SHA,
                   'train_n': TRAIN_N, 'heldout_n': TEST_N,
                   'model_seeds': list(MODEL_SEEDS), 'steps': STEPS, 'ensemble': ENSEMBLE},
        'per_seed': result, **summarize(result),
        'negative_gates_unchanged': NEGATIVE_GATES
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--run', action='store_true')
    p.add_argument('--out', required=True)
    args = p.parse_args(argv)
    if not args.run:
        raise ValueError('Explicit --run required for registered research job')
    report = run()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=out.parent,
                                     prefix='.world-jepa-', delete=False) as tmp:
        tmp.write(json.dumps(report, sort_keys=True, indent=2) + '\n')
        tmp.flush(); os.fsync(tmp.fileno())
        name = tmp.name
    os.replace(name, out)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
