"""Run59: synthetic-only heldout action swap after train-only latent ridge fit.

The swapped action is an input perturbation, NOT an observed counterfactual
outcome. No real Store, Runtime, weights publication or decision authority.
"""
from __future__ import annotations

import copy
import hashlib

import numpy as np

from v13 import world_jepa_action_outcome_shadow_fit as shadow
from v13 import world_jepa_synthetic_outcome_baselines as linear
from v13 import world_jepa_synthetic_predicted_latent_readout as original

SCHEMA = 'v13.world_jepa.synthetic_heldout_action_swap.v1'


def _fit_readout(train_z, train_y):
    features = np.column_stack((np.ones(len(train_z)), train_z))
    penalty = np.eye(features.shape[1], dtype=np.float64) * linear.RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    weights = np.linalg.solve(
        features.T @ features + penalty, features.T @ train_y)
    if weights.shape != (train_z.shape[1] + 1, len(linear.TARGETS)):
        raise ValueError('RUN59_READOUT_SHAPE')
    if not np.isfinite(weights).all():
        raise ValueError('RUN59_NONFINITE_READOUT')
    return weights


def _score(holdout_z, holdout_y, weights):
    features = np.column_stack((np.ones(len(holdout_z)), holdout_z))
    residual = features @ weights - holdout_y
    per_target = np.mean(residual * residual, axis=0)
    if (per_target.shape != (len(linear.TARGETS),)
            or not np.isfinite(per_target).all()):
        raise ValueError('RUN59_NONFINITE_HOLDOUT_METRICS')
    return {
        'overall_mse': float(per_target.mean()),
        'per_target_mse': {
            k: float(v) for k, v in zip(linear.TARGETS, per_target)}}


def _checked_latent(model, x, a, *, rows, cols=None):
    z = np.asarray(model.predict(x, a)[0], dtype=np.float64)
    if (z.ndim != 2 or z.shape[0] != rows
            or (cols is not None and z.shape[1] != cols)
            or not 1 <= z.shape[1] <= 512 or not np.isfinite(z).all()):
        raise ValueError('RUN59_INVALID_PREDICTED_LATENT')
    return z


