"""Source-bound World-JEPA replay preview on a detached in-memory model copy.

No live model, optimizer, checkpoint, Age state or runtime is modified. The
returned copy is an unapproved SHADOW proposal; there is no promotion API here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from . import world_jepa as wj
from . import world_jepa_replay as original
from . import world_jepa_shadow_checkpoint as checkpoint

PINS = {
    'world_jepa.py': '14ee7982ab3866a13b2cca83086123281cf112a3c133b91c06df9df3669715fd',
    'world_jepa_replay.py': '57e075c2a0345948b7b8d68422b3b67ea9d357e1b8e18724f9254225e9ed8a52',
    'world_jepa_shadow_checkpoint.py': 'cacf2532a02ba3d8e4a60e8047996675bec62a0190a9209c2366dd06b492b570',
}
# #1658/#1661 only reorder calibration validation; the actual source hashes
# are checked again before the detached preview uses either implementation.
ALTERNATE_PINS = {
    'world_jepa_shadow_checkpoint.py': frozenset({
        'f88ad5eea241aacd55e5c3d0f53eb0b132a164a2d49cc0185726f1a0a8a076ae',
    }),
}
MAX_TRANSITION_BYTES = 64 * 1024 * 1024
_REQUIRED_STATE = frozenset({'seed', 'ensemble', '_fit_steps', '_action_counts', 'mu', 'sd',
                             'history', 'enc', 'tgt', 'preds', 'zsd', '_ztrain', '_nn_med'})
_VALIDATION_TAG = '0' * 64  # Shape/finite-state validator only; not source provenance.


def _check_sources():
    directory = Path(__file__).resolve().parent
    for name, expected in PINS.items():
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if actual != expected and actual not in ALTERNATE_PINS.get(name, ()):
            raise ValueError('replay candidate source changed: ' + name)


def _row_fingerprints(triple):
    """Canonical exact numeric triples; this is not source-ID disjointness."""
    x, a, y = triple
    rows = set()
    for i in range(len(x)):
        with np.errstate(over='ignore', invalid='ignore'):
            values = np.concatenate((np.asarray(x[i], dtype='<f8'),
                                     np.asarray(a[i], dtype='<f8'),
                                     np.asarray(y[i], dtype='<f8')))
        if not np.isfinite(values).all():
            raise ValueError('transition cannot be represented as finite float64')
        values[values == 0] = 0.  # +0 and -0 are numerically the same.
        rows.add(hashlib.sha256(values.tobytes()).digest())
    return rows


def _validated_inputs(new, replay, old_holdout, new_holdout, steps, replay_fraction, seed):
    if (type(steps) is not int or not 1 <= steps <= original.MAX_STEPS
            or type(seed) is not int or not 0 <= seed < 2**63
            or type(replay_fraction) not in (float, int)
            or not 0 <= replay_fraction <= 1 or not np.isfinite(replay_fraction)):
        raise ValueError('invalid replay budget')
    raw = (new, replay, old_holdout, new_holdout)
    if any(type(triple) not in (tuple, list) or len(triple) != 3 for triple in raw):
        raise ValueError('expected four transition triples')
    if any(type(array) is not np.ndarray for triple in raw for array in triple):
        raise ValueError('preallocated NumPy arrays required')
    if sum(array.nbytes for triple in raw for array in triple) > MAX_TRANSITION_BYTES:
        raise ValueError('transition byte budget exceeded')
    transitions = tuple(original._transition(value, label) for value, label in (
        (new, 'new'), (replay, 'replay'), (old_holdout, 'old_holdout'), (new_holdout, 'new_holdout')))
    if len({(x.shape[1], a.shape[1]) for x, a, _ in transitions}) != 1:
        raise ValueError('incompatible JEPA transition dimensions')
    # Caller-owned arrays must not be changed between split checking, sampling,
    # and the held-out measurements. This is a memory snapshot, not verified
    # historical source lineage or atomic capture from a concurrent writer.
    transitions = tuple(tuple(np.array(array, copy=True, order='C', subok=False)
                              for array in triple) for triple in transitions)
    for value, label in zip(transitions, ('new', 'replay', 'old_holdout', 'new_holdout')):
        original._transition(value, label)
    fingerprints = tuple(_row_fingerprints(t) for t in transitions)
    if any(fingerprints[i] & fingerprints[j] for i, j in
           ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))):
        raise ValueError('exact transition occurs in multiple splits')
    return transitions


def _mixture(new, replay, replay_fraction, seed):
    n_rows, r_rows = len(new[0]), len(replay[0])
    count = min(original.MAX_ROWS, n_rows + r_rows)
    r_count = min(r_rows, round(count * replay_fraction))
    n_count = min(n_rows, count - r_count)
    if n_count < 2:
        raise ValueError('insufficient new transitions')
    r_count = min(r_count, count - n_count)
    rng = np.random.default_rng(seed)
    ni = rng.choice(n_rows, n_count, replace=False)
    ri = rng.choice(r_rows, r_count, replace=False)
    selected = tuple(np.concatenate((new[k][ni], replay[k][ri]), axis=0) for k in range(3))
    return selected, n_count, r_count


def _plain_model_containers(model):
    """Avoid arbitrary conversion/deepcopy hooks in a caller-supplied state."""
    if (set(model.__dict__) != _REQUIRED_STATE or type(model.seed) is not int
            or type(model.ensemble) is not int or type(model._fit_steps) is not int
            or type(model._nn_med) is not float or type(model.history) is not list
            or len(model.history) > 100000 or type(model.enc) is not dict
            or type(model.tgt) is not dict or type(model.preds) is not list
            or len(model.preds) != model.ensemble):
        raise ValueError('unsupported WorldJEPA state')
    if any(type(row) is not dict or any(type(k) is not str or type(v) not in (int, float)
                                         or not np.isfinite(v) for k, v in row.items())
           for row in model.history):
        raise ValueError('unsupported WorldJEPA history')
    if any(type(getattr(model, name)) is not np.ndarray for name in
           ('mu', 'sd', 'zsd', '_ztrain', '_action_counts')):
        raise ValueError('unsupported WorldJEPA array')
    for group, keys in ((model.enc, checkpoint.ENC_KEYS), (model.tgt, checkpoint.ENC_KEYS),
                        *((pred, checkpoint.PRED_KEYS) for pred in model.preds)):
        if (type(group) is not dict or len(group) != len(keys)
                or any(type(k) is not str for k in group)
                or set(group) != set(keys)
                or any(type(group[k]) is not np.ndarray for k in keys)):
            raise ValueError('unsupported WorldJEPA parameter containers')


def _detached_model(model):
    if type(model) is not wj.WorldJEPA:
        raise ValueError('reviewed fitted WorldJEPA instance required')
    with wj._WORLD_JEPA_IO_LOCK:
        _plain_model_containers(model)
        meta, source_arrays = checkpoint._extract(model, _VALIDATION_TAG)
        checkpoint._validate(meta, source_arrays, _VALIDATION_TAG)
        def cloned(name):
            return np.array(source_arrays[name], copy=True, order='C', subok=False)
        # Construct from validated numeric fields only; never execute a
        # caller-controlled __deepcopy__. Existing history is diagnostic and
        # is intentionally not copied into the proposal.
        staged = wj.WorldJEPA(seed=meta['seed'], ensemble=meta['ensemble'])
        staged.__dict__.update(
            _fit_steps=meta['fit_steps'], _action_counts=cloned('action_counts'),
            mu=cloned('mu'), sd=cloned('sd'), zsd=cloned('zsd'),
            _ztrain=cloned('ztrain'), _nn_med=float(source_arrays['nn_med'][0]),
            history=[],
            enc={k: cloned('enc__' + k) for k in checkpoint.ENC_KEYS},
            tgt={k: cloned('tgt__' + k) for k in checkpoint.ENC_KEYS},
            preds=[{k: cloned(f'pred{i}__{k}') for k in checkpoint.PRED_KEYS}
                   for i in range(meta['ensemble'])])
        staged_meta, staged_arrays = checkpoint._extract(staged, _VALIDATION_TAG)
        checkpoint._validate(staged_meta, staged_arrays, _VALIDATION_TAG)
        if staged is model or any(np.shares_memory(source_arrays[k], staged_arrays[k]) for k in source_arrays):
            raise ValueError('WorldJEPA copy is not detached')
        return staged


def preview_replay(model, new, replay, old_holdout, new_holdout, *,
                   steps=100, replay_fraction=.25, seed=0):
    """Return a detached proposal and finite measurements, without live update.

    Exact duplicate rows across provided splits are rejected. Source IDs,
    semantic near-duplicates, historical provenance and heldout quality are not
    independently verified. All model training happens on a detached clone.
    """
    _check_sources()
    n, r, old, fresh = _validated_inputs(new, replay, old_holdout, new_holdout,
                                         steps, replay_fraction, seed)
    mixture, new_count, replay_count = _mixture(n, r, replay_fraction, seed)
    staged = _detached_model(model)
    before_old, before_new = (float(staged.prediction_loss(*batch)) for batch in (old, fresh))
    if not all(np.isfinite(value) and value >= 0 for value in (before_old, before_new)):
        raise ValueError('nonfinite baseline retention')
    staged.partial_fit(*mixture, steps=steps, log_every=max(1, steps // 4))
    after_old, after_new = (float(staged.prediction_loss(*batch)) for batch in (old, fresh))
    if not all(np.isfinite(value) and value >= 0 for value in (after_old, after_new)):
        raise ValueError('nonfinite post-update retention')
    meta, arrays = checkpoint._extract(staged, _VALIDATION_TAG)
    checkpoint._validate(meta, arrays, _VALIDATION_TAG)
    report = {
        'scope': 'DETACHED_SHADOW_PREVIEW',
        'new_train_rows': new_count, 'replay_train_rows': replay_count,
        'requested_replay_fraction': float(replay_fraction),
        'actual_replay_fraction': replay_count / (new_count + replay_count),
        'old_holdout_before': before_old, 'old_holdout_after': after_old,
        'old_holdout_delta': after_old - before_old,
        'new_holdout_before': before_new, 'new_holdout_after': after_new,
        'new_holdout_delta': after_new - before_new,
        'exact_cross_split_duplicate_check': True,
        'source_id_disjointness_verified': False,
        'optimizer_state_continued': False,
        'fixed_target_retention_verified': False,
        'retention_measurement_scope': 'MOVING_EMA_TARGET_DIAGNOSTIC_ONLY',
        'live_model_updated': False, 'active_model_promoted': False,
        'pretrained_weights_changed': False,
    }
    return staged, report
