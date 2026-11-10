"""Private, explicit, bounded checkpoint lifecycle for experimental Runtime World-JEPA.

No automatic deployment, model promotion, or source authority. Existing safe
NPZ loader validates arrays, source digest and checkpoint hash.
"""
import json
import os
from pathlib import Path
import re
import uuid

from . import world_jepa_shadow_checkpoint as checkpoint

HEX=re.compile(r'[0-9a-f]{64}$')
FILE=re.compile(r'jepa-[0-9a-f]{32}[.]npz$')
SCHEMA='v13.runtime_world_jepa.private.v1'


def _home(runtime):
    path=Path(runtime.home)/'world_jepa_online'
    if path.is_symlink():
        raise ValueError('Unsafe JEPA private directory')
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    if not path.is_dir() or path.is_symlink():
        raise ValueError('Invalid JEPA private directory')
    return path


def _manifest(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4096:
        raise ValueError('Missing or unsafe JEPA manifest')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate JEPA manifest key')
            result[k]=v
        return result
    obj=json.loads(path.read_text(),object_pairs_hook=pairs)
    if (type(obj) is not dict or set(obj)!={'schema','filename','source_sha256','sha256'}
            or obj['schema']!=SCHEMA or type(obj['filename']) is not str
            or not FILE.fullmatch(obj['filename'])
            or type(obj['source_sha256']) is not str or not HEX.fullmatch(obj['source_sha256'])
            or type(obj['sha256']) is not str or not HEX.fullmatch(obj['sha256'])):
        raise ValueError('Invalid JEPA manifest')
    return obj


def _write_manifest(home, name, manifest):
    tmp=home/('.manifest-'+uuid.uuid4().hex+'.tmp')
    try:
        with open(tmp,'x',encoding='utf-8') as f:
            os.chmod(tmp,0o600)
            json.dump(manifest,f,sort_keys=True)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,home/name)
        fd=os.open(home,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if tmp.exists():tmp.unlink()


def _restore(runtime, name):
    home=_home(runtime)
    meta=_manifest(home/name)
    model=checkpoint.load(home/meta['filename'],meta['source_sha256'],meta['sha256'])
    runtime._world_jepa_online=model
    runtime._world_jepa_source_sha=meta['source_sha256']
    return {'restored':True,'source_sha256':meta['source_sha256'],
            'active_model_promoted':False,'scope':'PRIVATE_EXPERIMENTAL_JEPA_ONLY'}


def rollback(runtime):
    """Explicitly load the last verified checkpoint; never promote active weights."""
    return _restore(runtime,'previous.json')


def save(runtime):
    model=getattr(runtime,'_world_jepa_online',None)
    source=getattr(runtime,'_world_jepa_source_sha',None)
    if model is None or type(source) is not str or not HEX.fullmatch(source):
        raise ValueError('No source-bound fitted JEPA model to checkpoint')
    home=_home(runtime)
    filename='jepa-'+uuid.uuid4().hex+'.npz'
    path=home/filename
    receipt=checkpoint.save(model,path,source)
    manifest={'schema':SCHEMA,'filename':filename,
              'source_sha256':source,'sha256':receipt['sha256']}
    # Validate the former active snapshot before offering it as rollback.
    # Never follow symlinks or trust filenames outside the private directory.
    previous=None
    active=home/'active.json'
    if active.exists() or active.is_symlink():
        old=_manifest(active)
        checkpoint.load(home/old['filename'],old['source_sha256'],old['sha256'])
        previous=old
    if previous is not None:
        _write_manifest(home,'previous.json',previous)
    _write_manifest(home,'active.json',manifest)
    # Only files referenced by the two manifests may survive. Ignore unknown
    # names rather than deleting user-owned material; reject links before unlink.
    retained={manifest['filename']}
    if previous is not None:
        retained.add(previous['filename'])
    for entry in home.iterdir():
        if FILE.fullmatch(entry.name) and entry.name not in retained:
            if entry.is_symlink() or not entry.is_file():
                raise ValueError('Unsafe stale JEPA checkpoint')
            entry.unlink()
    return {'sha256':receipt['sha256'],'source_sha256':source,
            'scope':'PRIVATE_EXPERIMENTAL_JEPA_ONLY','persisted':True,
            'active_model_promoted':False}


def restore(runtime):
    return _restore(runtime,'active.json')
