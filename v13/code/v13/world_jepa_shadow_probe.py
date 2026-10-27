"""Explicit local-only read-only World-JEPA SHADOW probe.

This is a manual experiment on a calibrated v2 slot predictor. It never
supplies answer facts, trains weights, executes actions or changes Age gates.
Bindings survive restart; every prediction rechecks the whole-file digest.
"""
import json
import re
from pathlib import Path
import numpy as np

from .world_jepa_slots import SlotWorldJEPA

KEY = 'WORLD_JEPA_SHADOW_BINDING_V1'
MAX_QUERY_CHARS = 65536
MAX_SAMPLES = 4
MAX_OUTPUT_CELLS = 32768
_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\.npz\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _digest(value):
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise ValueError('Expected exact lowercase 64-hex SHA256')
    return value


def _path(runtime, name):
    if type(name) is not str or _NAME.fullmatch(name) is None:
        raise ValueError('Only a simple .npz checkpoint basename is allowed')
    home = Path(runtime.home).resolve()
    parent = Path(runtime.home) / 'checkpoints'
    root = parent / 'world_jepa'
    if (parent.is_symlink() or root.is_symlink() or not root.is_dir()
            or root.resolve().parent != parent.resolve()
            or not root.resolve().is_relative_to(home)):
        raise ValueError('World-JEPA checkpoint directory unavailable or outside home')
    path = root / name
    if (path.is_symlink() or not path.is_file()
            or path.resolve().parent != root.resolve()):
        raise ValueError('World-JEPA checkpoint must be a regular file in the dedicated directory')
    return path


def _binding(runtime):
    st, _ = runtime.store.state(KEY)
    if not st:
        return None
    if (type(st) is not dict or type(st.get('name')) is not str
            or type(st.get('provenance')) is not dict):
        raise ValueError('Malformed persisted World-JEPA SHADOW binding')
    return st


def _load_bound(runtime, binding):
    path = _path(runtime, binding['name'])
    return SlotWorldJEPA.load(
        path, expected_provenance=binding['provenance'],
        expected_sha256=_digest(binding['sha256']))


def _reject_constant(value):
    raise ValueError('Nonfinite JSON constant')


def _numbers_only(value):
    if type(value) is list:
        return all(_numbers_only(x) for x in value)
    return type(value) in (int, float)


def _array(raw, ndim):
    if type(raw) is not str or not 1 <= len(raw) <= MAX_QUERY_CHARS:
        raise ValueError('Bounded JSON array required')
    try:
        value = json.loads(raw, parse_constant=_reject_constant)
        if type(value) is not list or not _numbers_only(value):
            raise ValueError('Only numeric JSON arrays are accepted')
        arr = np.asarray(value, dtype=np.float64)
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError('Invalid numeric JSON array') from exc
    if arr.ndim != ndim or not np.isfinite(arr).all():
        raise ValueError('Nonfinite or wrong-rank array')
    return arr


def operator_command(runtime, args):
    """Manual :world shadow [status|load|predict|unload]. Never a live hook."""
    if not args or args == ['status']:
        binding = _binding(runtime)
        return ({'status': 'UNBOUND', 'mode': 'MANUAL_SHADOW_ONLY',
                 'automatic_turn_activation': False, 'truth_authority': False}
                if binding is None else
                {'status': 'BOUND_UNVERIFIED', 'mode': 'MANUAL_SHADOW_ONLY',
                 'name': binding['name'], 'sha256': binding['sha256'],
                 'automatic_turn_activation': False, 'truth_authority': False})
    action = args[0]
    if action == 'load' and len(args) == 5:
        name, sha, cohort, source = args[1:]
        binding = {'name': name, 'sha256': _digest(sha),
                   'provenance': {'cohort_sha256': _digest(cohort),
                                  'source_sha256': _digest(source)}}
        model = _load_bound(runtime, binding)  # verify BEFORE persisting authority-free binding
        binding.update({'slots': model.S, 'input_dim': len(model.mu),
                        'op_dim': len(model.op_counts), 'latent_dim': model.k})
        _, version = runtime.store.state(KEY)
        runtime.store.set_state(KEY, binding, expected=version)
        return {'status': 'VERIFIED_SHADOW_BOUND', 'mode': 'MANUAL_SHADOW_ONLY',
                'slots': model.S, 'checkpoint_sha256': sha,
                'automatic_turn_activation': False, 'truth_authority': False}
    if action == 'unload' and len(args) == 1:
        _, version = runtime.store.state(KEY)
        runtime.store.set_state(KEY, {}, expected=version)
        return {'status': 'UNBOUND', 'checkpoint_deleted': False,
                'automatic_turn_activation': False, 'truth_authority': False}
    if action == 'predict' and len(args) == 3:
        binding = _binding(runtime)
        if binding is None:
            raise ValueError('No verified World-JEPA SHADOW binding')
        model = _load_bound(runtime, binding)  # recheck bytes/provenance on EVERY query
        X = _array(args[1], 2)
        A = _array(args[2], 3)
        n = len(X)
        if (not 1 <= n <= MAX_SAMPLES or len(A) != n
                or X.shape[1] != model.S * len(model.mu)
                or A.shape[1:] != (model.S, len(model.op_counts))
                or n * model.S * model.k > MAX_OUTPUT_CELLS
                or not np.logical_or(A == 0., A == 1.).all()
                or not np.all(A.sum(2) == 1.)):
            raise ValueError('SHADOW query shape, size or one-hot action mismatch')
        prediction, spread = model.predict(X, A)
        confidence, labels = model.confidence(X, A)
        if not all(np.isfinite(x).all() for x in (prediction, spread, confidence)):
            raise ValueError('Nonfinite SHADOW prediction')
        return {'status': 'MODEL_SIMULATION_ONLY', 'mode': 'MANUAL_SHADOW_ONLY',
                'prediction_latent': prediction.tolist(), 'spread': spread.tolist(),
                'confidence': confidence.tolist(), 'labels': labels,
                'checkpoint_sha256': binding['sha256'],
                'automatic_turn_activation': False, 'truth_authority': False}
    raise ValueError(':world shadow [status|load <name.npz> <sha256> <cohortsha256> <sourcesha256>|predict <X-json> <A-json>|unload]')