def run(bundle, *, approved_shadow_fit=False, source_kind=None,
        seed=11, steps=20, ensemble=2):
    if approved_shadow_fit is not True or source_kind != 'SYNTHETIC_TEST_ONLY':
        raise PermissionError('RUN59_EXPLICIT_SYNTHETIC_SHADOW_APPROVAL_REQUIRED')
    if type(bundle) is not dict or type(bundle.get('manifest')) is not dict:
        raise ValueError('RUN59_ADAPTER_BUNDLE_REQUIRED')
    manifest = bundle['manifest']
    for side, count_key in (('train', 'n_train'), ('holdout', 'n_holdout')):
        count = manifest.get(count_key)
        triple = bundle.get(side)
        if (type(count) is not int or not 8 <= count <= 256
                or type(triple) not in (tuple, list) or len(triple) != 3):
            raise ValueError('RUN59_UNBOUNDED_ADAPTER_INPUT')
        for value, cols in zip(triple, (7, 4, 7)):
            if (type(value) is not np.ndarray
                    or value.shape != (count, cols)
                    or value.dtype != np.dtype('float64')):
                raise ValueError('RUN59_UNBOUNDED_ADAPTER_INPUT')
    safe = {'manifest': copy.deepcopy(manifest),
            'train': tuple(v.copy() for v in bundle['train']),
            'holdout': tuple(v.copy() for v in bundle['holdout'])}
    # Run55 and Run51 both independently enforce exact registered source
    # digests and configuration before any fit. No caller data escapes.
    previous = original.run(
        safe, approved_shadow_fit=True, source_kind=source_kind,
        seed=seed, steps=steps, ensemble=ensemble)
    fitted = shadow.run(
        safe, approved_shadow_fit=True, source_kind=source_kind,
        seed=seed, steps=steps, ensemble=ensemble)
    report = fitted['report']
    if (report['adapter_rows_sha256'] != previous['adapter_rows_sha256']
            or report['train_rows_sha256'] != previous['train_rows_sha256']
            or report['holdout_rows_sha256'] != previous['holdout_rows_sha256']
            or report['action_permutation_sha256'] !=
            previous['control_train_permutation_sha256']):
        raise ValueError('RUN59_PARENT_SOURCE_OR_CONTROL_MISMATCH')
    x, a, x2 = safe['train']
    hx, ha, hx2 = safe['holdout']
    swapped = np.roll(ha, shift=1, axis=1)
    if (not np.all((swapped == 0) | (swapped == 1))
            or not np.all(swapped.sum(axis=1) == 1)
            or not np.all(np.any(swapped != ha, axis=1))):
        raise ValueError('RUN59_ACTION_SWAP_NOT_DISTINCT')
    perm = np.random.default_rng(seed).permutation(len(a))
    shuffled_a = a[perm].copy()
    if np.array_equal(shuffled_a, a):
        perm = np.roll(np.arange(len(a)), 1)
        shuffled_a = a[perm].copy()
    if np.array_equal(shuffled_a, a):
        raise ValueError('RUN59_UNCHANGED_TRAIN_ACTION_CONTROL')
    digest = hashlib.sha256(
        np.ascontiguousarray(perm.astype('<i8')).tobytes()).hexdigest()
    if digest != report['action_permutation_sha256']:
        raise ValueError('RUN59_PERMUTATION_MISMATCH')
    scores = {}
    for key, model, train_a in (
            ('observed_action', fitted['observed_model'], a),
            ('shuffled_train_action', fitted['shuffled_model'], shuffled_a)):
        counts = np.asarray(model._action_counts)
        if (counts.shape != (ha.shape[1],)
                or not np.all(counts[np.argmax(swapped, axis=1)] > 0)):
            raise ValueError('RUN59_UNSUPPORTED_SWAP_ACTION')
        train_z = _checked_latent(model, x, train_a, rows=len(x))
        correct_z = _checked_latent(
            model, hx, ha, rows=len(hx), cols=train_z.shape[1])
        wrong_z = _checked_latent(
            model, hx, swapped, rows=len(hx), cols=train_z.shape[1])
        weights = _fit_readout(train_z, x2[:, 4:])
        correct = _score(correct_z, hx2[:, 4:], weights)
        wrong = _score(wrong_z, hx2[:, 4:], weights)
        baseline = previous['predicted_latent_outcome_metrics'][key]
        for field in ('overall_mse',):
            if not np.isclose(correct[field], baseline[field], atol=1e-12, rtol=1e-10):
                raise ValueError('RUN59_RUN55_READOUT_MISMATCH')
        for name in linear.TARGETS:
            if not np.isclose(correct['per_target_mse'][name],
                              baseline['per_target_mse'][name],
                              atol=1e-12, rtol=1e-10):
                raise ValueError('RUN59_RUN55_READOUT_MISMATCH')
        scores[key] = {
            'correct_action': correct,
            'swapped_holdout_action': wrong,
            'wrong_minus_correct_overall_mse':
                float(wrong['overall_mse'] - correct['overall_mse']),
            'readout_weights_published': False,
        }
    return {
        'schema': SCHEMA,
        'status': 'SYNTHETIC_HELDOUT_ACTION_SWAP_DIAGNOSTIC_ONLY',
        'source_kind': source_kind,
        'adapter_rows_sha256': report['adapter_rows_sha256'],
        'train_rows_sha256': report['train_rows_sha256'],
        'holdout_rows_sha256': report['holdout_rows_sha256'],
        'train_permutation_sha256': digest,
        'seed': seed, 'steps': steps, 'ensemble': ensemble,
        'n_train': len(x), 'n_holdout': len(hx),
        'swapped_action_rows': len(hx),
        'ridge_lambda': linear.RIDGE_LAMBDA,
        'readout_metrics': scores,
        'direct_linear_outcome_metrics': previous['direct_linear_outcome_metrics'],
        'readout_supervised_on_synthetic_outcomes': True,
        'counterfactual_outcome_observed': False,
        'causality_proven': False, 'outcome_utility_proven': False,
        'source_disjointness_verified': False, 'native_executed': False,
        'phone_measured': False, 'age_authority': 0,
        'learning_gate_pass': False, 'jepa_weight': 0,
        'whole_system_complete': False,
    }
