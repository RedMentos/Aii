"""Private fitted NumPy WorldJEPA SHADOW checkpoint.

Stores numeric model/EMA state and, when present, validated Adam/inverse/RNG resume
state in the same atomic archive. No age authority or gate promotion. No pickle/object
deserialization. Never put trained checkpoints in public Git.
"""
from __future__ import annotations

import ctypes
import errno
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import tempfile
import zipfile

import numpy as np

from v13 import world_jepa as wj
from v13 import world_jepa_training_state as training_state

SCHEMA = 'v13.world_jepa.shadow_inference_checkpoint.v2'
LEGACY_SCHEMA = 'v13.world_jepa.shadow_inference_checkpoint.v1'
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


@wj._read_locked
def _extract(model, source_sha256):
    if not all(hasattr(model, k) for k in
               ('enc', 'tgt', 'preds', 'mu', 'sd', 'zsd', '_ztrain',
                '_nn_med', '_action_counts', 'seed', 'ensemble')):
        raise ValueError('WorldJEPA must be fitted before inference export')
    if type(getattr(model, '_fit_steps', None)) is not int or model._fit_steps <= 0:
        raise ValueError('WorldJEPA zero-step or missing training-step evidence')
    meta = {'schema': SCHEMA, 'source_sha256': _pin(source_sha256),
            'model_revision': wj.REVISION, 'seed': model.seed,
            'ensemble': model.ensemble, 'fit_steps': model._fit_steps}
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
    if hasattr(model, '_training_state'):
        meta['training_resume'], extra = training_state.pack(model)
        arrays.update(extra)
    return meta, arrays


def _validate(meta, arrays, source_sha256):
    if type(meta) is dict and 'training_resume' in meta:
        numeric_meta = {k:v for k,v in meta.items() if k != 'training_resume'}
        numeric = {k:v for k,v in arrays.items() if not k.startswith(training_state.PREFIX)}
        extra = {k:v for k,v in arrays.items() if k.startswith(training_state.PREFIX)}
        _validate(numeric_meta, numeric, source_sha256)
        training_state.validate_payload(meta['training_resume'], extra, numeric_meta, numeric)
        return True
    # v1 had no optimizer-step evidence. Read it for numeric inference only;
    # its loaded confidence must remain SIMULATION_UNCERTAIN. New v2 archives
    # bind a positive integer step count and never silently upgrade v1.
    if type(meta) is not dict:
        raise ValueError('WorldJEPA checkpoint metadata invalid')
    legacy = meta.get('schema') == LEGACY_SCHEMA
    expected = {'schema', 'source_sha256', 'model_revision', 'seed', 'ensemble'}
    if not legacy:
        expected.add('fit_steps')
    if (set(meta) != expected
            or meta.get('schema') not in (SCHEMA, LEGACY_SCHEMA)
            or meta.get('source_sha256') != _pin(source_sha256)
            or meta.get('model_revision') != wj.REVISION
            or type(meta.get('seed')) is not int or not 0 <= meta['seed'] <= 2**63-1
            or type(meta.get('ensemble')) is not int or not 1 <= meta['ensemble'] <= 16
            or (not legacy and (type(meta.get('fit_steps')) is not int
                                or not 1 <= meta['fit_steps'] <= 10**9))):
        raise ValueError('WorldJEPA checkpoint source/revision/config mismatch')
    a = arrays.get('action_counts')
    mu = arrays.get('mu')
    ztr = arrays.get('ztrain')
    # Validate all array types/shapes before using their lengths. A corrupt
    # NPZ can otherwise raise TypeError instead of a controlled rejection.
    if (not isinstance(a, np.ndarray) or a.ndim != 1 or not 1 <= len(a) <= 64
            or a.dtype != np.dtype('int64') or np.any(a < 0)
            or not isinstance(mu, np.ndarray) or mu.ndim != 1 or not 1 <= len(mu) <= 4096
            or not isinstance(ztr, np.ndarray) or ztr.ndim != 2
            or not 2 <= len(ztr) <= 100000 or ztr.shape[1] != wj.Z
            or sum(int(x) for x in a) > len(ztr)):
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



_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAMEAT2_SYSCALLS = {
    'x86_64': 316, 'amd64': 316, 'aarch64': 276, 'arm64': 276,
    'arm64-v8a': 276, 'riscv64': 276, 'armv7l': 382, 'i386': 353, 'i686': 353,
}


def _renameat2_noreplace(source, destination):
    """Atomically rename within one directory without replacing a target.

    Android/Linux expose renameat2 on supported kernels. Prefer the libc symbol;
    use the architecture syscall number when Bionic/libc does not export it.
    There is deliberately no unsafe os.rename fallback.
    """
    source_b = os.fsencode(source)
    destination_b = os.fsencode(destination)
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, 'renameat2', None)
    if renameat2 is not None:
        renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                              ctypes.c_char_p, ctypes.c_uint)
        renameat2.restype = ctypes.c_int
        result = renameat2(_AT_FDCWD, source_b, _AT_FDCWD, destination_b,
                           _RENAME_NOREPLACE)
    else:
        number = _RENAMEAT2_SYSCALLS.get(platform.machine().lower())
        syscall = getattr(libc, 'syscall', None)
        if number is None or syscall is None:
            raise OSError(errno.ENOSYS, 'renameat2(RENAME_NOREPLACE) unavailable',
                          os.fsdecode(destination_b))
        syscall.restype = ctypes.c_long
        result = syscall(ctypes.c_long(number), ctypes.c_int(_AT_FDCWD),
                         ctypes.c_char_p(source_b), ctypes.c_int(_AT_FDCWD),
                         ctypes.c_char_p(destination_b), ctypes.c_uint(_RENAME_NOREPLACE))
    if result != 0:
        error = ctypes.get_errno() or errno.EIO
        raise OSError(error, os.strerror(error), os.fsdecode(destination_b))


