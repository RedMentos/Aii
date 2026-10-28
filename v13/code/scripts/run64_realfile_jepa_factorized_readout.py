"""Run64: exploratory real-file factorized-action WorldJEPA with supervised readout.

Frozen NumPy WorldJEPA is fitted only on real isolated temporary-file
transitions. This does not demonstrate JEPA-only, causal, native, Redmi,
online-learning, user-facing or whole-system utility.
"""
from __future__ import annotations

import hashlib
import random

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run63_z12b_factorized_real_file_baselines as factor
from scripts import z12b_world_jepa as original
from v13.world_jepa import WorldJEPA

SCHEMA = 'v13.z12b.real_file_factorized_jepa_readout.v1'
SEEDS = (251, 257, 263)
N_TRAIN = 240
N_TEST = 60
STEPS = 200
ENSEMBLE = 1
RIDGE = .01
ARM_NAMES = ('observed_action', 'zero_action', 'shuffled_train_action')


def _factor_actions(rows):
    out = np.stack([
        factor._factorized_global_features(x, action)[1+parent.FEATURES:]
        for x, action, _, _ in rows])
    if (out.shape != (len(rows), len(original.OPS)+original.SLOTS)
            or not np.isfinite(out).all()
            or any(out[i].sum() != (0 if row[1] == original.NOOP else 2)
                   for i, row in enumerate(rows))):
        raise ValueError('RUN64_INVALID_FACTORIZED_ACTION')
    return out


def _perm_sha256(perm):
    return hashlib.sha256(
        np.ascontiguousarray(perm, dtype='<i8').tobytes()).hexdigest()


def _fit_readout(x, train_actions, x2, x_holdout, heldout_actions, *, seed):
    """Fit JEPA and supervised decoder on train only; heldout x2 not accepted."""
    if (x.ndim != 2 or x2.shape != x.shape or len(x) < 2
            or train_actions.shape != (len(x), len(original.OPS)+original.SLOTS)
            or x_holdout.ndim != 2 or x_holdout.shape[1] != x.shape[1]
            or heldout_actions.shape != (len(x_holdout), train_actions.shape[1])
            or not all(np.isfinite(v).all()
                       for v in (x, x2, train_actions, x_holdout, heldout_actions))):
        raise ValueError('RUN64_INVALID_TRAIN_HOLDOUT_SHAPES')
    model = WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(
        x, train_actions, x2, steps=STEPS, log_every=STEPS)
    z_train, _ = model.predict(x, train_actions)
    z_test, _ = model.predict(x_holdout, heldout_actions)
    if (z_train.shape != (len(x), 16)
            or z_test.shape != (len(x_holdout), 16)
            or not np.isfinite(z_train).all()
            or not np.isfinite(z_test).all()):
        raise ValueError('RUN64_INVALID_PREDICTED_LATENTS')
    readout_x = np.c_[np.ones(len(x)), z_train]
    readout_w = parent._ridge(readout_x, x2)
    predicted = np.c_[np.ones(len(x_holdout)), z_test] @ readout_w
    if predicted.shape != x_holdout.shape or not np.isfinite(predicted).all():
        raise ValueError('RUN64_NONFINITE_GROUNDED_OUTCOME')
    return predicted


def _metrics(predicted, holdout):
    x2 = np.stack([r[2] for r in holdout])
    if predicted.shape != x2.shape or not np.isfinite(predicted).all():
        raise ValueError('RUN64_INVALID_PREDICTIONS')
    delta = predicted - x2
    slots = [original.ACTIONS[r[1]][1] for r in holdout]
    if any(s is None for s in slots):
        raise ValueError('RUN64_HOLDOUT_NOOP')
    target = [float(np.mean(delta[i, s*parent.SLOT_FEATURES:
                                     (s+1)*parent.SLOT_FEATURES]**2))
              for i, s in enumerate(slots)]
    return {'overall_mse': float(np.mean(delta**2)),
            'target_slot_mse': float(np.mean(target))}


