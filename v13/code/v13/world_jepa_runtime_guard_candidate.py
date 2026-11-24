"""Review-only World-JEPA authority and current-source guard for a test copy.

It trains an independent in-memory proposal under the Store lock; frozen
Runtime does not import this candidate. Durable lineage is not implemented.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np

from . import online_world_policy as policy
from . import world_jepa as wj
from . import world_jepa_online_experiment as experiment
from . import world_jepa_shadow_checkpoint as checkpoint
from . import world_model
from .online_world import OnlineWorld
from .store import Store

PINS = {
    'world_jepa.py': '14ee7982ab3866a13b2cca83086123281cf112a3c133b91c06df9df3669715fd',
    'world_jepa_shadow_checkpoint.py': 'f88ad5eea241aacd55e5c3d0f53eb0b132a164a2d49cc0185726f1a0a8a076ae',
    'world_jepa_online_experiment.py': 'c05b38d5722fe26c91797448d9e67d3901f2a9efcb98302f90de235c9ac3948b',
    'world_jepa_action_outcome_adapter.py': '202488c7d06707cd92c2d5e46f611f685dbbb08f3ab795d98c7476c66aaeafcd',
    'world_model.py': 'cb58f26778501c02b986b08d4e356591776d998fa7e5bc14f81bb5b33a29322b',
    'online_world.py': '027f51b9c0fff5e69369adff7faf48343dd7da606154c69c7d5c967f9cf7356d',
    'online_world_policy.py': 'd75e5ec91ac40bd6898d2cf01e2261795455090b9c98a948fa56b20098031e53',
    'store.py': 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
}
REQUIRED = frozenset({'seed', 'ensemble', '_fit_steps', '_action_counts', 'mu', 'sd',
                      'history', 'enc', 'tgt', 'preds', 'zsd', '_ztrain', '_nn_med'})
VALIDATION_TAG = '0' * 64


def _check_sources():
    directory = Path(__file__).resolve().parent
    for name, expected in PINS.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError('World-JEPA guard source changed: ' + name)


def _digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def _clone(model):
    """Copy only validated numeric WorldJEPA fields, never arbitrary deepcopy hooks."""
    if type(model) is not wj.WorldJEPA or set(model.__dict__) != REQUIRED:
        raise ValueError('unsupported or unbound World-JEPA model')
    if (type(model.seed) is not int or type(model.ensemble) is not int
            or type(model._fit_steps) is not int or type(model._nn_med) is not float
            or type(model.history) is not list or len(model.history) > 100000
            or type(model.enc) is not dict or type(model.tgt) is not dict
            or type(model.preds) is not list or len(model.preds) != model.ensemble):
        raise ValueError('unsupported World-JEPA state')
    if any(type(row) is not dict or any(type(k) is not str or type(v) not in (int, float)
                                         or not np.isfinite(v) for k, v in row.items())
           for row in model.history):
        raise ValueError('unsupported World-JEPA history')
    if any(type(getattr(model, name)) is not np.ndarray for name in
           ('mu', 'sd', 'zsd', '_ztrain', '_action_counts')):
        raise ValueError('unsupported World-JEPA array')
    for group, keys in ((model.enc, checkpoint.ENC_KEYS), (model.tgt, checkpoint.ENC_KEYS),
                        *((pred, checkpoint.PRED_KEYS) for pred in model.preds)):
        if (type(group) is not dict or set(group) != set(keys)
                or any(type(group[k]) is not np.ndarray for k in keys)):
            raise ValueError('unsupported World-JEPA parameter containers')
    meta, arrays = checkpoint._extract(model, VALIDATION_TAG)
    checkpoint._validate(meta, arrays, VALIDATION_TAG)
    def copied(name):
        return np.array(arrays[name], copy=True, order='C', subok=False)
    staged = wj.WorldJEPA(seed=meta['seed'], ensemble=meta['ensemble'])
    staged.__dict__.update(
        _fit_steps=meta['fit_steps'], _action_counts=copied('action_counts'),
        mu=copied('mu'), sd=copied('sd'), zsd=copied('zsd'),
        _ztrain=copied('ztrain'), _nn_med=float(arrays['nn_med'][0]), history=[],
        enc={k: copied('enc__' + k) for k in checkpoint.ENC_KEYS},
        tgt={k: copied('tgt__' + k) for k in checkpoint.ENC_KEYS},
        preds=[{k: copied(f'pred{i}__{k}') for k in checkpoint.PRED_KEYS}
               for i in range(meta['ensemble'])])
    clone_meta, clone_arrays = checkpoint._extract(staged, VALIDATION_TAG)
    checkpoint._validate(clone_meta, clone_arrays, VALIDATION_TAG)
    if any(np.shares_memory(arrays[k], clone_arrays[k]) for k in arrays):
        raise ValueError('World-JEPA proposal is not detached')
    return staged


def update(runtime, steps=10, limit=2048, authority='SYSTEM'):
    """Explicit bounded update; check current and previous in-memory source rows.

    The full fit holds the Store write transaction. This is a correctness test
    seam, not a latency- or device-ready background scheduler.
    """
    _check_sources()
    if authority != policy.HUMAN:
        return {'status': 'SKIPPED_EXPLICIT_HUMAN_REQUIRED', 'trained': False}
    reason = policy.blocked(runtime, authority)
    if reason:
        return {'status': 'SKIPPED_' + reason, 'trained': False}
    if type(steps) is not int or not 1 <= steps <= 50:
        raise ValueError('invalid JEPA step budget')
    if type(limit) is not int or not 16 <= limit <= world_model.MAX_ROWS:
        raise ValueError('invalid JEPA transition limit')
    if type(runtime.store) is not Store:
        raise ValueError('reviewed Store instance required')
    runtime.require_idle()
    with runtime.lock:
        reason = policy.blocked(runtime, authority)
        if reason:
            return {'status': 'SKIPPED_' + reason, 'trained': False}
        current = getattr(runtime, '_world_jepa_online', None)
        prior = getattr(runtime, '_world_jepa_lineage', None)
        if getattr(runtime, '_world_jepa_quarantined', False) is not False:
            raise ValueError('World-JEPA model quarantined; source review required')
        if current is None:
            if prior not in (None, {}):
                raise ValueError('orphaned JEPA lineage')
            prior = {}
        elif type(prior) is not dict or not prior:
            raise ValueError('unbound legacy JEPA model; review required')
        if len(prior) > world_model.MAX_ROWS or any(
                type(k) is not str or not k or type(v) is not str or not re.fullmatch(r'[0-9a-f]{64}', v)
                for k, v in prior.items()):
            raise ValueError('invalid JEPA in-memory lineage')
        # A failed DB commit must not publish a staged model in memory.
        old_model = current
        old_source = getattr(runtime, '_world_jepa_source_sha', None)
        old_lineage = getattr(runtime, '_world_jepa_lineage', None)
        try:
            with runtime.store.tx():
                rows = world_model.transitions(runtime.store, limit=limit)
                available = world_model.transitions(runtime.store, limit=world_model.MAX_ROWS) if prior else rows
                by_id = {row.get('action_id'): row for row in available}
                if len(by_id) != len(available):
                    raise ValueError('duplicate current world transition')
                verifier = object.__new__(OnlineWorld)
                verifier.runtime = runtime
                for action_id, expected in prior.items():
                    row = by_id.get(action_id)
                    if row is None or _digest(row) != expected or not verifier._source_current(row):
                        runtime._world_jepa_quarantined = True
                        raise ValueError('previous JEPA source no longer verifiable')
                lineage = dict(prior)
                for row in rows:
                    action_id = row.get('action_id')
                    if type(action_id) is not str or not action_id or not verifier._source_current(row):
                        raise ValueError('current JEPA source no longer verifiable')
                    digest = _digest(row)
                    if action_id in lineage and lineage[action_id] != digest:
                        raise ValueError('JEPA source content changed')
                    lineage[action_id] = digest
                if len(lineage) > world_model.MAX_ROWS:
                    raise ValueError('JEPA lineage capacity exhausted')
                candidate = _clone(current) if current is not None else wj.WorldJEPA(seed=7, ensemble=2)
                result = experiment.update(candidate, rows, steps=steps)
                source = result.get('source_sha256')
                loss = result.get('holdout_loss_after')
                if (type(source) is not str or not re.fullmatch(r'[0-9a-f]{64}', source)
                        or type(loss) not in (int, float) or not np.isfinite(loss) or loss < 0):
                    raise ValueError('invalid JEPA training receipt')
                runtime._world_jepa_online = candidate
                runtime._world_jepa_source_sha = source
                runtime._world_jepa_lineage = lineage
        except BaseException:
            for name, value in (('_world_jepa_online', old_model), ('_world_jepa_source_sha', old_source),
                                ('_world_jepa_lineage', old_lineage)):
                if value is None:
                    if hasattr(runtime, name): delattr(runtime, name)
                else:
                    setattr(runtime, name, value)
            raise
        return dict(result, source_verified=True, trained=True, active_model_promoted=False,
                    persisted=False, status='EXPERIMENTAL_JEPA_CURRENT_SOURCES_ONLY',
                    lineage_scope='IN_MEMORY_BOUNDED_NOT_DURABLE')


def checkpoint_blocked(runtime, authority='SYSTEM'):
    """Do not claim safe resume for legacy checkpoints lacking complete lineage."""
    _check_sources()
    if authority != policy.HUMAN:
        raise PermissionError('explicit operator authority required')
    raise ValueError('JEPA checkpoint lineage not yet bound; save/restore disabled for review')
