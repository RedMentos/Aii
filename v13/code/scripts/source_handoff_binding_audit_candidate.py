#!/usr/bin/env python3
"""Read-only, preregistered SourceHandoff source-tree verifier.

This is a standalone review candidate, not installed in the running ablation.
Checks all recorded source SHA256 bindings and the complete recursively frozen
runtime Python source inventory. It NEVER claims the model/binary binding is
verified: real installed weights and shared libraries require separate checks.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

HEX64 = re.compile('[0-9a-f]{64}\\Z')
SCOPE = 'ALL_RUNTIME_PYTHON_RECURSIVE_PLUS_HARNESS_AND_BASELINE'
BLOCK = 1024*1024


def _stable_sha256(path):
    before=path.stat()
    if not path.is_file() or path.is_symlink() or before.st_size > (32 << 20):
        raise ValueError('Bound source missing, linked or oversize')
    whole=hashlib.sha256()
    with path.open('rb') as f:
        while piece:=f.read(BLOCK):whole.update(piece)
    after=path.stat()
    attrs=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
    if attrs(before)!=attrs(after):
        raise ValueError('Bound source changed during verification')
    return whole.hexdigest()


def _safe_member(name,root):
    if not isinstance(name,str) or '\\' in name or not name or name.startswith('/'):
        raise ValueError('Noncanonical bound source path')
    pos=PurePosixPath(name)
    if any(part in ('','.', '..') for part in name.split('/')) or pos.as_posix()!=name:
        raise ValueError('Noncanonical bound source path')
    resolved=(root / name).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('Bound path escapes source root')
    if any(parent.is_symlink() for parent in (root / name).parents if parent!=root.parent):
        raise ValueError('Bound path traverses symbolic link')
    return root/name


def audit(registration_path,code_root):
    registration_path,code_root=Path(registration_path),Path(code_root)
    if registration_path.is_symlink() or not registration_path.is_file() or registration_path.stat().st_size>1<<20:
        raise ValueError('Missing or unsafe preregistration')
    if code_root.is_symlink() or not code_root.is_dir():
        raise ValueError('Source root is missing or linked')
    code_root=code_root.resolve()
    original=registration_path.read_bytes()
    doc=json.loads(original)
    if not isinstance(doc,dict) or doc.get('schema')!='SOURCE_HANDOFF_ABLATION_PREREGISTRATION_V1':
        raise ValueError('Invalid preregistration schema')
    binding=doc.get('binding')
    if not isinstance(binding,dict) or binding.get('source_scope')!=SCOPE:
        raise ValueError('Unrecognized complete source inventory scope')
    registered=binding.get('source_sha256')
    if not isinstance(registered,dict) or not registered:
        raise ValueError('Empty or malformed source binding')
    expected_runtime={p for p in registered if isinstance(p,str) and p.startswith('v13/') and p.endswith('.py')}
    if not expected_runtime:
        raise ValueError('Missing runtime Python inventory')
    actual_runtime=set()
    for path in (code_root/'v13').rglob('*.py'):
        if '__pycache__' in path.parts:continue
        if path.is_symlink():raise ValueError('Unregistered or linked Python source')
        actual_runtime.add(path.relative_to(code_root).as_posix())
    if actual_runtime!=expected_runtime:
        raise ValueError('Complete runtime Python inventory drift: missing/new sources')
    for name,digest in sorted(registered.items()):
        if not isinstance(digest,str) or not HEX64.fullmatch(digest):
            raise ValueError('Invalid source SHA256 binding')
        if _stable_sha256(_safe_member(name,code_root))!=digest:
            raise ValueError('Frozen source SHA256 drift: '+name)
    if registration_path.is_symlink() or hashlib.sha256(registration_path.read_bytes()).hexdigest()!=hashlib.sha256(original).hexdigest():
        raise ValueError('Preregistration changed during source inspection')
    return {'status':'SOURCE_BINDING_PASS_MODELS_UNVERIFIED',
            'preregistration_sha256':hashlib.sha256(original).hexdigest(),
            'verified_source_count':len(registered),
            'verified_runtime_source_count':len(expected_runtime),
            'native_model_and_library_bindings_verified':False,
            'native_models_launched':False,
            'canonical_gate_pass':False,'phone_measured':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preregistration',required=True,type=Path)
    parser.add_argument('--code-root',required=True,type=Path)
    args=parser.parse_args()
    try:receipt=audit(args.preregistration,args.code_root)
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({'status':'SOURCE_BINDING_REJECTED','error_type':type(exc).__name__}),file=sys.stderr)
        return 2
    print(json.dumps(receipt,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
