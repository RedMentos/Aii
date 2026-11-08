"""Immutable, crash-consistent JEPA inference+replay generations.

The journal is committed with matching model bytes, not independently.
This is NOT an optimizer checkpoint or active-model promotion.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from . import world_jepa_shadow_checkpoint as checkpoint
from .world_jepa_replay import ReplaySession

SCHEMA = 'v13.world_jepa.atomic_generation.v1'
MAX_JOURNAL_BYTES = 8 * 1024 * 1024


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(model, replay, destination):
    """Publish one immutable generation; never advance journal without model."""
    if not isinstance(replay, ReplaySession):
        raise ValueError('ReplaySession required')
    destination = Path(destination)
    parent = destination.parent
    if (not parent.is_dir() or parent.is_symlink() or destination.exists()
            or destination.is_symlink()):
        raise ValueError('fresh private generation destination required')
    stage = Path(tempfile.mkdtemp(prefix='.jepa-generation-', dir=parent))
    try:
        model_path = stage / 'model.npz'
        model_info = checkpoint.save(model, model_path, replay.source)
        model_sha = model_info['sha256']
        journal_raw = _canonical(replay.snapshot())
        if not 0 < len(journal_raw) <= MAX_JOURNAL_BYTES:
            raise ValueError('invalid journal size')
        manifest = {'schema': SCHEMA, 'source_sha256': replay.source,
                    'model_sha256': model_sha, 'journal_sha256': _sha(journal_raw),
                    'optimizer_state_persisted': False, 'active_model_promoted': False}
        for path, raw in ((stage / 'replay.json', journal_raw),
                          (stage / 'manifest.json', _canonical(manifest))):
            with path.open('xb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
        _sync_dir(stage)
        if destination.exists() or destination.is_symlink():
            raise ValueError('generation destination already exists')
        os.rename(stage, destination)
        _sync_dir(parent)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def load(destination, source_sha256):
    """Verify both payloads before restoring model and replay."""
    destination = Path(destination)
    names = ('model.npz', 'replay.json', 'manifest.json')
    if (destination.is_symlink() or not destination.is_dir()
            or any((destination / name).is_symlink() for name in names)
            or {p.name for p in destination.iterdir()} != set(names)):
        raise ValueError('unsafe or incomplete generation')
    manifest_raw = (destination / 'manifest.json').read_bytes()
    if len(manifest_raw) > 2048:
        raise ValueError('oversized manifest')
    manifest = json.loads(manifest_raw)
    if (type(manifest) is not dict or set(manifest) != {'schema', 'source_sha256',
            'model_sha256', 'journal_sha256', 'optimizer_state_persisted', 'active_model_promoted'}
            or manifest['schema'] != SCHEMA or manifest['source_sha256'] != source_sha256
            or manifest['optimizer_state_persisted'] is not False
            or manifest['active_model_promoted'] is not False
            or _canonical(manifest) != manifest_raw):
        raise ValueError('generation manifest mismatch')
    raw = (destination / 'replay.json').read_bytes()
    if not 0 < len(raw) <= MAX_JOURNAL_BYTES or _sha(raw) != manifest['journal_sha256']:
        raise ValueError('replay journal hash mismatch')
    snapshot = json.loads(raw)
    if _canonical(snapshot) != raw:
        raise ValueError('noncanonical replay journal')
    replay = ReplaySession.restore(snapshot, source_sha256)
    model = checkpoint.load(destination / 'model.npz', source_sha256, manifest['model_sha256'])
    return model, replay, manifest
