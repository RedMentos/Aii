"""Review-only preflight and exception-atomic C3 LoRA checkpoint restore.

The enclosing builder substitutes the call only in an exact-source disposable
Runtime copy. This does not grant learning authority or activate an adapter.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re

SHA = re.compile(r'[0-9a-f]{64}\Z')


def binding(master_sha, base_generation, items, anchors, probes, cfg):
    """Hash the exact training inputs; None means the checkpoint cannot resume."""
    if (type(master_sha) is not str or not SHA.fullmatch(master_sha)
            or type(base_generation) is not str or not base_generation):
        return None
    try:
        raw = json.dumps({'schema': 'v13.c3.lora.resume.v1', 'master_sha256': master_sha,
                          'base_generation': base_generation, 'items': items, 'anchors': anchors,
                          'probes': probes, 'config': cfg}, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError, UnicodeError) as exc:
        raise ValueError('C3 resume inputs cannot be bound') from exc
    return hashlib.sha256(raw).hexdigest()


def optimizer_layout(model, optimizer):
    names = {id(param): name for name, param in model.named_parameters() if param.requires_grad}
    if not names:
        raise ValueError('no trainable C3 parameters')
    seen = set()
    result = []
    for group in optimizer.param_groups:
        members = []
        for param in group['params']:
            name = names.get(id(param))
            if name is None or name in seen:
                raise ValueError('unbound or duplicate C3 optimizer parameter')
            seen.add(name)
            members.append(name)
        result.append(members)
    if seen != set(names.values()):
        raise ValueError('C3 optimizer omits trainable parameters')
    return result


def _validate_optimizer(torch, model, optimizer, incoming, layout, completed_step):
    current = optimizer.state_dict()
    if (type(incoming) is not dict or set(incoming) != {'state', 'param_groups'}
            or type(incoming['state']) is not dict or type(incoming['param_groups']) is not list
            or len(incoming['param_groups']) != len(current['param_groups'])
            or layout != optimizer_layout(model, optimizer)):
        raise ValueError('invalid C3 optimizer checkpoint structure')
    params = {name: param for name, param in model.named_parameters() if param.requires_grad}
    known = set()
    for saved, expected, names in zip(incoming['param_groups'], current['param_groups'], layout):
        if (type(saved) is not dict or set(saved) != set(expected)
                or type(saved.get('params')) is not list or len(saved['params']) != len(names)
                or any(saved[k] != expected[k] for k in expected if k != 'params')):
            raise ValueError('C3 optimizer groups or configuration differ')
        for pid, name in zip(saved['params'], names):
            if type(pid) is not int or pid in known:
                raise ValueError('invalid or duplicate C3 optimizer parameter id')
            known.add(pid)
            if pid not in incoming['state']:
                continue  # Parameters without a gradient may have no Adam slot.
            slot = incoming['state'][pid]
            expected_keys = {'step', 'exp_avg', 'exp_avg_sq'}
            if saved.get('amsgrad'):
                expected_keys.add('max_exp_avg_sq')
            if type(slot) is not dict or set(slot) != expected_keys:
                raise ValueError('incomplete C3 AdamW state')
            step = slot['step']
            if torch.is_tensor(step):
                if step.numel() != 1 or not bool(torch.isfinite(step).all()):
                    raise ValueError('invalid C3 optimizer step')
                step = float(step)
            if (type(step) not in (int, float) or not math.isfinite(step)
                    or not float(step).is_integer() or not 1 <= step <= completed_step):
                raise ValueError('invalid C3 optimizer step')
            for key in expected_keys - {'step'}:
                value = slot[key]
                if (not torch.is_tensor(value) or value.layout != torch.strided
                        or value.shape != params[name].shape or value.dtype != params[name].dtype
                        or not bool(torch.isfinite(value).all())):
                    raise ValueError('invalid C3 optimizer moment')
                if key in ('exp_avg_sq', 'max_exp_avg_sq') and bool((value < 0).any()):
                    raise ValueError('negative C3 optimizer second moment')
    if set(incoming['state']) - known:
        raise ValueError('orphaned C3 optimizer state')
    if completed_step > 0 and not incoming['state']:
        raise ValueError('C3 optimizer state missing after training')


def restore(torch, model, optimizer, state, dataset_hash, max_steps, source_binding,
            seed, data_size, anchor_size, anchor_weight):
    """Validate source, tensors, RNG and AdamW state before any live mutation."""
    from .lora_trainer import _valid_lora_resume, _valid_lora_tensors, _resume_shuffle_rng
    if getattr(optimizer, '_v13_c3_resume_unusable', False):
        raise RuntimeError('discard C3 optimizer after failed recovery')
    if (source_binding is None or type(state) is not dict
            or state.get('resume_source_sha256') != source_binding
            or not _valid_lora_resume(state, dataset_hash, max_steps)
            or not _valid_lora_tensors(torch, state.get('lora'), model.state_dict())):
        raise ValueError('unbound or invalid C3 resume checkpoint')
    if any(param.device.type != 'cpu' for param in model.parameters()):
        raise ValueError('C3 resume candidate only verifies CPU RNG')
    for entry in state['hist']:
        value = entry.get('jepa')
        if value is not None and (type(value) not in (float, int) or not math.isfinite(value)):
            raise ValueError('invalid C3 history')
    if not torch.is_tensor(state.get('shuffle_rng_state')):
        raise ValueError('missing C3 shuffle RNG')
    generator = _resume_shuffle_rng(torch, seed, state['step'], state['shuffle_rng_state'],
                                    data_size, anchor_size, anchor_weight)
    torch_rng = state.get('torch_rng_state')
    if not torch.is_tensor(torch_rng):
        raise ValueError('missing C3 Torch RNG')
    # Validate on an independent CPU generator before touching process state.
    torch.Generator(device='cpu').set_state(torch_rng)
    _validate_optimizer(torch, model, optimizer, state.get('opt'), state.get('optimizer_layout'), state['step'])
    current = model.state_dict()
    old_weights = {key: current[key].detach().clone() for key in state['lora']}
    old_optimizer = copy.deepcopy(optimizer.state_dict())
    old_torch_rng = torch.get_rng_state().clone()
    try:
        model.load_state_dict(state['lora'], strict=False)
        optimizer.load_state_dict(state['opt'])
        torch.set_rng_state(torch_rng)
    except BaseException as exc:
        try:
            model.load_state_dict(old_weights, strict=False)
            optimizer.load_state_dict(old_optimizer)
            torch.set_rng_state(old_torch_rng)
        except BaseException as recovery:
            optimizer._v13_c3_resume_unusable = True
            raise RuntimeError('C3 resume recovery failed; discard model and optimizer') from recovery
        raise exc
    return generator
