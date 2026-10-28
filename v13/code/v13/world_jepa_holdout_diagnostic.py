"""Bounded, read-only World-JEPA action-conditioned holdout diagnostic.

Software SHADOW only. Different externally asserted source hashes are NOT
proof of disjoint training/holdout rows. Positive metrics cannot promote any
V13 age, learning, native, or utility gate.
"""
from __future__ import annotations

import hashlib
import json
import re

import numpy as np

from v13 import world_jepa as wj

SCHEMA = 'v13.world_jepa.action_holdout_diagnostic.v1'
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
MIN_ROWS = 8
MAX_ROWS = 256
MAX_FEATURES = 512


def _pin(value):
    if type(value) is not str or not HEX64.fullmatch(value):
        raise ValueError('RUN48_SOURCE_SHA256_REQUIRED')
    return value


def _digest_arrays(named):
    """Stable content digest; never put raw observations or weights in reports."""
    h = hashlib.sha256()
    for name, value in named:
        arr = np.asarray(value)
        if arr.dtype.kind not in 'fiu' or not np.isfinite(arr).all():
            raise ValueError('RUN48_NONFINITE_OR_UNSAFE_STATE')
        kind = 'f8' if arr.dtype.kind == 'f' else 'i8'
        raw = np.ascontiguousarray(arr.astype('<' + kind, copy=False))
        h.update(name.encode('ascii') + b'\0')
        h.update(json.dumps(list(raw.shape), separators=(',', ':')).encode('ascii') + b'\0')
        h.update(kind.encode('ascii') + b'\0')
        h.update(raw.tobytes(order='C'))
    return h.hexdigest()


def _state_digest(model):
    arrays = [('mu', model.mu), ('sd', model.sd), ('zsd', model.zsd),
              ('ztrain', model._ztrain), ('nn_med', [model._nn_med]),
              ('action_counts', model._action_counts)]
    for name in ('enc', 'tgt'):
        for key in ('W1', 'b1', 'W2', 'b2'):
            arrays.append((name + '_' + key, getattr(model, name)[key]))
    for i, pred in enumerate(model.preds):
        for key in ('P1', 'c1', 'P2', 'c2'):
            arrays.append(('pred' + str(i) + '_' + key, pred[key]))
    digest = _digest_arrays(arrays)
    h = hashlib.sha256()
    h.update(json.dumps({'revision': wj.REVISION, 'seed': model.seed,
                         'ensemble': model.ensemble, 'fit_steps': model._fit_steps,
                         'arrays_sha256': digest}, sort_keys=True,
                        separators=(',', ':')).encode('ascii'))
    return h.hexdigest()


