#!/usr/bin/env python3
"""Model-free extracted Phone source integrity preflight (not origin authentication).

Standard library only, run with Python -I -S before importing any V13 modules,
installing pip dependencies or starting bootstrap. The manifest itself is part
of the ZIP; a maliciously rebuilt ZIP can forge it. External signature / pinned
ZIP hash is required to establish publisher authenticity.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat

CHUNK = 1 << 20
REQUIRED = {'setup.sh', 'STARTEN.sh', 'scripts/verify_installed_source_run194.py',
            'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md'}
FORBIDDEN = ('.gguf', '.safetensors', '.sqlite', '.sqlite3', '.db', '.env', '.pem', '.key')


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_MANIFEST_KEY')
        result[key] = value
    return result


def safe_relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or '\x00' in value or value.startswith('/')
            or any(part in ('', '.', '..') for part in value.split('/'))
            or PurePosixPath(value).as_posix() != value):
        raise ValueError('UNSAFE_MANIFEST_PATH')
    return value


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def verify(root):
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('UNSAFE_SOURCE_ROOT')
    root = root.resolve()
    manifest_path = root / 'WORKSPACE_FILES.json'
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('SOURCE_MANIFEST_MISSING')
    original = manifest_path.read_bytes()
    try:
        doc = json.loads(original, object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError) as exc:
        raise ValueError('SOURCE_MANIFEST_INVALID') from exc
    if (not isinstance(doc, dict) or type(doc.get('schema_version')) is not int
            or doc['schema_version'] != 1 or not isinstance(doc.get('files'), dict)
            or not doc['files']):
        raise ValueError('SOURCE_MANIFEST_INVALID')
    files = doc['files']
    if not REQUIRED <= set(files):
        raise ValueError('REQUIRED_SOURCE_MISSING')
    for relative, expected in files.items():
        safe_relative(relative)
        if (relative == 'WORKSPACE_FILES.json' or relative.lower().endswith(FORBIDDEN)
                or not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected)):
            raise ValueError('INVALID_SOURCE_MANIFEST_ENTRY')
        path = root / relative
        current = root
        for part in PurePosixPath(relative).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('SOURCE_SYMLINK_FORBIDDEN')
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError('SOURCE_FILE_MISSING_OR_UNSAFE')
        if sha_file(path) != expected:
            raise ValueError('SOURCE_HASH_MISMATCH:' + relative)
    allowed = set(files) | {'WORKSPACE_FILES.json'}
    for path in root.rglob('*'):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError('SOURCE_SYMLINK_FORBIDDEN')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('SOURCE_SPECIAL_FILE_FORBIDDEN')
        if relative not in allowed:
            # Python may create caches on a later installer run. Never ignore
            # new .py, .pth, shell or native binaries in the source directory.
            if '__pycache__' in path.relative_to(root).parts and path.suffix == '.pyc':
                continue
            raise ValueError('UNREGISTERED_SOURCE_FILE:' + relative)
    if manifest_path.read_bytes() != original:
        raise ValueError('SOURCE_MANIFEST_CHANGED_DURING_CHECK')
    return {'status': 'EXTRACTED_SOURCE_INTEGRITY_PASS',
            'files': len(files), 'manifest_sha256': hashlib.sha256(original).hexdigest(),
            'authenticity_proven': False, 'native_models_run': False,
            'redmi_measured': False, 'canonical_gate_pass': False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, type=Path)
    args = ap.parse_args()
    try:
        result = verify(args.root)
    except ValueError as exc:
        raise SystemExit('V13_SOURCE_PREFLIGHT_FAIL:' + str(exc)) from exc
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