def _file_identity(info):
    return info.st_dev, info.st_ino


def _verify_published(path, original, expected_sha256, expected_size):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode)
                or _file_identity(before) != _file_identity(original)
                or before.st_size != expected_size):
            raise ValueError('WorldJEPA published checkpoint identity/size mismatch')
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
        after = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        if (_file_identity(after) != _file_identity(before)
                or _file_identity(named) != _file_identity(before)
                or not stat.S_ISREG(named.st_mode)
                or total != expected_size
                or after.st_size != expected_size
                or named.st_size != expected_size):
            raise ValueError('WorldJEPA checkpoint changed during publication verification')
        if digest.hexdigest() != expected_sha256:
            raise ValueError('WorldJEPA published checkpoint hash mismatch')
    finally:
        os.close(fd)


def _publish_exclusive(temp, path, expected_sha256, expected_size):
    """Publish a same-directory temp file without ever replacing a checkpoint.

    Hardlinks remain the preferred fast path. Android filesystems that deny them
    with EPERM/EACCES use atomic renameat2(RENAME_NOREPLACE). Both paths verify
    the exact inode and bytes, remove the temporary name, then fsync the parent.
    """
    original = os.stat(temp, follow_symlinks=False)
    if (not stat.S_ISREG(original.st_mode) or original.st_nlink != 1
            or original.st_size != expected_size):
        raise ValueError('WorldJEPA temporary checkpoint identity/size mismatch')
    published = False
    try:
        try:
            os.link(temp, path)
        except OSError as exc:
            if exc.errno not in (errno.EPERM, errno.EACCES):
                raise
            _renameat2_noreplace(temp, path)
        published = True
        _verify_published(path, original, expected_sha256, expected_size)
        try:
            current_temp = os.stat(temp, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if (_file_identity(current_temp) != _file_identity(original)
                    or not stat.S_ISREG(current_temp.st_mode)):
                raise ValueError('WorldJEPA temporary checkpoint changed before cleanup')
            os.unlink(temp)
        _sync_dir(path.parent)
    except BaseException:
        # If verification or durability fails after publication, remove only the
        # exact inode this call created. A racing replacement is never deleted.
        if published:
            try:
                current = os.stat(path, follow_symlinks=False)
                if (_file_identity(current) == _file_identity(original)
                        and stat.S_ISREG(current.st_mode)):
                    os.unlink(path)
                    try:
                        _sync_dir(path.parent)
                    except OSError:
                        pass
            except OSError:
                pass
        raise
    finally:
        # A successful rename consumes the temp name; a hardlink leaves it.
        # Clean up only the original temp inode, never a swapped-in path.
        try:
            current_temp = os.stat(temp, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if (_file_identity(current_temp) == _file_identity(original)
                    and stat.S_ISREG(current_temp.st_mode)):
                os.unlink(temp)


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
        _publish_exclusive(temp, path, hashlib.sha256(data).hexdigest(), len(data))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return {'schema': SCHEMA, 'source_sha256': source_sha256,
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'scope': ('PRIVATE_SHADOW_TRAINING_RESUME' if hasattr(model, '_training_state') else 'PRIVATE_INFERENCE_ONLY_SHADOW'),
            'age_authority': 0,
            'optimizer_state_persisted': hasattr(model, '_training_state'),
            'optimizer_state_bootstrapped': (meta.get('training_resume', {}).get('origin') == 'BOOTSTRAPPED_FROM_INFERENCE_ONLY')}


def load(path, source_sha256, expected_sha256):
    """Verify exact external pins and safe NPZ arrays before constructing a model."""
    _pin(source_sha256)
    _pin(expected_sha256)
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_BYTES):
        raise ValueError('Missing/unsafe WorldJEPA checkpoint file')
    raw = training_state.read_checkpoint(path, MAX_BYTES)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('WorldJEPA checkpoint bytes changed')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        info = archive.infolist()
        if (not info or len(info) > 512 or
                len({x.filename for x in info}) != len(info) or
                any('/' in x.filename or '\\' in x.filename or not x.filename.endswith('.npy')
                    or x.file_size > MAX_UNCOMPRESSED for x in info) or
                sum(x.file_size for x in info) > MAX_UNCOMPRESSED):
            raise ValueError('Unsafe WorldJEPA NPZ archive members')
    training_state.validate_archive(raw)
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
    model.history = []  # per-fit diagnostics are transient; resume state is restored separately
    model._fit_steps = 0 if meta['schema'] == LEGACY_SCHEMA else meta['fit_steps']
    if 'training_resume' in meta:
        model._training_state = training_state.unpack(
            meta['training_resume'],
            {k:v for k,v in arrays.items() if k.startswith(training_state.PREFIX)},
            {k:v for k,v in meta.items() if k != 'training_resume'},
            {k:v for k,v in arrays.items() if not k.startswith(training_state.PREFIX)},
        )
    return model