def _seed(seed):
    held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
    train = parent._rows(seed, held, N_TRAIN, test=False)
    test = parent._rows(seed, held, N_TEST, test=True)
    if (len(train) != N_TRAIN or len(test) != N_TEST
            or any(a in held for _, a, _, _ in train)
            or any(a not in held for _, a, _, _ in test)
            or len(set(a for _, a, _, _ in test)) < 2):
        raise ValueError('RUN64_SPLIT_CONTAMINATION')
    x = np.stack([r[0] for r in train])
    x2 = np.stack([r[2] for r in train])
    xt = np.stack([r[0] for r in test])
    a = _factor_actions(train)
    at = _factor_actions(test)
    perm = np.random.default_rng(seed+500).permutation(len(train))
    arms = {
        'observed_action': (a, at),
        'zero_action': (np.zeros_like(a), np.zeros_like(at)),
        'shuffled_train_action': (a[perm], at),
    }
    scores = {}
    for name in ARM_NAMES:
        aa, ah = arms[name]
        pred = _fit_readout(x, aa, x2, xt, ah, seed=seed)
        scores[name] = _metrics(pred, test)
    baselines = factor._evaluate(train, test)
    return {
        'seed': seed, 'heldout_action_indices': list(held),
        'n_train': len(train), 'n_holdout': len(test),
        'train_rows_sha256': parent._digest(train),
        'test_rows_sha256': parent._digest(test),
        'shuffled_train_permutation_sha256': _perm_sha256(perm),
        'train_action_count': len(set(r[1] for r in train)),
        'test_action_count': len(set(r[1] for r in test)),
        'train_changed_count': sum(not np.array_equal(r[0], r[2])
                                   for r in train),
        'test_changed_count': sum(not np.array_equal(r[0], r[2])
                                  for r in test),
        'test_action_succeeded_count': sum(bool(r[3]) for r in test),
        'jepa_readout_metrics': scores,
        'supervised_baseline_metrics': baselines,
    }


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_test=N_TEST, steps=STEPS):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_test) is not int or n_test != N_TEST
            or type(steps) is not int or steps != STEPS):
        raise PermissionError('RUN64_ONLY_PREREGISTERED_REAL_FILE_COHORT')
    reports = [_seed(seed) for seed in seeds]
    def aggregate(field, names):
        return {name: {key: float(np.mean([r[field][name][key] for r in reports]))
                       for key in ('overall_mse', 'target_slot_mse')}
                for name in names}
    return {
        'schema': SCHEMA, 'status': 'REAL_FILE_JEPA_SUPERVISED_READOUT_SHADOW_ONLY',
        'source_kind': 'ISOLATED_LINUX_TEMP_FILE_ACTIONS',
        'seeds': list(seeds), 'n_train_per_seed': n_train,
        'n_holdout_per_seed': n_test, 'jepa_steps': STEPS,
        'jepa_ensemble': ENSEMBLE, 'ridge_lambda': RIDGE,
        'action_encoding': 'FACTORIZED_5_OP_PLUS_6_SLOT_TWO_HOT',
        'jepa_confidence_supported_for_factorized_actions': False,
        'reports': reports,
        'aggregate_jepa_readout_metrics': aggregate('jepa_readout_metrics', ARM_NAMES),
        'aggregate_supervised_baseline_metrics':
            aggregate('supervised_baseline_metrics', factor.MODEL_NAMES),
        'file_actions_executed': True, 'native_model_executed': False,
        'model_weights_published': False,
        'jepa_training_executed': True,
        'jepa_only_utility_proven': False,
        'counterfactual_causality_proven': False,
        'source_disjointness_verified': False, 'phone_measured': False,
        'age_authority': 0, 'learning_gate_pass': False,
        'jepa_weight': 0, 'whole_system_complete': False,
    }
