"""Run60: slot-local compositional ridge baseline on real isolated file actions.

Fresh exploratory Linux filesystem study; no native model, Runtime, Store,
external tools, online learning, authority or original Z12b gate promotion.
"""
from __future__ import annotations

import hashlib
import random
import shutil
import tempfile
from pathlib import Path

import numpy as np

from scripts import z12b_world_jepa as original

SCHEMA = 'v13.z12b.slotlocal_real_file_baseline.v1'
SEEDS = (211, 223, 227)
N_TRAIN = 240
N_TEST = 60
RIDGE = 0.01
SLOT_FEATURES = 10
FEATURES = original.SLOTS * SLOT_FEATURES
NOOP = original.NOOP
NON_NOOP = tuple(range(NOOP))


def _onehot(i, n):
    result = np.zeros(n, dtype=np.float64)
    result[i] = 1.0
    return result


def _digest(rows):
    h = hashlib.sha256()
    for x, action, x2, success in rows:
        h.update(np.ascontiguousarray(x, dtype='<f8').tobytes())
        h.update(int(action).to_bytes(4, 'little'))
        h.update(np.ascontiguousarray(x2, dtype='<f8').tobytes())
        h.update(b'1' if success else b'0')
    return h.hexdigest()


def _rows(seed, held, count, *, test):
    """Perform actual file operations in private copies of a fresh state walk."""
    state_seed = seed + (10000 if test else 1000)
    rng = random.Random(state_seed)
    choices = random.Random(state_seed + 1)
    allowed = tuple(i for i in NON_NOOP if i not in held)
    targets = tuple(sorted(held)) if test else allowed + (NOOP,)
    rows = []
    with tempfile.TemporaryDirectory(prefix='v13-run60-file-') as td:
        root = Path(td)
        live = root / 'live'
        live.mkdir()
        trial = root / 'trial'
        for _ in range(count):
            # Evolve source state without introducing held-out action combos.
            for _ in range(1 + choices.randrange(3)):
                i = choices.choice(allowed)
                op, slot = original.ACTIONS[i]
                original.do(live, op, slot, rng)
            action = choices.choice(targets)
            x = np.asarray(original.features(live), dtype=np.float64)
            shutil.copytree(live, trial)
            op, slot = original.ACTIONS[action]
            success = bool(original.do(trial, op, slot, rng))
            x2 = np.asarray(original.features(trial), dtype=np.float64)
            shutil.rmtree(trial)
            if (x.shape != (FEATURES,) or x2.shape != x.shape
                    or not np.isfinite(x).all() or not np.isfinite(x2).all()):
                raise ValueError('RUN60_INVALID_REAL_FILE_FEATURES')
            rows.append((x.copy(), action, x2.copy(), success))
    return rows


def _ridge(features, targets):
    if (features.ndim != 2 or targets.ndim != 2
            or len(features) != len(targets)
            or not np.isfinite(features).all()
            or not np.isfinite(targets).all()):
        raise ValueError('RUN60_INVALID_RIDGE_ARRAYS')
    penalty = np.eye(features.shape[1], dtype=np.float64) * RIDGE
    penalty[0, 0] = 0.
    w = np.linalg.solve(features.T @ features + penalty,
                        features.T @ targets)
    if not np.isfinite(w).all():
        raise ValueError('RUN60_NONFINITE_RIDGE')
    return w


def _global_features(x, action):
    return np.r_[1., x, _onehot(action, len(original.ACTIONS))]


def _local_features(x, action):
    op, slot = original.ACTIONS[action]
    if slot is None:
        raise ValueError('RUN60_LOCAL_NOOP_HAS_NO_SLOT')
    return np.r_[1., x[slot*SLOT_FEATURES:(slot+1)*SLOT_FEATURES],
                 _onehot(original.OPS.index(op), len(original.OPS))]


def _fit(train):
    g = np.stack([_global_features(x, a) for x, a, _, _ in train])
    gy = np.stack([x2 for _, _, x2, _ in train])
    global_w = _ridge(g, gy)
    local = [(x, a, x2) for x, a, x2, _ in train if a != NOOP]
    lf = np.stack([_local_features(x, a) for x, a, _ in local])
    ly = np.stack([
        x2[original.ACTIONS[a][1]*SLOT_FEATURES:
           (original.ACTIONS[a][1]+1)*SLOT_FEATURES]
        for x, a, x2 in local])
    local_w = _ridge(lf, ly)
    return global_w, local_w


