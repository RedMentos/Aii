"""Preregistered World-JEPA action-row permutation control; synthetic research only.

Unlike a bijective action-column rotation, rotating *rows* breaks which
observed action belongs to which transition while preserving split marginals.
No model/seed/cohort changes, private data, weights, or runtime authority.
"""
import json
import sys

import numpy as np

from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_fair_baseline as fair
from v13 import world_jepa as wj

SEEDS = fair.SEEDS
STEPS = fair.STEPS
ENSEMBLE = fair.ENSEMBLE
LAMBDA = fair.LAMBDA


def row_shift_actions(A, train, heldout):
    """Fixed shift by one row *within* each split; no heldout mixing."""
    A = np.asarray(A, dtype=np.float64)
    train, heldout = np.asarray(train), np.asarray(heldout)
    if (A.ndim != 2 or A.shape[1] != 4 or not np.isfinite(A).all()
            or not np.all((A == 0.) | (A == 1.))
            or not np.all(A.sum(axis=1) == 1.)
            or any(x.ndim != 1 or len(x) < 2 for x in (train, heldout))
            or not np.issubdtype(train.dtype, np.integer)
            or not np.issubdtype(heldout.dtype, np.integer)
            or any(np.any(x < 0) or np.any(x >= len(A))
                   or len(np.unique(x)) != len(x) for x in (train, heldout))
            or np.intersect1d(train, heldout).size):
        raise ValueError('Invalid split/action permutation input')
    a_train, a_heldout = A[train], A[heldout]
    shifted_train = np.roll(a_train, 1, axis=0)
    shifted_heldout = np.roll(a_heldout, 1, axis=0)
    # Counts are exactly conserved separately, even with repeated actions.
    if (not np.array_equal(shifted_train.sum(0), a_train.sum(0))
            or not np.array_equal(shifted_heldout.sum(0), a_heldout.sum(0))):
        raise ValueError('Action permutation changed split marginals')
    return shifted_train, shifted_heldout


def run_rows(rows, steps=STEPS):
    if type(steps) is not int or not 0 <= steps <= STEPS:
        raise ValueError('Invalid preregistered World-JEPA step count')
    data = bridge.make_dataset(rows)
    tr, te = data['train'], data['heldout']
    X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
    shifted_tr, shifted_te = row_shift_actions(A, tr, te)

    direct = np.c_[np.ones(len(X)), X[:, :4], A]
    dtr, dte = fair._scaled_direct(direct[tr], direct[te])
    direct_w = bridge._ridge(dtr, Y[tr], LAMBDA)
    direct_mae = bridge._mae(dte @ direct_w, Y[te])

    state = np.c_[np.ones(len(X)), X[:, :4]]
    str_, ste = fair._scaled_direct(state[tr], state[te])
    state_w = bridge._ridge(str_, Y[tr], LAMBDA)
    state_mae = bridge._mae(ste @ state_w, Y[te])

    # Fixed old control is retained for comparability but not called a shuffle.
    column_rotated = np.roll(A, 1, axis=1)
    arms = []
    for seed in SEEDS:
        model = wj.WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(
            X[tr], A[tr], X2[tr], steps=steps)
        ztr, _ = model.predict(X[tr], A[tr])
        zte, _ = model.predict(X[te], A[te])
        correct = fair._score(dtr, dte, ztr, zte, Y[tr], Y[te])

        zrow_tr, _ = model.predict(X[tr], shifted_tr)
        zrow_te, _ = model.predict(X[te], shifted_te)
        row_shifted = fair._score(dtr, dte, zrow_tr, zrow_te, Y[tr], Y[te])

        zcol_tr, _ = model.predict(X[tr], column_rotated[tr])
        zcol_te, _ = model.predict(X[te], column_rotated[te])
        column_rotated_mae = fair._score(
            dtr, dte, zcol_tr, zcol_te, Y[tr], Y[te])
        arms.append({
            'seed': seed,
            'correct_latent_mae': correct,
            'row_shifted_latent_mae': row_shifted,
            'column_rotated_latent_mae': column_rotated_mae,
            'correct_gain_vs_row_shifted': float(
                row_shifted['pooled'] - correct['pooled']),
            'correct_gain_vs_column_rotated': float(
                column_rotated_mae['pooled'] - correct['pooled']),
            'correct_gain_vs_scaled_direct': float(
                direct_mae['pooled'] - correct['pooled']),
        })

    return {
        'scope': 'WORLD_JEPA_ACTION_ROW_PERMUTATION_SYNTHETIC_RESEARCH',
        'evidence_level': 'SYNTHETIC_ONLY_NO_ACTION_CAUSALITY_PROOF',
        'source_sha256': data['source_sha256'],
        'train_ids_sha256': data['train_ids_sha256'],
        'heldout_ids_sha256': data['heldout_ids_sha256'],
        'n': len(rows), 'train_n': len(tr), 'heldout_n': len(te),
        'seeds': list(SEEDS), 'steps': steps, 'ensemble': ENSEMBLE,
        'ridge_lambda': LAMBDA, 'model_revision': wj.REVISION,
        'row_shift': 1, 'row_shift_split_isolated': True,
        'row_shift_train_changed_fraction': float(
            np.mean(np.any(shifted_tr != A[tr], axis=1))),
        'row_shift_heldout_changed_fraction': float(
            np.mean(np.any(shifted_te != A[te], axis=1))),
        'scaled_state_only_mae': state_mae,
        'scaled_state_action_direct_mae': direct_mae,
        'per_seed': arms,
        'runtime_wired': False, 'model_weights_persisted': False,
        'utility_proven': False, 'age_authority': 0,
        'negative_gates_unchanged': bridge.NEGATIVE_GATES,
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic-smoke', action='store_true')
    args = parser.parse_args(argv)
    if not args.synthetic_smoke:
        raise ValueError('Explicit synthetic-only mode required')
    result = run_rows(bridge.synthetic_fixture(n=64, seed=20261027))
    sys.stdout.write(json.dumps(result, sort_keys=True, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
