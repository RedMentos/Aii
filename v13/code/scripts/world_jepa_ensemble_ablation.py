#!/usr/bin/env python3
"""Frozen v2 World-JEPA ensemble-mean ablation, read-only and authority zero.

This is bound to ONE already closed real Linux file-world checkpoint and three
persisted holdouts. It does not train, recalibrate, collect actions or replace
the existing first-predictor runtime behavior.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from scripts.world_jepa_holdout_utility import _training, verify_holdout_export
from v13.world_jepa_shadow_probe import _json_file

SCHEMA = 'V13_WORLD_JEPA_FROZEN_ENSEMBLE_ABLATION_V1'
CHECKPOINT_SHA256 = '955ee6efd0eaf2f85803297773ad016d54a33c7c707cd0406b3ceb23739d5e51'
TRAINING_MANIFEST_SHA256 = 'dbf68c92ac3f371432cd0f9d3b94a42ca7633ed71e318db72d42b3aa27dde96d'
TRAINING_SOURCE_SHA256 = 'bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770'
HOLDOUTS = (
    ('heldout', 313, '709fed825ed1636a618871cc5294085a3a58f08a39913c67cb2dc8c16960c509'),
    ('heldout314', 314, '499aeaf2ddb05d4531aa32a2715a76bdabed2539121f7d4e663cc9d415cf1b07'),
    ('heldout315', 315, '872ea08ad70f7c2a9bb8c1db63c01251a9accb8468b3c088e48cd135446b02c9'),
)
CLAIM_LIMIT = ('Exploratory frozen Linux synthetic-content file-world ensemble ablation; '
               'no training, causal/semantic utility, Redmi or decision authority')


def _sha(path):
    with Path(path).open('rb') as stream:
        h = hashlib.sha256()
        while True:
            b = stream.read(1024 * 1024)
            if not b:
                return h.hexdigest()
            h.update(b)


def _encode(weights, prefix, x):
    h = np.tanh(x @ weights[prefix + '_W1'].T + weights[prefix + '_b1'])
    return h @ weights[prefix + '_W2'].T + weights[prefix + '_b2']


def _predict(weights, index, z, a):
    u = np.concatenate([z, a], axis=1)
    h = np.tanh(u @ weights[f'pred{index}_P1'].T + weights[f'pred{index}_c1'])
    return z + h @ weights[f'pred{index}_P2'].T + weights[f'pred{index}_c2']


def evaluate_frozen(model, weights, rows):
    """Independent NumPy weight-path reference; first member checked against V13."""
    if len(model.preds) != 2 or model.S != 6 or len(model.mu) != 10:
        raise ValueError('Expected exact frozen two-member six-slot checkpoint')
    sums = np.zeros(4, dtype=np.float64)
    mean_beats_first = mean_beats_identity = 0
    n = len(rows)
    for lo in range(0, n, 16):
        chunk = rows[lo:lo + 16]
        x = np.asarray([r['x'] for r in chunk], dtype=np.float64).reshape(-1, 6, 10)
        x2 = np.asarray([r['x2'] for r in chunk], dtype=np.float64).reshape(-1, 6, 10)
        a = np.zeros((len(chunk), 6, 6), dtype=np.float64)
        a[:, :, 5] = 1.
        for j, row in enumerate(chunk):
            action = row['a']
            if type(action) is not int or not 0 <= action <= 30:
                raise ValueError('Invalid frozen file-world action')
            if action != 30:
                op, slot = divmod(action, 6)
                a[j, slot] = 0.
                a[j, slot, op] = 1.
        z = _encode(weights, 'enc', ((x - weights['mu']) / weights['sd']).reshape(-1, 10))
        target = _encode(weights, 'tgt', ((x2 - weights['mu']) / weights['sd']).reshape(-1, 10))
        identity = _encode(weights, 'tgt', ((x - weights['mu']) / weights['sd']).reshape(-1, 10))
        aa = a.reshape(-1, 6)
        first = _predict(weights, 0, z, aa)
        second = _predict(weights, 1, z, aa)
        mean = (first + second) / 2.
        # Cross-check this independent NumPy reference with the V13 loaded
        # model; this must remain the existing first-predictor default.
        actual, _ = model.predict(x.reshape(len(chunk), -1), a)
        if not np.allclose(actual.reshape(-1, 8), first, rtol=0., atol=1e-12):
            raise ValueError('Independent first predictor differs from V13 source')
        scale = weights['zsd']
        errors = [np.mean(((v - target) / scale) ** 2, axis=1).reshape(-1, 6)
                  for v in (first, second, mean, identity)]
        if not all(np.isfinite(v).all() and np.all(v >= 0) for v in errors):
            raise ValueError('Nonfinite frozen ablation metric')
        for k, err in enumerate(errors):
            sums[k] += float(err.sum())
        mean_beats_first += int(np.count_nonzero(errors[2].mean(1) < errors[0].mean(1)))
        mean_beats_identity += int(np.count_nonzero(errors[2].mean(1) < errors[3].mean(1)))
    result = {
        'rows': n,
        'first_mse': float(sums[0] / (n * 6)),
        'second_mse': float(sums[1] / (n * 6)),
        'ensemble_mean_mse': float(sums[2] / (n * 6)),
        'identity_mse': float(sums[3] / (n * 6)),
        'fraction_mean_beats_first': mean_beats_first / n,
        'fraction_mean_beats_identity': mean_beats_identity / n,
    }
    if not all(math.isfinite(v) for v in result.values()):
        raise ValueError('Invalid frozen summary')
    return result


def ablate(root):
    """Verify pinned training + three original holdouts, then evaluate without writes."""
    root = Path(root)
    train = root / 'training'
    if _sha(train / 'manifest.json') != TRAINING_MANIFEST_SHA256:
        raise ValueError('Not the exact frozen training manifest')
    train_manifest, model = _training(train, holdout_seed=313)
    if (train_manifest.get('checkpoint_sha256') != CHECKPOINT_SHA256
            or train_manifest.get('source_sha256') != TRAINING_SOURCE_SHA256
            or _sha(train / 'slot-shadow-v2.npz') != CHECKPOINT_SHA256
            or len(model.preds) != 2):
        raise ValueError('Frozen checkpoint or source mismatch')
    with np.load(train / 'slot-shadow-v2.npz', allow_pickle=False) as arrays:
        weights = {name: arrays[name].copy() for name in arrays.files if name != 'meta'}
    per_seed = []
    for folder, seed, pinned_manifest_sha in HOLDOUTS:
        out = root / folder
        if _sha(out / 'manifest.json') != pinned_manifest_sha:
            raise ValueError('Not the exact frozen heldout manifest: ' + folder)
        verified = verify_holdout_export(out, train)
        manifest = _json_file(out / 'manifest.json', 1024 * 1024)
        if manifest.get('holdout_seed') != seed or verified['rows'] != 160:
            raise ValueError('Frozen heldout seed/row mismatch')
        rows = _json_file(out / 'cohort.json', 128 * 1024 * 1024)
        scores = evaluate_frozen(model, weights, rows)
        if (abs(scores['first_mse'] - manifest['metrics']['action_prediction_mse']) > 1e-12
                or abs(scores['identity_mse'] - manifest['metrics']['identity_target_mse']) > 1e-12):
            raise ValueError('Independent NumPy metrics differ from original holdout')
        per_seed.append({'seed': seed, 'manifest_sha256': pinned_manifest_sha,
                         'cohort_sha256': verified['cohort_sha256'], **scores})
    weighted = lambda key: sum(row['rows'] * row[key] for row in per_seed) / sum(row['rows'] for row in per_seed)
    return {
        'schema': SCHEMA,
        'mode': 'SHADOW_ONLY',
        'authority': 0,
        'training_performed': False,
        'checkpoint_sha256': CHECKPOINT_SHA256,
        'training_source_sha256': TRAINING_SOURCE_SHA256,
        'seeds': [r['seed'] for r in per_seed],
        'rows': sum(r['rows'] for r in per_seed),
        'per_seed': per_seed,
        'weighted_first_mse': weighted('first_mse'),
        'weighted_second_mse': weighted('second_mse'),
        'weighted_ensemble_mean_mse': weighted('ensemble_mean_mse'),
        'weighted_identity_mse': weighted('identity_mse'),
        'ensemble_mean_beats_first_seeds': sum(r['ensemble_mean_mse'] < r['first_mse'] for r in per_seed),
        'ensemble_mean_beats_identity_seeds': sum(r['ensemble_mean_mse'] < r['identity_mse'] for r in per_seed),
        'redmi_measured': False,
        'step2': 'UTILITY_FAIL',
        'b3': 'L1_FAIL',
        'body_jepa': 'UNAVAILABLE',
        'jepa_weight': 0,
        'canonical_architecture_complete': False,
        'user_full_scope_complete': False,
        'claim_limit': CLAIM_LIMIT,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='V13 frozen World-JEPA ensemble mean ablation')
    parser.add_argument('--frozen-root', required=True)
    args = parser.parse_args(argv)
    print(json.dumps(ablate(args.frozen_root), sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
