"""Opt-in CPU B-JEPA adapter step checkpoints. No live learning/age authority.

Immutable step blobs plus an fsynced CURRENT pointer keep the previous good
checkpoint usable if a write crashes. Never publish training-state files to git.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

REVISION = 'body-jepa-step-checkpoint-v1'
SHA = re.compile(r'[0-9a-f]{64}\Z')
BLOB = re.compile(r'step-[0-9]{6,9}-[0-9a-f]{16}\.pt\Z')
MAX_BYTES = 2 * 1024**3


def _hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _atomic_json(path, obj):
    fd, tmp = tempfile.mkstemp(prefix='.pointer-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(obj, f, sort_keys=True, separators=(',', ':'))
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        _sync_dir(path.parent)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _finite_tree(value, depth=0):
    import torch
    if depth > 16:
        return False
    if isinstance(value, torch.Tensor):
        return bool(torch.isfinite(value).all()) if value.is_floating_point() or value.is_complex() else True
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) in (tuple, list):
        return len(value) < 100000 and all(_finite_tree(v, depth + 1) for v in value)
    if type(value) is dict:
        return len(value) < 100000 and all(type(k) in (str, int) and _finite_tree(v, depth + 1)
                                             for k, v in value.items())
    return False


def _params(model):
    result = {name: p for name, p in model.named_parameters() if p.requires_grad}
    if not result:
        raise ValueError('No trainable adapter parameters')
    return result


def _optimizer_layout(model, predictor, optimizer):
    names = {id(p): 'adapter:' + n for n, p in _params(model).items()}
    for n, p in predictor.named_parameters():
        if id(p) in names:
            raise ValueError('Shared adapter/predictor optimizer parameter')
        names[id(p)] = 'predictor:' + n
    groups = []
    seen = set()
    for group in optimizer.param_groups:
        row = []
        for p in group['params']:
            name = names.get(id(p))
            if name is None or name in seen:
                raise ValueError('Unbound or duplicate optimizer parameter')
            seen.add(name)
            row.append(name)
        groups.append(row)
    if seen != set(names.values()):
        raise ValueError('Optimizer omits a trainable parameter')
    return groups


def _validate_source(source_sha):
    if type(source_sha) is not str or not SHA.fullmatch(source_sha):
        raise ValueError('A full pinned source SHA256 is required')


def _root(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Checkpoint root cannot be a symlink')
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ValueError('Invalid checkpoint root')
    return path


def save(root, source_sha, step, model, predictor, optimizer, ema, generator, history):
    """Save a completed optimizer step. Does not change learning authority."""
    import torch
    _validate_source(source_sha)
    if type(step) is not int or not 1 <= step <= 999999999:
        raise ValueError('Invalid completed step')
    params = _params(model)
    if len(ema.params) != len(params) or any(a is not b for a, b in zip(ema.params, params.values())):
        raise ValueError('EMA does not own the exact trainable adapter')
    if type(ema.updates) is not int or ema.updates != step:
        raise ValueError('EMA updates must match the completed optimizer step')
    if type(history) is not list or len(history) != step or not _finite_tree(history):
        raise ValueError('Invalid step history')
    payload = {'revision': REVISION, 'source_sha256': source_sha, 'step': step,
               'adapter': {n: p.detach().cpu().clone() for n, p in params.items()},
               'predictor': {n: p.detach().cpu().clone() for n, p in predictor.state_dict().items()},
               'optimizer': optimizer.state_dict(),
               'optimizer_layout': _optimizer_layout(model, predictor, optimizer),
               'ema': [v.detach().cpu().clone() for v in ema.shadow],
               'ema_updates': ema.updates, 'generator_rng': generator.get_state().clone(),
               'torch_rng': torch.get_rng_state().clone(), 'history': history}
    if not _finite_tree(payload):
        raise ValueError('Nonfinite checkpoint state')
    root = _root(root)
    fd, tmp = tempfile.mkstemp(prefix='.step-', dir=root)
    try:
        with os.fdopen(fd, 'wb') as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        size = Path(tmp).stat().st_size
        if not 0 < size <= MAX_BYTES:
            raise ValueError('Checkpoint size outside bounds')
        sha = _hash(Path(tmp))
        name = f'step-{step:06d}-{sha[:16]}.pt'
        final = root / name
        try:
            os.link(tmp, final)
        except FileExistsError:
            if _hash(final) != sha:
                raise ValueError('Conflicting immutable checkpoint blob')
        _sync_dir(root)
        current = root / 'CURRENT.json'
        if current.exists():
            if current.is_symlink() or current.stat().st_size > 4096:
                raise ValueError('Untrusted prior checkpoint pointer')
            old = json.loads(current.read_text(encoding='utf-8'))
            if (type(old) is not dict or old.get('source_sha256') != source_sha
                    or type(old.get('step')) is not int or old['step'] >= step):
                raise ValueError('Checkpoint source changed or step did not advance')
        pointer = {'revision': REVISION, 'source_sha256': source_sha, 'step': step,
                   'file': name, 'size': size, 'sha256': sha}
        _atomic_json(current, pointer)
        return pointer
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def restore(root, source_sha, model, predictor, optimizer, ema, generator):
    """Verify before mutating any live state. None means no committed checkpoint."""
    import copy
    import torch
    _validate_source(source_sha)
    root = Path(root)
    pointer_path = root / 'CURRENT.json'
    if not pointer_path.exists():
        return None
    if root.is_symlink() or pointer_path.is_symlink() or not pointer_path.is_file():
        raise ValueError('Invalid checkpoint pointer')
    if pointer_path.stat().st_size > 4096:
        raise ValueError('Oversized checkpoint pointer')
    pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
    if (type(pointer) is not dict or set(pointer) != {'revision', 'source_sha256', 'step', 'file', 'size', 'sha256'}
            or pointer['revision'] != REVISION or pointer['source_sha256'] != source_sha
            or type(pointer['step']) is not int or not 1 <= pointer['step'] <= 999999999
            or type(pointer['file']) is not str or not BLOB.fullmatch(pointer['file'])
            or type(pointer['size']) is not int or not 0 < pointer['size'] <= MAX_BYTES
            or type(pointer['sha256']) is not str or not SHA.fullmatch(pointer['sha256'])):
        raise ValueError('Untrusted or cross-source checkpoint pointer')
    path = root / pointer['file']
    if (path.is_symlink() or not path.is_file() or path.stat().st_size != pointer['size']
            or _hash(path) != pointer['sha256']):
        raise ValueError('Missing or modified checkpoint blob')
    state = torch.load(path, map_location='cpu', weights_only=True)
    if (type(state) is not dict or set(state) != {'revision', 'source_sha256', 'step', 'adapter', 'predictor',
                                                 'optimizer', 'optimizer_layout', 'ema', 'ema_updates', 'generator_rng', 'torch_rng', 'history'}
            or state['revision'] != REVISION or state['source_sha256'] != source_sha
            or state['step'] != pointer['step'] or type(state['step']) is not int
            or type(state['ema_updates']) is not int or state['ema_updates'] != state['step']
            or type(state['history']) is not list or len(state['history']) != state['step']
            or not _finite_tree(state)):
        raise ValueError('Invalid checkpoint payload')
    params = _params(model)
    adapter = state['adapter']
    pred = state['predictor']
    expected_pred = predictor.state_dict()
    if (type(adapter) is not dict or set(adapter) != set(params)
            or type(pred) is not dict or set(pred) != set(expected_pred)
            or type(state['ema']) is not list or len(state['ema']) != len(params)
            or len(ema.params) != len(params)
            or any(a is not b for a, b in zip(ema.params, params.values()))):
        raise ValueError('Adapter/predictor/EMA structure mismatch')
    for name, param in params.items():
        t = adapter[name]
        if not isinstance(t, torch.Tensor) or t.shape != param.shape or t.dtype != param.dtype:
            raise ValueError('Adapter tensor mismatch')
    for name, expected in expected_pred.items():
        t = pred[name]
        if not isinstance(t, torch.Tensor) or t.shape != expected.shape or t.dtype != expected.dtype:
            raise ValueError('Predictor tensor mismatch')
    for shadow, param in zip(state['ema'], params.values()):
        if not isinstance(shadow, torch.Tensor) or shadow.shape != param.shape or shadow.dtype != param.dtype:
            raise ValueError('EMA tensor mismatch')
    if (not isinstance(state['generator_rng'], torch.Tensor) or state['generator_rng'].dtype != torch.uint8
            or state['generator_rng'].shape != generator.get_state().shape
            or not isinstance(state['torch_rng'], torch.Tensor) or state['torch_rng'].dtype != torch.uint8
            or state['torch_rng'].shape != torch.get_rng_state().shape):
        raise ValueError('Invalid RNG state')
    if state['optimizer_layout'] != _optimizer_layout(model, predictor, optimizer):
        raise ValueError('Optimizer parameter names/order differ from checkpoint')
    incoming = state['optimizer']
    current = optimizer.state_dict()
    if (type(incoming) is not dict or set(incoming) != {'state', 'param_groups'}
            or type(incoming['param_groups']) is not list
            or len(incoming['param_groups']) != len(current['param_groups'])):
        raise ValueError('Optimizer groups mismatch')
    for new, old in zip(incoming['param_groups'], current['param_groups']):
        if (type(new) is not dict or set(new) != set(old)
                or len(new['params']) != len(old['params'])
                or any(new[k] != old[k] for k in old if k != 'params')):
            raise ValueError('Optimizer source/config mismatch')
    param_by_name = {'adapter:' + n: p for n, p in params.items()}
    param_by_name.update({'predictor:' + n: p for n, p in predictor.named_parameters()})
    known_ids = set()
    for group, names in zip(incoming['param_groups'], state['optimizer_layout']):
        for pid, name in zip(group['params'], names):
            if type(pid) is not int or pid in known_ids:
                raise ValueError('Duplicate or invalid optimizer state id')
            known_ids.add(pid)
            slot = incoming['state'].get(pid, {})
            if type(slot) is not dict:
                raise ValueError('Invalid optimizer state slot')
            for moment in ('exp_avg', 'exp_avg_sq', 'max_exp_avg_sq'):
                if moment in slot and (not isinstance(slot[moment], torch.Tensor)
                                       or slot[moment].shape != param_by_name[name].shape):
                    raise ValueError('Optimizer moment shape mismatch')
    if set(incoming['state']) - known_ids:
        raise ValueError('Orphan optimizer state id')
    old_params = {n: p.detach().clone() for n, p in params.items()}
    old_pred = copy.deepcopy(predictor.state_dict())
    old_opt = copy.deepcopy(current)
    old_ema = [p.clone() for p in ema.shadow]
    old_updates = ema.updates
    old_g = generator.get_state().clone()
    old_rng = torch.get_rng_state().clone()
    try:
        with torch.no_grad():
            for name, param in params.items():
                param.copy_(adapter[name].to(device=param.device))
        predictor.load_state_dict(pred, strict=True)
        optimizer.load_state_dict(incoming)
        ema.shadow = [p.to(device=q.device).clone() for p, q in zip(state['ema'], params.values())]
        ema.updates = state['ema_updates']
        generator.set_state(state['generator_rng'])
        torch.set_rng_state(state['torch_rng'])
    except Exception:
        with torch.no_grad():
            for name, param in params.items():
                param.copy_(old_params[name])
        predictor.load_state_dict(old_pred, strict=True)
        optimizer.load_state_dict(old_opt)
        ema.shadow = old_ema
        ema.updates = old_updates
        generator.set_state(old_g)
        torch.set_rng_state(old_rng)
        raise
    return {'step': state['step'], 'history': state['history'], 'sha256': pointer['sha256'],
            'source_sha256': source_sha, 'authority': 'SHADOW_ONLY'}
