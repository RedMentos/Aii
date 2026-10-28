"""Run63: same-cohort real file-action JEPA-latent readout vs slot-local ridge.

Fresh preregistered real isolated file operations. The JEPA readout is
SUPERVISED on train outcomes; it is not JEPA-only utility, a native run,
causal planning, or a production/age authorization.
"""
from __future__ import annotations

import hashlib
import random

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as base
from scripts import z12b_world_jepa as fileworld
from v13.world_jepa import WorldJEPA

SCHEMA = 'v13.z12b.samecohort_worldjepa_readout.v1'
SEEDS = (233, 239, 241)
N_TRAIN = 240
N_HOLDOUT = 60
STEPS = 40
ENSEMBLE = 2
ARMS = ('observed_action', 'zero_action', 'shuffled_train_action')


def _predicted(model, x, a, rows):
    z = np.asarray(model.predict(x, a)[0], dtype=np.float64)
    if (z.ndim != 2 or z.shape[0] != rows or not 1 <= z.shape[1] <= 512
            or not np.isfinite(z).all()):
        raise ValueError('RUN63_NONFINITE_OR_INVALID_JEPA_LATENT')
    return z


def _mse(predicted, truth, heldout_actions):
    delta = np.asarray(predicted - truth, dtype=np.float64)
    if delta.shape != truth.shape or not np.isfinite(delta).all():
        raise ValueError('RUN63_INVALID_OUTCOME_PREDICTION')
    target = []
    for d, action in zip(delta, heldout_actions):
        slot = fileworld.ACTIONS[int(action)][1]
        if slot is None:
            raise ValueError('RUN63_HELDOUT_NOOP')
        part = d[slot*base.SLOT_FEATURES:(slot+1)*base.SLOT_FEATURES]
        target.append(float(np.mean(part*part)))
    return {'overall_mse': float(np.mean(delta*delta)),
            'target_slot_mse': float(np.mean(target))}


def _evaluate(seed, train, holdout):
    x = np.stack([row[0] for row in train])
    a = np.stack([fileworld.onehot(row[1]) for row in train])
    x2 = np.stack([row[2] for row in train])
    hx = np.stack([row[0] for row in holdout])
    ha = np.stack([fileworld.onehot(row[1]) for row in holdout])
    hx2 = np.stack([row[2] for row in holdout])
    hold_actions = np.array([row[1] for row in holdout], dtype=np.int64)
    perm = np.random.default_rng(seed).permutation(len(a))
    shuffled = a[perm].copy()
    if np.array_equal(shuffled, a):
        perm = np.roll(np.arange(len(a)), 1)
        shuffled = a[perm].copy()
    if np.array_equal(shuffled, a):
        raise ValueError('RUN63_UNCHANGED_SHUFFLED_ACTION_CONTROL')
    perm_digest = hashlib.sha256(
        np.ascontiguousarray(perm.astype('<i8')).tobytes()).hexdigest()
    models = {}
    for name, train_a, test_a in (
            ('observed_action', a, ha),
            ('zero_action', np.zeros_like(a), np.zeros_like(ha)),
            ('shuffled_train_action', shuffled, ha)):
        model = WorldJEPA(seed=seed, ensemble=ENSEMBLE)
        model.fit(x, train_a, x2, steps=STEPS)
        train_z = _predicted(model, x, train_a, len(x))
        hold_z = _predicted(model, hx, test_a, len(hx))
        if hold_z.shape[1] != train_z.shape[1]:
            raise ValueError('RUN63_JEPA_LATENT_WIDTH_CHANGED')
        # Train-only supervised decoder, same fixed ridge lambda as Run60.
        features = np.column_stack((np.ones(len(train_z)), train_z))
        weights = base._ridge(features, x2)
        predictions = np.column_stack((np.ones(len(hold_z)), hold_z)) @ weights
        models[name] = _mse(predictions, hx2, hold_actions)
    return models, perm_digest


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_holdout=N_HOLDOUT,
        steps=STEPS, ensemble=ENSEMBLE):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_holdout) is not int or n_holdout != N_HOLDOUT
            or type(steps) is not int or steps != STEPS
            or type(ensemble) is not int or ensemble != ENSEMBLE):
        raise PermissionError('RUN63_ONLY_PREREGISTERED_REAL_FILE_FIXTURE')
    reports = []
    for seed in seeds:
        held = tuple(sorted(random.Random(seed).sample(base.NON_NOOP, 4)))
        train = base._rows(seed, held, n_train, test=False)
        test = base._rows(seed, held, n_holdout, test=True)
        if (any(a in held for _, a, _, _ in train)
                or any(a not in held for _, a, _, _ in test)
                or len(train) != n_train or len(test) != n_holdout):
            raise ValueError('RUN63_HELDOUT_ACTION_LEAKAGE')
        baselines = base._evaluate(train, test)
        jepa, permutation = _evaluate(seed, train, test)
        reports.append({
            'seed': seed, 'heldout_action_indices': list(held),
            'n_train': len(train), 'n_holdout': len(test),
            'train_rows_sha256': base._digest(train),
            'holdout_rows_sha256': base._digest(test),
            'train_action_permutation_sha256': permutation,
            'train_changed_count': sum(not np.array_equal(x, x2)
                                       for x, _, x2, _ in train),
            'holdout_changed_count': sum(not np.array_equal(x, x2)
                                         for x, _, x2, _ in test),
            'holdout_action_succeeded_count': sum(ok for _, _, _, ok in test),
            'jepa_readout_metrics': jepa,
            'same_cohort_baseline_metrics': baselines,
        })
    aggregate = {}
    for kind, names in (
            ('jepa_readout_metrics', ARMS),
            ('same_cohort_baseline_metrics',
             ('persistence', 'global_ridge', 'slot_local_ridge'))):
        aggregate[kind] = {
            name: {
                metric: float(np.mean([
                    r[kind][name][metric] for r in reports]))
                for metric in ('overall_mse', 'target_slot_mse')}
            for name in names}
    return {
        'schema': SCHEMA,
        'status': 'REAL_FILE_WORLDJEPA_SUPERVISED_READOUT_COMPARISON_ONLY',
        'source_kind': 'ISOLATED_LINUX_TEMP_FILE_ACTIONS',
        'seeds': list(seeds), 'n_train_per_seed': n_train,
        'n_holdout_per_seed': n_holdout,
        'steps': steps, 'ensemble': ensemble,
        'ridge_lambda': base.RIDGE,
        'reports': reports, 'aggregate_metrics': aggregate,
        'jepa_training_executed': True,
        'readout_supervised_on_real_train_outcomes': True,
        'counterfactual_outcome_observed': False,
        'causality_proven': False, 'jepa_only_utility_proven': False,
        'original_z12b_gate_pass': False,
        'model_weights_published': False,
        'source_disjointness_verified': False,
        'native_model_executed': False, 'phone_measured': False,
        'age_authority': 0, 'learning_gate_pass': False,
        'jepa_weight': 0, 'whole_system_complete': False,
    }
