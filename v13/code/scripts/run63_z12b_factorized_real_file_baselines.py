"""Run63: fresh, preregistered factorized-action real file baselines.

Supervised offline Linux filesystem actions only. No JEPA, Runtime, Store,
native LLM, user file, permission, model publication or authority changes.
"""
from __future__ import annotations

import hashlib
import random

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import z12b_world_jepa as original

SCHEMA = 'v13.z12b.factorized_real_file_baseline.v1'
SEEDS = (233, 239, 241)
N_TRAIN = 240
N_TEST = 60
RIDGE = parent.RIDGE
MODEL_NAMES = ('persistence', 'global_ridge', 'slot_local_ridge',
               'factorized_global_delta_ridge', 'slot_aware_local_ridge')


def _factorized_global_features(x, action):
    """Separate operation and slot; no exact op×slot one-hot feature."""
    op, slot = original.ACTIONS[action]
    op_hot = np.zeros(len(original.OPS), dtype=np.float64)
    slot_hot = np.zeros(original.SLOTS, dtype=np.float64)
    if action != original.NOOP:
        op_hot[original.OPS.index(op)] = 1.
        slot_hot[slot] = 1.
    return np.r_[1., x, op_hot, slot_hot]


def _slot_aware_features(x, action):
    op, slot = original.ACTIONS[action]
    if action == original.NOOP or slot is None:
        raise ValueError('RUN63_NOOP_NOT_A_LOCAL_ACTION')
    return np.r_[parent._local_features(x, action),
                 parent._onehot(slot, original.SLOTS)]


def _fit(train):
    if not train or any(len(row) != 4 for row in train):
        raise ValueError('RUN63_EMPTY_OR_INVALID_TRAIN')
    base_global, base_local = parent._fit(train)
    x = np.stack([r[0] for r in train])
    y = np.stack([r[2] for r in train])
    factors = np.stack([_factorized_global_features(r[0], r[1])
                        for r in train])
    factor_w = parent._ridge(factors, y - x)
    local = [r for r in train if r[1] != original.NOOP]
    local_f = np.stack([_slot_aware_features(r[0], r[1]) for r in local])
    local_y = np.stack([
        r[2][original.ACTIONS[r[1]][1]*parent.SLOT_FEATURES:
             (original.ACTIONS[r[1]][1]+1)*parent.SLOT_FEATURES]
        for r in local])
    aware_w = parent._ridge(local_f, local_y)
    return base_global, base_local, factor_w, aware_w


def _predict(x, action, weights):
    base_global, base_local, factor_w, aware_w = weights
    pred = parent._predict(x, action, base_global, base_local)
    pred['factorized_global_delta_ridge'] = (
        x + _factorized_global_features(x, action) @ factor_w)
    aware = x.copy()
    if action != original.NOOP:
        slot = original.ACTIONS[action][1]
        start = slot*parent.SLOT_FEATURES
        aware[start:start+parent.SLOT_FEATURES] = (
            _slot_aware_features(x, action) @ aware_w)
    pred['slot_aware_local_ridge'] = aware
    if set(pred) != set(MODEL_NAMES):
        raise AssertionError('RUN63_COMPARATOR_SET_DRIFT')
    return pred


def _evaluate(train, holdout):
    """No holdout targets are used in _fit; all models score same x2 rows."""
    weights = _fit(train)
    errors = {name: {'overall': [], 'target_slot': []} for name in MODEL_NAMES}
    for x, action, x2, _ in holdout:
        slot = original.ACTIONS[action][1]
        if slot is None:
            raise ValueError('RUN63_HOLDOUT_NOOP')
        start = slot*parent.SLOT_FEATURES
        for name, predicted in _predict(x, action, weights).items():
            delta = np.asarray(predicted - x2, dtype=np.float64)
            if (delta.shape != (parent.FEATURES,)
                    or not np.isfinite(delta).all()):
                raise ValueError('RUN63_NONFINITE_PREDICTION')
            errors[name]['overall'].append(float(np.mean(delta*delta)))
            errors[name]['target_slot'].append(float(
                np.mean(delta[start:start+parent.SLOT_FEATURES]**2)))
    return {
        name: {'overall_mse': float(np.mean(v['overall'])),
               'target_slot_mse': float(np.mean(v['target_slot']))}
        for name, v in errors.items()
    }


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_test=N_TEST):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_test) is not int or n_test != N_TEST):
        raise PermissionError('RUN63_ONLY_PREREGISTERED_REAL_FILE_FIXTURE')
    reports = []
    for seed in seeds:
        held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
        train = parent._rows(seed, held, n_train, test=False)
        test = parent._rows(seed, held, n_test, test=True)
        if (len(train) != n_train or len(test) != n_test
                or any(a in held for _, a, _, _ in train)
                or any(a not in held for _, a, _, _ in test)
                or len(set(a for _, a, _, _ in test)) < 2):
            raise ValueError('RUN63_SPLIT_CONTAMINATION')
        metrics = _evaluate(train, test)
        reports.append({
            'seed': seed, 'heldout_action_indices': list(held),
            'n_train': len(train), 'n_holdout': len(test),
            'train_rows_sha256': parent._digest(train),
            'test_rows_sha256': parent._digest(test),
            'train_action_count': len(set(a for _, a, _, _ in train)),
            'test_action_count': len(set(a for _, a, _, _ in test)),
            'train_changed_count': sum(not np.array_equal(x, x2)
                                       for x, _, x2, _ in train),
            'test_changed_count': sum(not np.array_equal(x, x2)
                                      for x, _, x2, _ in test),
            'test_action_succeeded_count': sum(ok for _, _, _, ok in test),
            'metrics': metrics,
        })
    aggregate = {
        name: {key: float(np.mean([r['metrics'][name][key] for r in reports]))
               for key in ('overall_mse', 'target_slot_mse')}
        for name in MODEL_NAMES}
    return {
        'schema': SCHEMA, 'status': 'REAL_FILE_FACTORIZED_BASELINES_ONLY',
        'source_kind': 'ISOLATED_LINUX_TEMP_FILE_ACTIONS',
        'seeds': list(seeds), 'n_train_per_seed': n_train,
        'n_holdout_per_seed': n_test, 'ridge_lambda': RIDGE,
        'reports': reports, 'aggregate_metrics': aggregate,
        'file_actions_executed': True, 'native_model_executed': False,
        'model_weights_published': False, 'jepa_training_executed': False,
        'counterfactual_causality_proven': False,
        'source_disjointness_verified': False, 'phone_measured': False,
        'age_authority': 0, 'learning_gate_pass': False,
        'jepa_weight': 0, 'whole_system_complete': False,
    }
