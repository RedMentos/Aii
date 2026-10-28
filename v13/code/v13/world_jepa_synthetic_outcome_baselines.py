"""Run54: pinned synthetic-only outcome readouts versus World-JEPA diagnostics.

Linear baselines expose a simpler explanation for synthetic action-conditioned
metrics. No Runtime, Store, real-data fitting, checkpoint or decision authority.
"""
from __future__ import annotations

import copy
import hashlib

import numpy as np

from v13 import world_jepa_action_outcome_shadow_fit as shadow
from v13 import world_model

SCHEMA = 'v13.world_jepa.synthetic_outcome_baselines.v1'
RIDGE_LAMBDA = 0.01
TARGETS = tuple(world_model.TARGETS)


def _ridge_metrics(train_features, holdout_features, train_y, holdout_y):
    """Fit only on train, evaluate only on holdout; no holdout tuning."""
    tr = np.column_stack((np.ones(len(train_features)), train_features))
    ho = np.column_stack((np.ones(len(holdout_features)), holdout_features))
    penalty = np.eye(tr.shape[1], dtype=np.float64) * RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    try:
        weights = np.linalg.solve(tr.T @ tr + penalty, tr.T @ train_y)
        delta = ho @ weights - holdout_y
        by_target = np.mean(delta * delta, axis=0)
    except (np.linalg.LinAlgError, ValueError, FloatingPointError) as exc:
        raise ValueError('RUN54_RIDGE_EVALUATION_FAILED') from exc
    if by_target.shape != (len(TARGETS),) or not np.isfinite(by_target).all():
        raise ValueError('RUN54_NONFINITE_BASELINE')
    return {'overall_mse': float(by_target.mean()),
            'per_target_mse': {name: float(value)
                               for name, value in zip(TARGETS, by_target)}}


def run(bundle, *, approved_shadow_fit=False, source_kind=None,
        seed=11, steps=20, ensemble=2):
    """Return synthetic-only aggregate evidence; no fitted models are exported.

    All source/array and permission gates are inherited from Run51, on a
    private copy. No external Store object is accepted by Run51.
    """
    if type(bundle) is not dict:
        raise ValueError('RUN54_ADAPTER_BUNDLE_REQUIRED')
    try:
        copied = {
            'manifest': copy.deepcopy(bundle.get('manifest')),
            'train': tuple(np.array(v, copy=True) for v in bundle['train']),
            'holdout': tuple(np.array(v, copy=True) for v in bundle['holdout']),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('RUN54_INVALID_ADAPTER_BUNDLE') from exc
    fitted = shadow.run(
        copied, approved_shadow_fit=approved_shadow_fit,
        source_kind=source_kind, seed=seed, steps=steps, ensemble=ensemble)
    prior = fitted['report']
    if prior['status'] != 'SYNTHETIC_SHADOW_ABLATION_ONLY':
        raise ValueError('RUN54_INVALID_PARENT_DIAGNOSTIC')
    x, a, x2 = copied['train']
    hx, ha, hx2 = copied['holdout']
    train_y = x2[:, 4:]
    holdout_y = hx2[:, 4:]
    if train_y.shape[1] != len(TARGETS):
        raise ValueError('RUN54_OUTCOME_DIMENSION_MISMATCH')

    rng = np.random.default_rng(seed ^ 0x543)
    perm = rng.permutation(len(a))
    shuffled = a[perm]
    if np.array_equal(shuffled, a):
        perm = np.roll(np.arange(len(a)), 1)
        shuffled = a[perm]
    if np.array_equal(shuffled, a):
        raise ValueError('RUN54_UNCHANGED_ACTION_CONTROL')
    digest = hashlib.sha256(
        np.ascontiguousarray(perm.astype('<i8')).tobytes()).hexdigest()

    zeros_train = np.empty((len(x), 0), dtype=np.float64)
    zeros_holdout = np.empty((len(hx), 0), dtype=np.float64)
    results = {
        'intercept_only': _ridge_metrics(zeros_train, zeros_holdout,
                                         train_y, holdout_y),
        'state_only': _ridge_metrics(x[:, :4], hx[:, :4],
                                     train_y, holdout_y),
        'state_plus_action': _ridge_metrics(
            np.column_stack((x[:, :4], a)),
            np.column_stack((hx[:, :4], ha)), train_y, holdout_y),
        'shuffled_train_action': _ridge_metrics(
            np.column_stack((x[:, :4], shuffled)),
            np.column_stack((hx[:, :4], ha)), train_y, holdout_y),
    }
    return {
        'schema': SCHEMA, 'status': 'SYNTHETIC_OUTCOME_BASELINES_ONLY',
        'source_kind': 'SYNTHETIC_TEST_ONLY',
        'train_rows_sha256': prior['train_rows_sha256'],
        'holdout_rows_sha256': prior['holdout_rows_sha256'],
        'adapter_rows_sha256': prior['adapter_rows_sha256'],
        'baseline_train_permutation_sha256': digest,
        'ridge_lambda': RIDGE_LAMBDA, 'seed': seed,
        'steps': steps, 'ensemble': ensemble,
        'n_train': len(x), 'n_holdout': len(hx),
        'baseline_metrics': results,
        'world_jepa_observed_latent_diagnostic': prior['observed_action'],
        'world_jepa_shuffled_latent_diagnostic': prior['shuffled_action'],
        'outcome_utility_proven': False,
        'causality_proven': False, 'source_disjointness_verified': False,
        'native_executed': False, 'phone_measured': False,
        'age_authority': 0, 'learning_gate_pass': False,
        'jepa_weight': 0, 'whole_system_complete': False,
    }