@wj._read_locked
def evaluate(model, X, A, X2, *, train_source_sha256, holdout_source_sha256):
    """Measure observed latent transition/action sensitivity without authority.

    Source pins identify externally supplied datasets, but this function has
    no independently verified train-row ledger. No disjointness or learning
    proof is inferred even if the two source hashes differ.
    """
    train_source_sha256 = _pin(train_source_sha256)
    holdout_source_sha256 = _pin(holdout_source_sha256)
    if type(model) is not wj.WorldJEPA:
        raise ValueError('RUN48_WORLDJEPA_MODEL_REQUIRED')
    steps = getattr(model, '_fit_steps', None)
    base = {'schema': SCHEMA, 'train_source_sha256': train_source_sha256,
            'holdout_source_sha256': holdout_source_sha256,
            'source_disjointness_verified': False,
            'native_executed': False, 'phone_measured': False,
            'age_authority': 0, 'learning_gate_pass': False,
            'utility_proven': False, 'jepa_weight': 0,
            'whole_system_complete': False}
    if type(steps) is not int or steps <= 0:
        return dict(base, status='NO_TRAINING_EVIDENCE', metrics=None,
                    fit_steps=0, model_state_sha256=None,
                    holdout_rows_sha256=None)
    try:
        x = np.asarray(X, dtype=np.float64)
        a = np.asarray(A, dtype=np.float64)
        x2 = np.asarray(X2, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('RUN48_INVALID_HOLDOUT_ARRAYS') from exc
    if (x.ndim != 2 or a.ndim != 2 or x2.ndim != 2
            or not MIN_ROWS <= len(x) <= MAX_ROWS
            or not 1 <= x.shape[1] <= MAX_FEATURES
            or x2.shape != x.shape
            or a.shape[0] != len(x)
            or not 2 <= a.shape[1] <= 64
            or not np.isfinite(x).all() or not np.isfinite(a).all()
            or not np.isfinite(x2).all()
            or not np.all((a == 0) | (a == 1))
            or not np.all(a.sum(axis=1) == 1)):
        raise ValueError('RUN48_INVALID_HOLDOUT_TRANSITIONS')
    if (not hasattr(model, '_action_counts')
            or len(model._action_counts) != a.shape[1]
            or x.shape[1] != len(model.mu)):
        raise ValueError('RUN48_MODEL_HOLDOUT_DIMENSION_MISMATCH')
    actions = np.argmax(a, axis=1)
    if len(np.unique(actions)) < 2:
        raise ValueError('RUN48_TWO_ACTION_HOLDOUT_REQUIRED')
    counts = np.asarray(model._action_counts)
    if (counts.ndim != 1 or counts.dtype.kind not in 'iu'
            or np.any(counts < 0)):
        raise ValueError('RUN48_INVALID_TRAIN_SUPPORT')
    supported = np.flatnonzero(counts > 0)
    if len(supported) < 2 or not np.all(counts[actions] > 0):
        return dict(base, status='INSUFFICIENT_TRAIN_ACTION_SUPPORT',
                    metrics=None, fit_steps=steps,
                    model_state_sha256=_state_digest(model),
                    holdout_rows_sha256=_digest_arrays([('X', x), ('A', a), ('X2', x2)]))
    # Every alternative action is also in the training support, unlike a
    # shuffled control that might accidentally keep the original action.
    next_action = {int(k): int(supported[(i + 1) % len(supported)])
                   for i, k in enumerate(supported)}
    wrong = np.zeros_like(a)
    wrong[np.arange(len(a)), [next_action[int(k)] for k in actions]] = 1.
    zt = np.asarray(model.latent(x2, target=True), dtype=np.float64)
    z = np.asarray(model.latent(x, target=False), dtype=np.float64)
    predicted = np.asarray(model.predict(x, a)[0], dtype=np.float64)
    wrong_predicted = np.asarray(model.predict(x, wrong)[0], dtype=np.float64)
    scale = np.asarray(model.zsd, dtype=np.float64)
    if (scale.shape != (wj.Z,) or not np.isfinite(scale).all()
            or np.any(scale <= 0)
            or any(v.shape != (len(x), wj.Z) or not np.isfinite(v).all()
                   for v in (zt, z, predicted, wrong_predicted))):
        raise ValueError('RUN48_INVALID_LATENT_PREDICTION')
    def mse(value):
        delta = (value - zt) / scale
        result = float(np.mean(delta * delta))
        if not np.isfinite(result):
            raise ValueError('RUN48_NONFINITE_HOLDOUT_METRIC')
        return result
    correct_mse = mse(predicted)
    wrong_mse = mse(wrong_predicted)
    persistence_mse = mse(z)
    return dict(base, status='SHADOW_OBSERVATION_ONLY', fit_steps=steps,
                model_state_sha256=_state_digest(model),
                holdout_rows_sha256=_digest_arrays([('X', x), ('A', a), ('X2', x2)]),
                n_rows=len(x), n_actions_observed=len(np.unique(actions)),
                metrics={'correct_action_mse': correct_mse,
                         'different_supported_action_mse': wrong_mse,
                         'persistence_mse': persistence_mse,
                         'action_sensitivity_delta': wrong_mse - correct_mse,
                         'persistence_gain_delta': persistence_mse - correct_mse})
