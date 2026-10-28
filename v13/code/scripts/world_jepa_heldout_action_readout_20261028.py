"""Train-correct, fixed-readout heldout-action sensitivity for World-JEPA.

Independent SHADOW research; no runtime hook, model persistence, private IDs,
native inference or age/gate promotion. Original registered probes unchanged.
"""
import argparse
import json
import sys

import numpy as np

from scripts import world_jepa_action_permutation_control as controls
from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_fair_baseline as fair
from scripts import world_jepa_incremental_probe as original
from v13 import world_jepa as wj

SEEDS = fair.SEEDS
STEPS = fair.STEPS
ENSEMBLE = fair.ENSEMBLE
LAMBDA = fair.LAMBDA


def _frozen_readout(dtr, dte, ztr, zte, zrow, zcol, ytr, yte):
    """Fit ONE outcome ridge on correct training actions; reuse all weights."""
    train, correct = original._standardize_train_only(ztr, zte)
    _, wrong_row = original._standardize_train_only(ztr, zrow)
    _, wrong_col = original._standardize_train_only(ztr, zcol)
    weights = bridge._ridge(np.c_[dtr, train], ytr, LAMBDA)
    return {
        'correct': bridge._mae(np.c_[dte, correct] @ weights, yte),
        'heldout_row_mismatch': bridge._mae(np.c_[dte, wrong_row] @ weights, yte),
        'heldout_column_mismatch': bridge._mae(np.c_[dte, wrong_col] @ weights, yte),
    }


def run_rows(rows, steps=STEPS):
    if type(steps) is not int or not 0 <= steps <= STEPS:
        raise ValueError('Invalid registered World-JEPA training step count')
    data = bridge.make_dataset(rows)
    tr, te = data['train'], data['heldout']
    X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
    _, row_mismatch = controls.row_shift_actions(A, tr, te)
    col_mismatch = np.roll(A[te], 1, axis=1)
    row_changed = float(np.mean(np.any(row_mismatch != A[te], axis=1)))
    col_changed = float(np.mean(np.any(col_mismatch != A[te], axis=1)))
    if row_changed <= 0 or col_changed <= 0:
        raise ValueError('Heldout action mismatch control has no changed rows')
    if not np.array_equal(row_mismatch.sum(0), A[te].sum(0)):
        raise ValueError('Heldout row permutation changed action marginals')

    direct = np.c_[np.ones(len(X)), X[:, :4], A]
    dtr, dte = fair._scaled_direct(direct[tr], direct[te])
    direct_weights = bridge._ridge(dtr, Y[tr], LAMBDA)
    direct_mae = bridge._mae(dte @ direct_weights, Y[te])

    per_seed = []
    for seed in SEEDS:
        model = wj.WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(
            X[tr], A[tr], X2[tr], steps=steps)
        ztr, _ = model.predict(X[tr], A[tr])
        zte, _ = model.predict(X[te], A[te])
        zrow, _ = model.predict(X[te], row_mismatch)
        zcol, _ = model.predict(X[te], col_mismatch)
        score = _frozen_readout(dtr, dte, ztr, zte, zrow, zcol, Y[tr], Y[te])
        per_seed.append({
            'seed': seed, **score,
            'gain_vs_direct': float(direct_mae['pooled'] - score['correct']['pooled']),
            'gain_vs_heldout_row_mismatch': float(
                score['heldout_row_mismatch']['pooled'] - score['correct']['pooled']),
            'gain_vs_heldout_column_mismatch': float(
                score['heldout_column_mismatch']['pooled'] - score['correct']['pooled']),
        })
    return {
        'scope': 'WORLD_JEPA_FIXED_READOUT_HELDOUT_ACTION_ABLATION',
        'evidence_level': 'SYNTHETIC_OR_OBSERVED_DIGITAL_SHADOW_ONLY_NO_CAUSAL_PROOF',
        'source_sha256': data['source_sha256'],
        'train_ids_sha256': data['train_ids_sha256'],
        'heldout_ids_sha256': data['heldout_ids_sha256'],
        'n': len(rows), 'train_n': len(tr), 'heldout_n': len(te),
        'model_revision': wj.REVISION, 'seeds': list(SEEDS),
        'steps': steps, 'ensemble': ENSEMBLE, 'ridge_lambda': LAMBDA,
        'readout_frozen_for_heldout_controls': True,
        'model_and_readout_train_actions_correct': True,
        'heldout_row_shift': 1,
        'heldout_row_mismatch_changed_fraction': row_changed,
        'heldout_column_mismatch_changed_fraction': col_changed,
        'heldout_row_marginals_preserved': True,
        'scaled_direct_ridge_mae': direct_mae, 'per_seed': per_seed,
        'runtime_wired': False, 'model_weights_persisted': False,
        'utility_proven': False, 'age_authority': 0,
        'negative_gates_unchanged': bridge.NEGATIVE_GATES,
    }


def main(argv=None, stdout=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-smoke', action='store_true')
    parser.add_argument('--steps', type=int, default=STEPS)
    args = parser.parse_args(argv)
    if not args.synthetic_smoke:
        raise ValueError('Explicit synthetic-only mode required')
    report = run_rows(bridge.synthetic_fixture(n=64, seed=20261027),
                      steps=args.steps)
    out = sys.stdout if stdout is None else stdout
    out.write(json.dumps(report, sort_keys=True, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
