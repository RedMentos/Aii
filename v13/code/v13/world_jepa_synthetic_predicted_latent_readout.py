"""Run55: grounded synthetic outcome readout from World-JEPA predicted latents.

No real Store, Runtime, external tools, persistent weights or decision authority.
A supervised ridge readout on synthetic outcomes is not JEPA causal utility.
"""
from __future__ import annotations

import copy
import hashlib

import numpy as np

from v13 import world_jepa_action_outcome_shadow_fit as shadow
from v13 import world_jepa_synthetic_outcome_baselines as linear

SCHEMA = 'v13.world_jepa.synthetic_predicted_latent_outcome_readout.v1'


def run(bundle, *, approved_shadow_fit=False, source_kind=None,
        seed=11, steps=20, ensemble=2):
    if approved_shadow_fit is not True or source_kind != 'SYNTHETIC_TEST_ONLY':
        raise PermissionError('RUN55_EXPLICIT_SYNTHETIC_SHADOW_APPROVAL_REQUIRED')
    if type(bundle) is not dict or type(bundle.get('manifest')) is not dict:
        raise ValueError('RUN55_ADAPTER_BUNDLE_REQUIRED')
    # Refuse unbounded arrays before copying; Run51/54 then check exact
    # preregistered fixture SHA256, numeric embedding and every source gate.
    m = bundle['manifest']
    for side, count_key in (('train', 'n_train'), ('holdout', 'n_holdout')):
        count = m.get(count_key)
        triple = bundle.get(side)
        if (type(count) is not int or not 8 <= count <= 256
                or type(triple) not in (tuple, list) or len(triple) != 3):
            raise ValueError('RUN55_UNBOUNDED_ADAPTER_INPUT')
        for value, cols in zip(triple, (7, 4, 7)):
            if (type(value) is not np.ndarray
                    or value.shape != (count, cols)
                    or value.dtype != np.dtype('float64')):
                raise ValueError('RUN55_UNBOUNDED_ADAPTER_INPUT')
    safe = {'manifest': copy.deepcopy(m),
            'train': tuple(v.copy() for v in bundle['train']),
            'holdout': tuple(v.copy() for v in bundle['holdout'])}
    baselines = linear.run(
        safe, approved_shadow_fit=True, source_kind=source_kind,
        seed=seed, steps=steps, ensemble=ensemble)
    fitted = shadow.run(
        safe, approved_shadow_fit=True, source_kind=source_kind,
        seed=seed, steps=steps, ensemble=ensemble)
    original = fitted['report']
    if (original['observed_action'] !=
            baselines['world_jepa_observed_latent_diagnostic']
            or original['shuffled_action'] !=
            baselines['world_jepa_shuffled_latent_diagnostic']):
        raise ValueError('RUN55_NONREPRODUCIBLE_PARENT_FIT')
    x, a, x2 = safe['train']
    hx, ha, hx2 = safe['holdout']
    observed_y, heldout_y = x2[:, 4:], hx2[:, 4:]
    # The negative-control decoder must see the same shuffled train actions
    # used to fit that WorldJEPA model; otherwise supervised ridge could
    # recover true action effects through random, untrained action features.
    perm = np.random.default_rng(seed).permutation(len(a))
    shuffled_a = a[perm].copy()
    if np.array_equal(shuffled_a, a):
        perm = np.roll(np.arange(len(a)), 1)
        shuffled_a = a[perm].copy()
    if np.array_equal(shuffled_a, a):
        raise ValueError('RUN55_UNCHANGED_ACTION_CONTROL')
    permutation_hash = hashlib.sha256(
        np.ascontiguousarray(perm.astype('<i8')).tobytes()).hexdigest()
    if permutation_hash != original['action_permutation_sha256']:
        raise ValueError('RUN55_ACTION_PERMUTATION_MISMATCH')
    readouts = {}
    for name, model in (('observed_action', fitted['observed_model']),
                        ('shuffled_train_action', fitted['shuffled_model'])):
        train_actions = shuffled_a if name == 'shuffled_train_action' else a
        train_latent = np.asarray(
            model.predict(x, train_actions)[0], dtype=np.float64)
        heldout_latent = np.asarray(model.predict(hx, ha)[0], dtype=np.float64)
        if (train_latent.ndim != 2 or heldout_latent.ndim != 2
                or train_latent.shape[0] != len(x)
                or heldout_latent.shape != (len(hx), train_latent.shape[1])
                or not np.isfinite(train_latent).all()
                or not np.isfinite(heldout_latent).all()):
            raise ValueError('RUN55_INVALID_PREDICTED_LATENTS')
        readouts[name] = linear._ridge_metrics(
            train_latent, heldout_latent, observed_y, heldout_y)
    return {
        'schema': SCHEMA,
        'status': 'SYNTHETIC_PREDICTED_LATENT_READOUT_ONLY',
        'source_kind': 'SYNTHETIC_TEST_ONLY',
        'adapter_rows_sha256': original['adapter_rows_sha256'],
        'train_rows_sha256': original['train_rows_sha256'],
        'holdout_rows_sha256': original['holdout_rows_sha256'],
        'seed': seed, 'steps': steps, 'ensemble': ensemble,
        'n_train': len(x), 'n_holdout': len(hx),
        'ridge_lambda': linear.RIDGE_LAMBDA,
        'control_train_permutation_sha256': permutation_hash,
        'predicted_latent_outcome_metrics': readouts,
        'direct_linear_outcome_metrics': baselines['baseline_metrics'],
        'world_jepa_latent_diagnostics': {
            'observed_action': original['observed_action'],
            'shuffled_action': original['shuffled_action']},
        'readout_supervised_on_synthetic_outcomes': True,
        'outcome_utility_proven': False, 'causality_proven': False,
        'source_disjointness_verified': False, 'native_executed': False,
        'phone_measured': False, 'age_authority': 0,
        'learning_gate_pass': False, 'jepa_weight': 0,
        'whole_system_complete': False,
    }