def _predict(x, action, global_w, local_w):
    global_prediction = _global_features(x, action) @ global_w
    local_prediction = x.copy()
    if action != NOOP:
        slot = original.ACTIONS[action][1]
        local_prediction[slot*SLOT_FEATURES:(slot+1)*SLOT_FEATURES] = (
            _local_features(x, action) @ local_w)
    return {'persistence': x,
            'global_ridge': global_prediction,
            'slot_local_ridge': local_prediction}


def _evaluate(train, holdout):
    global_w, local_w = _fit(train)
    by_model = {name: {'all': [], 'target_slot': []}
                for name in ('persistence', 'global_ridge', 'slot_local_ridge')}
    for x, action, x2, _ in holdout:
        slot = original.ACTIONS[action][1]
        for name, predicted in _predict(x, action, global_w, local_w).items():
            delta = np.asarray(predicted - x2, dtype=np.float64)
            if delta.shape != (FEATURES,) or not np.isfinite(delta).all():
                raise ValueError('RUN60_NONFINITE_REAL_FILE_PREDICTION')
            by_model[name]['all'].append(float(np.mean(delta*delta)))
            part = delta[slot*SLOT_FEATURES:(slot+1)*SLOT_FEATURES]
            by_model[name]['target_slot'].append(float(np.mean(part*part)))
    return {
        name: {'overall_mse': float(np.mean(scores['all'])),
               'target_slot_mse': float(np.mean(scores['target_slot']))}
        for name, scores in by_model.items()}


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_test=N_TEST):
    # No silent posthoc search over seeds, train sizes or fixture definitions.
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_test) is not int or n_test != N_TEST):
        raise PermissionError('RUN60_ONLY_PREREGISTERED_REAL_FILE_FIXTURE')
    reports = []
    for seed in seeds:
        held = tuple(sorted(random.Random(seed).sample(NON_NOOP, 4)))
        train = _rows(seed, held, n_train, test=False)
        test = _rows(seed, held, n_test, test=True)
        if (len(train) != n_train or len(test) != n_test
                or any(a in held for _, a, _, _ in train)
                or any(a not in held for _, a, _, _ in test)
                or len(set(a for _, a, _, _ in test)) < 2):
            raise ValueError('RUN60_SPLIT_CONTAMINATION_OR_COVERAGE')
        metrics = _evaluate(train, test)
        reports.append({
            'seed': seed,
            'heldout_action_indices': list(held),
            'train_rows_sha256': _digest(train),
            'test_rows_sha256': _digest(test),
            'n_train': len(train), 'n_holdout': len(test),
            'train_action_count': len(set(a for _, a, _, _ in train)),
            'test_action_count': len(set(a for _, a, _, _ in test)),
            'train_changed_count': sum(not np.array_equal(x, x2)
                                       for x, _, x2, _ in train),
            'test_changed_count': sum(not np.array_equal(x, x2)
                                      for x, _, x2, _ in test),
            'test_action_succeeded_count': sum(ok for _, _, _, ok in test),
            'metrics': metrics,
        })
    names = tuple(reports[0]['metrics'])
    aggregate = {
        name: {key: float(np.mean([r['metrics'][name][key] for r in reports]))
               for key in ('overall_mse', 'target_slot_mse')}
        for name in names}
    return {
        'schema': SCHEMA, 'status': 'REAL_FILE_ACTION_SLOTLOCAL_BASELINE_ONLY',
        'source_kind': 'ISOLATED_LINUX_TEMP_FILE_ACTIONS',
        'seeds': list(seeds), 'n_train_per_seed': n_train,
        'n_holdout_per_seed': n_test, 'ridge_lambda': RIDGE,
        'reports': reports, 'aggregate_metrics': aggregate,
        'file_actions_executed': True, 'native_model_executed': False,
        'model_weights_published': False,
        'jepa_training_executed': False, 'counterfactual_causality_proven': False,
        'source_disjointness_verified': False, 'phone_measured': False,
        'age_authority': 0, 'learning_gate_pass': False,
        'jepa_weight': 0, 'whole_system_complete': False,
    }
