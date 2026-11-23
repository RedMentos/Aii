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




CHECKPOINT_NAME = re.compile(r'jepa-[0-9a-f]{32}\.npz\Z')
PENDING_PREFIX = '.world-jepa-shadow-'
FALLBACK_LINK_ERRNOS = frozenset((errno.EPERM, errno.EACCES, errno.ENOSYS,
                                  errno.EOPNOTSUPP, errno.ENOTSUP))


def _private_dir_fd(parent):
    if not hasattr(os, 'O_DIRECTORY') or not hasattr(os, 'O_NOFOLLOW'):
        raise OSError(errno.ENOSYS, 'safe checkpoint directory open unavailable')
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077):
            raise ValueError('WorldJEPA checkpoint directory is not private')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _hardlink_named_no_replace(dir_fd, source, dest):
    """Atomically hard-link two verified names in one directory, never replacing."""
    try:
        linkat = ctypes.CDLL(None, use_errno=True).linkat
    except (AttributeError, OSError) as exc:
        raise OSError(errno.ENOSYS, 'linkat unavailable') from exc
    linkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                       ctypes.c_char_p, ctypes.c_int]
    linkat.restype = ctypes.c_int
    if linkat(dir_fd, os.fsencode(source), dir_fd, os.fsencode(dest), 0) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), dest)


def _rename_named_no_replace(dir_fd, source, dest):
    """Android-safe same-directory publication when ordinary hardlinks are denied."""
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError) as exc:
        raise OSError(errno.ENOSYS, 'renameat2 unavailable') from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p,
                          ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if renameat2(dir_fd, os.fsencode(source), dir_fd,
                 os.fsencode(dest), 1) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), dest)


def _verify_published(dir_fd, name, identity, size, expected_sha256, link_counts):
    info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode)
            or (info.st_dev, info.st_ino) != identity
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size != size or info.st_nlink not in link_counts):
        raise ValueError('WorldJEPA checkpoint publication identity mismatch')
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != identity
                or opened.st_uid != os.getuid()
                or stat.S_IMODE(opened.st_mode) != 0o600
                or opened.st_size != size or opened.st_nlink not in link_counts):
            raise ValueError('WorldJEPA checkpoint opened inode changed')
        digest = hashlib.sha256()
        count = 0
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
            count += len(block)
        if count != size or digest.hexdigest() != expected_sha256:
            raise ValueError('WorldJEPA checkpoint published bytes changed')
    finally:
        os.close(fd)
    return info


def _unlink_if_identity(dir_fd, name, identity):
    try:
        info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if (info.st_dev, info.st_ino) != identity:
        return False
    os.unlink(name, dir_fd=dir_fd)
    return True


def cleanup_pending(parent):
    """Reap only our private crash-left staging names under the consumer lock.

    A one-link pending inode was interrupted before publication. A two-link
    inode is removed only when its other name is a matching jepa-*.npz target.
    Unknown names, symlinks, foreign owners and ambiguous link counts fail closed.
    """
    parent = Path(parent)
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError('unsafe WorldJEPA checkpoint directory')
    dir_fd = _private_dir_fd(parent)
    try:
        names = os.listdir(dir_fd)
        removed = 0
        for name in names:
            if not name.startswith(PENDING_PREFIX):
                continue
            if '/' in name or '\\' in name or name in ('.', '..'):
                raise ValueError('unsafe pending WorldJEPA checkpoint name')
            info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise ValueError('unsafe pending WorldJEPA checkpoint entry')
            if info.st_nlink == 2:
                linked_target = False
                for candidate in names:
                    if not CHECKPOINT_NAME.fullmatch(candidate):
                        continue
                    try:
                        other = os.stat(candidate, dir_fd=dir_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    if (stat.S_ISREG(other.st_mode)
                            and (other.st_dev, other.st_ino) == (info.st_dev, info.st_ino)):
                        linked_target = True
                        break
                if not linked_target:
                    raise ValueError('pending checkpoint link has no verified target')
            elif info.st_nlink != 1:
                raise ValueError('ambiguous pending WorldJEPA checkpoint link count')
            os.unlink(name, dir_fd=dir_fd)
            removed += 1
        if removed:
            os.fsync(dir_fd)
        return removed
    finally:
        os.close(dir_fd)


def save(model, path, source_sha256):
    """Exclusive, fsynced, no-clobber NPZ export with Android hardlink fallback."""
    meta, arrays = _extract(model, source_sha256)
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
            or path.exists() or path.is_symlink()
            or not path.name or path.name in ('.', '..')):
        raise ValueError('Private checkpoint destination must be fresh')
    dir_fd = _private_dir_fd(path.parent)
    fd = None
    temp_name = None
    temp_identity = None
    published = False
    expected_sha256 = hashlib.sha256(data).hexdigest()
    try:
        fd, temp = tempfile.mkstemp(prefix=PENDING_PREFIX, dir=path.parent)
        temp_name = Path(temp).name
        initial = os.fstat(fd)
        if (not stat.S_ISREG(initial.st_mode) or initial.st_uid != os.getuid()
                or stat.S_IMODE(initial.st_mode) != 0o600 or initial.st_nlink != 1):
            raise ValueError('unsafe WorldJEPA temporary checkpoint')
        temp_identity = (initial.st_dev, initial.st_ino)
        out = os.fdopen(fd, 'wb')
        fd = None
        with out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        staged = os.stat(temp_name, dir_fd=dir_fd, follow_symlinks=False)
        if ((staged.st_dev, staged.st_ino) != temp_identity
                or not stat.S_ISREG(staged.st_mode)
                or staged.st_uid != os.getuid()
                or stat.S_IMODE(staged.st_mode) != 0o600
                or staged.st_nlink != 1 or staged.st_size != len(data)):
            raise ValueError('WorldJEPA temporary checkpoint changed before publish')
        try:
            _hardlink_named_no_replace(dir_fd, temp_name, path.name)
        except OSError as exc:
            if exc.errno not in FALLBACK_LINK_ERRNOS:
                raise
            _rename_named_no_replace(dir_fd, temp_name, path.name)
        published = True
        _verify_published(dir_fd, path.name, temp_identity, len(data),
                          expected_sha256, (1, 2))
        _unlink_if_identity(dir_fd, temp_name, temp_identity)
        try:
            os.stat(temp_name, dir_fd=dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('WorldJEPA pending name changed during publish')
        _verify_published(dir_fd, path.name, temp_identity, len(data),
                          expected_sha256, (1,))
        os.fsync(dir_fd)
    except BaseException:
        if temp_name is not None and temp_identity is not None:
            _unlink_if_identity(dir_fd, temp_name, temp_identity)
        if published and temp_identity is not None:
            _unlink_if_identity(dir_fd, path.name, temp_identity)
        try:
            os.fsync(dir_fd)
        except OSError:
            pass
        raise
    finally:
        if fd is not None:
            os.close(fd)
        os.close(dir_fd)
    return {'schema': SCHEMA, 'source_sha256': source_sha256,
            'sha256': expected_sha256, 'bytes': len(data),
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
