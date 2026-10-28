"""Private inference-only checkpoint for fitted NumPy WorldJEPA SHADOW.

No optimizer/EMA training resume, runtime hook, age authority or gate promotion.
No pickle/object deserialization. Never put trained checkpoints in public Git.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile
import zipfile

import numpy as np

from v13 import world_jepa as wj

SCHEMA = 'v13.world_jepa.shadow_inference_checkpoint.v1'
SHA = re.compile(r'[0-9a-f]{64}\Z')
MAX_BYTES = 32 * 1024 * 1024
MAX_UNCOMPRESSED = 64 * 1024 * 1024
MAX_META = 8192
ENC_KEYS = ('W1', 'b1', 'W2', 'b2')
PRED_KEYS = ('P1', 'c1', 'P2', 'c2')


def _pin(value):
    if type(value) is not str or not SHA.fullmatch(value):
        raise ValueError('Expected externally verified 64-hex SHA256')
    return value


def _meta_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def _strict_json(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('Duplicate checkpoint metadata key')
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite metadata')))


def _extract(model, source_sha256):
    if not all(hasattr(model, k) for k in
               ('enc', 'tgt', 'preds', 'mu', 'sd', 'zsd', '_ztrain',
                '_nn_med', '_action_counts', 'seed', 'ensemble')):
        raise ValueError('WorldJEPA must be fitted before inference export')
    meta = {'schema': SCHEMA, 'source_sha256': _pin(source_sha256),
            'model_revision': wj.REVISION, 'seed': model.seed,
            'ensemble': model.ensemble}
    arrays = {
        'mu': np.asarray(model.mu),
        'sd': np.asarray(model.sd),
        'zsd': np.asarray(model.zsd),
        'ztrain': np.asarray(model._ztrain),
        'nn_med': np.asarray([model._nn_med]),
        'action_counts': np.asarray(model._action_counts),
    }
    for name, values in (('enc', model.enc), ('tgt', model.tgt)):
        if type(values) is not dict or set(values) != set(ENC_KEYS):
            raise ValueError('Incomplete WorldJEPA encoder')
        for key in ENC_KEYS:
            arrays[name + '__' + key] = np.asarray(values[key])
    if type(model.preds) is not list or len(model.preds) != model.ensemble:
        raise ValueError('Incomplete WorldJEPA predictor ensemble')
    for i, pred in enumerate(model.preds):
        if type(pred) is not dict or set(pred) != set(PRED_KEYS):
            raise ValueError('Incomplete WorldJEPA predictor')
        for key in PRED_KEYS:
            arrays[f'pred{i}__{key}'] = np.asarray(pred[key])
    return meta, arrays


def _validate(meta, arrays, source_sha256):
    if (type(meta) is not dict or set(meta) !=
            {'schema', 'source_sha256', 'model_revision', 'seed', 'ensemble'}
            or meta['schema'] != SCHEMA or meta['source_sha256'] != _pin(source_sha256)
            or meta['model_revision'] != wj.REVISION
            or type(meta['seed']) is not int or not 0 <= meta['seed'] <= 2**63-1
            or type(meta['ensemble']) is not int or not 1 <= meta['ensemble'] <= 16):
        raise ValueError('WorldJEPA checkpoint source/revision/config mismatch')
    a = arrays.get('action_counts')
    mu = arrays.get('mu')
    ztr = arrays.get('ztrain')
    if (not isinstance(a, np.ndarray) or a.ndim != 1 or not 1 <= len(a) <= 64
            or a.dtype != np.dtype('int64') or np.any(a < 0)
            or sum(int(x) for x in a) > len(ztr)
            or not isinstance(mu, np.ndarray) or mu.ndim != 1 or not 1 <= len(mu) <= 4096
            or not isinstance(ztr, np.ndarray) or ztr.ndim != 2
            or not 2 <= len(ztr) <= 100000 or ztr.shape[1] != wj.Z):
        raise ValueError('Invalid WorldJEPA calibration dimensions')
    d, actions, n = len(mu), len(a), len(ztr)
    expected = {
        'mu': (d,), 'sd': (d,), 'zsd': (wj.Z,),
        'ztrain': (n, wj.Z), 'nn_med': (1,), 'action_counts': (actions,),
    }
    enc = {'W1': (wj.H, d), 'b1': (wj.H,),
           'W2': (wj.Z, wj.H), 'b2': (wj.Z,)}
    pred = {'P1': (wj.HP, wj.Z + actions), 'c1': (wj.HP,),
            'P2': (wj.Z, wj.HP), 'c2': (wj.Z,)}
    for name in ('enc', 'tgt'):
        expected.update({name + '__' + k: shape for k, shape in enc.items()})
    for i in range(meta['ensemble']):
        expected.update({f'pred{i}__{k}': shape for k, shape in pred.items()})
    if set(arrays) != set(expected):
        raise ValueError('Missing or unexpected WorldJEPA checkpoint arrays')
    for name, shape in expected.items():
        value = arrays[name]
        if not isinstance(value, np.ndarray) or value.shape != shape:
            raise ValueError('WorldJEPA checkpoint shape mismatch: ' + name)
        if name != 'action_counts':
            if value.dtype != np.dtype('float64') or not np.isfinite(value).all():
                raise ValueError('Nonfinite or non-float64 checkpoint array: ' + name)
    if (np.any(arrays['sd'] <= 0) or np.any(arrays['zsd'] <= 0)
            or arrays['nn_med'][0] <= 0):
        raise ValueError('Invalid WorldJEPA positive calibration')
    return True


def _sync_dir(parent):
    fd = os.open(parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(model, path, source_sha256):
    """Exclusive, fsynced private NPZ export; returns hash to pin externally."""
    meta, arrays = _extract(model, source_sha256)
    # Never coerce source tensors: fractional support counts or low-precision
    # weights would otherwise silently change inference/calibration evidence.
    arrays = {k: np.asarray(v) for k, v in arrays.items()}
    _validate(meta, arrays, source_sha256)
    raw_meta = _meta_json(meta)
    if len(raw_meta) > MAX_META:
        raise ValueError('Oversized WorldJEPA metadata')
    stream = io.BytesIO()
    np.savez_compressed(stream, meta=np.frombuffer(raw_meta, dtype=np.uint8),
                        **arrays)
    data = stream.getvalue()
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError('WorldJEPA checkpoint outside size bounds')
    path = Path(path)
    if (not path.parent.is_dir() or path.parent.is_symlink()
            or path.exists() or path.is_symlink()):
        raise ValueError('Private checkpoint destination must be fresh')
    fd, temp = tempfile.mkstemp(prefix='.world-jepa-shadow-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.link(temp, path)  # exclusive; never overwrite an existing target
        _sync_dir(path.parent)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return {'schema': SCHEMA, 'source_sha256': source_sha256,
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'scope': 'PRIVATE_INFERENCE_ONLY_SHADOW', 'age_authority': 0,
            'optimizer_state_persisted': False}


def load(path, source_sha256, expected_sha256):
    """Verify exact external pins and safe NPZ arrays before constructing a model."""
    _pin(source_sha256)
    _pin(expected_sha256)
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_BYTES):
        raise ValueError('Missing/unsafe WorldJEPA checkpoint file')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('WorldJEPA checkpoint bytes changed')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        info = archive.infolist()
        if (not info or len(info) > 128 or
                len({x.filename for x in info}) != len(info) or
                any('/' in x.filename or '\\' in x.filename or not x.filename.endswith('.npy')
                    or x.file_size > MAX_UNCOMPRESSED for x in info) or
                sum(x.file_size for x in info) > MAX_UNCOMPRESSED):
            raise ValueError('Unsafe WorldJEPA NPZ archive members')
    with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
        if 'meta' not in archive.files:
            raise ValueError('Missing WorldJEPA checkpoint metadata')
        meta_bytes = archive['meta']
        if (meta_bytes.dtype != np.uint8 or meta_bytes.ndim != 1
                or not 0 < len(meta_bytes) <= MAX_META):
            raise ValueError('Invalid WorldJEPA metadata encoding')
        meta = _strict_json(meta_bytes.tobytes().decode('utf-8'))
        arrays = {name: archive[name].copy() for name in archive.files if name != 'meta'}
    _validate(meta, arrays, source_sha256)
    model = wj.WorldJEPA(seed=meta['seed'], ensemble=meta['ensemble'])
    model.mu, model.sd, model.zsd = (arrays[k] for k in ('mu', 'sd', 'zsd'))
    model._ztrain, model._nn_med = arrays['ztrain'], float(arrays['nn_med'][0])
    model._action_counts = arrays['action_counts']
    model.enc = {k: arrays['enc__' + k] for k in ENC_KEYS}
    model.tgt = {k: arrays['tgt__' + k] for k in ENC_KEYS}
    model.preds = [{k: arrays[f'pred{i}__{k}'] for k in PRED_KEYS}
                   for i in range(meta['ensemble'])]
    model.history = []  # training history/optimizer not present: inference-only
    return model
