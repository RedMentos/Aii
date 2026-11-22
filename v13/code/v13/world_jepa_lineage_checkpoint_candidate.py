"""Bounded private JEPA generations with one atomic lineage-bound manifest.

Review-only: this module is used only in a hash-checked disposable Runtime copy.
It never deletes old or unknown files; the directory can fill and then stops.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

from . import online_world_policy as policy
from . import world_jepa_runtime_guard_candidate as guard
from . import world_jepa_shadow_checkpoint as checkpoint
from . import world_model
from .online_world import OnlineWorld
from .store import Store

SCHEMA = 'v13.jepa.lineage-generations.v1'
RECEIPT_SCHEMA = 'v13.jepa.lineage-receipt.v1'
QUOTA = 128 * 1024 * 1024
MAX_RECEIPT = 1024 * 1024
MAX_MANIFEST = 16 * 1024
MAX_FILES = 128
NAME = re.compile(r'[0-9a-f]{32}\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')
CHUNK = 64 * 1024


def _strict(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate checkpoint metadata key')
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid checkpoint metadata') from exc


def _bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _read_at(dir_fd, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('unsafe or oversized checkpoint metadata')
        parts = []
        count = 0
        while True:
            data = os.read(fd, min(CHUNK, limit - count + 1))
            if not data:
                break
            count += len(data)
            if count > limit:
                raise ValueError('checkpoint metadata exceeds limit')
            parts.append(data)
        if count != info.st_size:
            raise ValueError('checkpoint metadata changed while reading')
        return b''.join(parts)
    finally:
        os.close(fd)


def _entry(value):
    if (type(value) is not dict or set(value) != {'id', 'model_sha256', 'lineage_sha256', 'source_sha256'}
            or type(value['id']) is not str or not NAME.fullmatch(value['id'])
            or any(type(value[k]) is not str or not HEX.fullmatch(value[k])
                   for k in ('model_sha256', 'lineage_sha256', 'source_sha256'))):
        raise ValueError('invalid JEPA generation entry')
    return value


def _manifest(dir_fd, missing_ok=False):
    try:
        raw = _read_at(dir_fd, 'manifest.json', MAX_MANIFEST)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise ValueError('missing lineage-bound JEPA manifest')
    obj = _strict(raw)
    if type(obj) is not dict or set(obj) != {'schema', 'active', 'previous'} or obj['schema'] != SCHEMA:
        raise ValueError('invalid JEPA generation manifest')
    _entry(obj['active'])
    if obj['previous'] is not None:
        _entry(obj['previous'])
        if obj['previous']['id'] == obj['active']['id']:
            raise ValueError('duplicate JEPA generations')
    return obj


def _receipts(value):
    if (type(value) is not dict or not value or len(value) > world_model.MAX_ROWS
            or any(type(k) is not str or not 1 <= len(k) <= 160
                   or type(v) is not str or not HEX.fullmatch(v) for k, v in value.items())):
        raise ValueError('invalid JEPA lineage receipts')
    return dict(value)


def _lineage(dir_fd, entry):
    raw = _read_at(dir_fd, 'lineage-' + entry['id'] + '.json', MAX_RECEIPT)
    if hashlib.sha256(raw).hexdigest() != entry['lineage_sha256']:
        raise ValueError('JEPA lineage receipt changed')
    obj = _strict(raw)
    if (type(obj) is not dict or set(obj) != {'schema', 'model_sha256', 'source_sha256', 'receipts'}
            or obj['schema'] != RECEIPT_SCHEMA or obj['model_sha256'] != entry['model_sha256']
            or obj['source_sha256'] != entry['source_sha256']):
        raise ValueError('JEPA lineage receipt does not match model')
    return _receipts(obj['receipts'])


def _live_receipts(runtime, receipts):
    rows = world_model.transitions(runtime.store, limit=world_model.MAX_ROWS)
    mapping = {row.get('action_id'): row for row in rows}
    if len(mapping) != len(rows):
        raise ValueError('duplicate JEPA transition')
    verifier = object.__new__(OnlineWorld)
    verifier.runtime = runtime
    for action_id, expected in receipts.items():
        row = mapping.get(action_id)
        if row is None or guard._digest(row) != expected or not verifier._source_current(row):
            raise ValueError('JEPA checkpoint source no longer verifiable')


def _authorize(runtime, authority):
    guard._check_sources()
    if type(runtime.store) is not Store:
        raise ValueError('reviewed Store instance required')
    if authority != policy.HUMAN:
        raise PermissionError('explicit operator authority required')
    reason = policy.blocked(runtime, authority)
    if reason:
        raise ValueError('JEPA checkpoint unavailable: ' + reason)
    runtime.require_idle()


def _open_home(runtime, create=False):
    if not all(hasattr(os, x) for x in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise OSError('safe checkpoint directory unsupported')
    home = Path(runtime.home) / 'world_jepa_lineage'
    if create:
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
    return home, os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def _usage(dir_fd):
    count = total = 0
    with os.scandir(dir_fd) as items:
        for item in items:
            count += 1
            if count > MAX_FILES:
                raise ValueError('JEPA checkpoint directory has too many entries')
            info = item.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('unsafe JEPA checkpoint directory entry')
            total += info.st_size
    return count, total


def _write_exclusive(dir_fd, name, data):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError('short checkpoint metadata write')
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish_manifest(dir_fd, manifest):
    raw = _bytes(manifest)
    if len(raw) > MAX_MANIFEST:
        raise ValueError('JEPA generation manifest too large')
    temp = '.manifest-' + uuid.uuid4().hex + '.tmp'
    _write_exclusive(dir_fd, temp, raw)
    # A failed or interrupted publish keeps all generation files, even if the
    # atomic rename succeeded but the following fsync did not.
    os.replace(temp, 'manifest.json', src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    os.fsync(dir_fd)


def save(runtime, authority='SYSTEM'):
    _authorize(runtime, authority)
    with runtime.lock:
        _authorize(runtime, authority)
        if getattr(runtime, '_world_jepa_quarantined', False) is not False:
            raise ValueError('World-JEPA model quarantined')
        model = getattr(runtime, '_world_jepa_online', None)
        receipts = _receipts(getattr(runtime, '_world_jepa_lineage', None))
        source = getattr(runtime, '_world_jepa_source_sha', None)
        if model is None or type(source) is not str or not HEX.fullmatch(source):
            raise ValueError('no source-bound JEPA model')
        with runtime.store.tx():
            _live_receipts(runtime, receipts)
            home, dir_fd = _open_home(runtime, create=True)
            try:
                count, used = _usage(dir_fd)
                # Reserve the largest possible checkpoint, receipt, and manifest.
                if count + 4 > MAX_FILES or used + checkpoint.MAX_BYTES + MAX_RECEIPT + MAX_MANIFEST > QUOTA:
                    raise ValueError('JEPA checkpoint storage quota reached; existing files preserved')
                old = _manifest(dir_fd, missing_ok=True)
                if old:
                    for entry in (old['active'], old['previous']):
                        if entry is not None:
                            _lineage(dir_fd, entry)
                            checkpoint.load(home / ('jepa-' + entry['id'] + '.npz'),
                                            entry['source_sha256'], entry['model_sha256'])
                generation = uuid.uuid4().hex
                model_path = home / ('jepa-' + generation + '.npz')
                saved = checkpoint.save(model, model_path, source)
                receipt = {'schema': RECEIPT_SCHEMA, 'model_sha256': saved['sha256'],
                           'source_sha256': source, 'receipts': receipts}
                receipt_bytes = _bytes(receipt)
                if len(receipt_bytes) > MAX_RECEIPT:
                    raise ValueError('JEPA lineage receipt too large')
                _write_exclusive(dir_fd, 'lineage-' + generation + '.json', receipt_bytes)
                os.fsync(dir_fd)
                entry = {'id': generation, 'model_sha256': saved['sha256'],
                         'lineage_sha256': hashlib.sha256(receipt_bytes).hexdigest(), 'source_sha256': source}
                manifest = {'schema': SCHEMA, 'active': entry, 'previous': old['active'] if old else None}
                _publish_manifest(dir_fd, manifest)
                return {'persisted': True, 'sha256': saved['sha256'],
                        'source_sha256': source, 'active_model_promoted': False,
                        'scope': 'PRIVATE_LINEAGE_BOUND_EXPERIMENTAL_JEPA',
                        'optimizer_state_persisted': False}
            finally:
                os.close(dir_fd)


def restore(runtime, authority='SYSTEM', previous=False):
    _authorize(runtime, authority)
    if type(previous) is not bool:
        raise ValueError('invalid JEPA generation selector')
    with runtime.lock:
        _authorize(runtime, authority)
        old = {name: getattr(runtime, name, None) for name in
               ('_world_jepa_online', '_world_jepa_source_sha', '_world_jepa_lineage', '_world_jepa_quarantined')}
        try:
            with runtime.store.tx():
                try:
                    home, dir_fd = _open_home(runtime)
                except FileNotFoundError as exc:
                    raise ValueError('missing lineage-bound JEPA manifest') from exc
                try:
                    manifest = _manifest(dir_fd)
                    entry = manifest['previous' if previous else 'active']
                    if entry is None:
                        raise ValueError('no previous JEPA generation')
                    receipts = _lineage(dir_fd, entry)
                    _live_receipts(runtime, receipts)
                    model = checkpoint.load(home / ('jepa-' + entry['id'] + '.npz'),
                                            entry['source_sha256'], entry['model_sha256'])
                    runtime._world_jepa_online = model
                    runtime._world_jepa_source_sha = entry['source_sha256']
                    runtime._world_jepa_lineage = receipts
                    runtime._world_jepa_quarantined = False
                finally:
                    os.close(dir_fd)
        except BaseException:
            for name, value in old.items():
                if value is None:
                    if hasattr(runtime, name): delattr(runtime, name)
                else:
                    setattr(runtime, name, value)
            raise
        return {'restored': True, 'source_sha256': entry['source_sha256'],
                'active_model_promoted': False, 'scope': 'PRIVATE_LINEAGE_BOUND_EXPERIMENTAL_JEPA',
                'optimizer_state_persisted': False,
                'selection': 'previous' if previous else 'active', 'manifest_changed': False}
