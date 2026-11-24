"""Train-only incremental outcome readout on frozen World-JEPA SHADOW; synthetic CLI.

No private store, runtime hook, model weight persistence, tool use or Age authority.
This is an ablation of *additional* predicted-latent signal beyond direct ridge.
"""
import argparse
import json
import sys

import numpy as np
from scripts import world_jepa_digital_shadow as bridge
from v13 import world_jepa as wj

SEEDS = (3, 7)
STEPS = 400
ENSEMBLE = 3
LAMBDA = bridge.BASELINE_LAMBDA
PROJECTION_SEED = 20261027


def _standardize_train_only(train, heldout):
    """Fit all scaling on TRAIN; never use heldout rows to calibrate features."""
    train = np.asarray(train, dtype=np.float64)
    heldout = np.asarray(heldout, dtype=np.float64)
    if (train.ndim != 2 or heldout.ndim != 2 or train.shape[1] != wj.Z
            or heldout.shape[1] != wj.Z or len(train) < 2
            or not np.isfinite(train).all() or not np.isfinite(heldout).all()):
        raise ValueError('Invalid predicted-latent features')
    mean = train.mean(0)
    sd = train.std(0) + 1e-3
    return (train - mean) / sd, (heldout - mean) / sd


def _augment_score(direct_train, direct_heldout, latent_train, latent_heldout,
                   targets_train, targets_heldout):
    ztr, zte = _standardize_train_only(latent_train, latent_heldout)
    w = bridge._ridge(np.c_[direct_train, ztr], targets_train, LAMBDA)
    pred = np.c_[direct_heldout, zte] @ w
    return bridge._mae(pred, targets_heldout)


def run_probe(rows, steps=STEPS):
    if type(steps) is not int or not 0 <= steps <= STEPS:
        raise ValueError('Invalid preregistered synthetic step count')
    data = bridge.make_dataset(rows)
    tr, te = data['train'], data['heldout']
    X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
    direct = np.c_[np.ones(len(X)), X[:, :4], A]
    dtr, dte = direct[tr], direct[te]
    direct_w = bridge._ridge(dtr, Y[tr], LAMBDA)
    direct_mae = bridge._mae(dte @ direct_w, Y[te])
    results = []
    for seed in SEEDS:
        model = wj.WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(
            X[tr], A[tr], X2[tr], steps=steps)
        ztr, _ = model.predict(X[tr], A[tr])
        zte, _ = model.predict(X[te], A[te])
        augmented = _augment_score(dtr, dte, ztr, zte, Y[tr], Y[te])

        wrong = np.roll(A, 1, axis=1)
        zwtr, _ = model.predict(X[tr], wrong[tr])
        zwte, _ = model.predict(X[te], wrong[te])
        wrong_score = _augment_score(dtr, dte, zwtr, zwte, Y[tr], Y[te])

        # A same-width feature control carrying no information beyond direct.
        rng = np.random.default_rng(PROJECTION_SEED + seed)
        projection = rng.normal(size=(direct.shape[1], wj.Z)) / np.sqrt(direct.shape[1])
        random_score = _augment_score(
            dtr, dte, dtr @ projection, dte @ projection, Y[tr], Y[te])
        results.append({
            'seed': seed,
            'augmented_mae': augmented,
            'wrong_action_augmented_mae': wrong_score,
            'direct_projection_augmented_mae': random_score,
            'pooled_gain_vs_direct': float(direct_mae['pooled'] - augmented['pooled']),
        })
    return {
        'scope': 'WORLD_JEPA_INCREMENTAL_DIGITAL_OUTCOME_SHADOW',
        'evidence_level': 'SYNTHETIC_RESEARCH_ONLY_NOT_REAL_WORLD_UTILITY',
        'source_sha256': data['source_sha256'],
        'train_ids_sha256': data['train_ids_sha256'],
        'heldout_ids_sha256': data['heldout_ids_sha256'],
        'n': len(rows), 'train_n': len(tr), 'heldout_n': len(te),
        'model_revision': wj.REVISION, 'seeds': list(SEEDS),
        'steps': steps, 'ensemble': ENSEMBLE, 'ridge_lambda': LAMBDA,
        'direct_ridge_mae': direct_mae, 'per_seed': results,
        'runtime_wired': False, 'model_weights_persisted': False,
        'utility_proven': False, 'age_authority': 0,
        'negative_gates_unchanged': bridge.NEGATIVE_GATES,
    }


def main(argv=None, stdout=None):
    parser = argparse.ArgumentParser(description='Synthetic-only incremental World-JEPA readout')
    parser.add_argument('--synthetic-smoke', action='store_true')
    args = parser.parse_args(argv)
    if not args.synthetic_smoke:
        raise ValueError('Only explicit synthetic smoke is allowed')
    report = run_probe(bridge.synthetic_fixture(n=64, seed=20261027))
    out = sys.stdout if stdout is None else stdout
    out.write(json.dumps(report, sort_keys=True, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
