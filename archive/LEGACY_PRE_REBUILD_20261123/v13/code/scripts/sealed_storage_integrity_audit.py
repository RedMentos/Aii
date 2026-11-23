#!/usr/bin/env python3
"""Read-only, bounded-memory audit of v13-sealed-storage-parts-v1 evidence.

No model weights, runtime sources, manifests or binary parts are modified.
The report is diagnostic only, not a native model or quality gate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SCHEMA = 'v13-sealed-storage-parts-v1'
CHUNK_BYTES = 1 << 20
HEX = re.compile(r'[0-9a-f]{64}\Z')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit(manifest_path, *, reject_unlisted=False):
    manifest_path = Path(manifest_path)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('Manifest missing or symlinked')
    manifest_bytes = manifest_path.read_bytes()
    doc = json.loads(manifest_bytes)
    if (not isinstance(doc, dict) or doc.get('schema') != SCHEMA
        or type(doc.get('bytes')) is not int or doc['bytes'] < 0
        or doc.get('chunk_bytes') != CHUNK_BYTES
        or not isinstance(doc.get('sha256'), str) or not HEX.fullmatch(doc['sha256'])
        or not isinstance(doc.get('parts'), list)):
        raise ValueError('Invalid sealed evidence manifest')
    declared_bytes = doc['bytes']
    expected_parts = (declared_bytes + CHUNK_BYTES - 1) // CHUNK_BYTES
    if len(doc['parts']) != expected_parts:
        raise ValueError('Incorrect evidence part count')
    actual_total = 0
    full = hashlib.sha256()
    base = manifest_path.parent.resolve()
    for index, entry in enumerate(doc['parts']):
        tail = index == expected_parts-1
        expected_bytes = declared_bytes - index*CHUNK_BYTES if tail else CHUNK_BYTES
        if (not isinstance(entry, dict) or type(entry.get('index')) is not int
            or entry['index'] != index or entry.get('name') != f'part-{index:05d}.bin'
            or type(entry.get('bytes')) is not int or entry['bytes'] != expected_bytes
            or not isinstance(entry.get('sha256'), str) or not HEX.fullmatch(entry['sha256'])):
            raise ValueError(f'Invalid evidence descriptor {index}')
        path = base / entry['name']
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Evidence part {index} missing or symlinked')
        before = path.stat()
        with path.open('rb') as stream:
            block = stream.read(CHUNK_BYTES + 1)
        after = path.stat()
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError(f'Evidence part {index} changed during audit')
        if len(block) != expected_bytes or sha(block) != entry['sha256']:
            raise ValueError(f'Evidence part {index} bytes/hash mismatch')
        full.update(block)
        actual_total += len(block)
    if actual_total != declared_bytes or full.hexdigest() != doc['sha256']:
        raise ValueError('Whole evidence SHA256 mismatch')
    if reject_unlisted:
        expected = {entry['name'] for entry in doc['parts']}
        unlisted = sorted(p.name for p in base.glob('part-*.bin') if p.name not in expected)
        if unlisted:
            raise ValueError('Unlisted evidence parts present: ' + ','.join(unlisted[:5]))
    if manifest_path.is_symlink() or sha(manifest_path.read_bytes()) != sha(manifest_bytes):
        raise ValueError('Evidence manifest changed during audit')
    return {'schema':'V13_SEALED_EVIDENCE_READ_ONLY_AUDIT_V1',
            'status':'INTEGRITY_PASS_NOT_UTILITY_PASS',
            'source_schema': SCHEMA, 'manifest_sha256':sha(manifest_bytes),
            'expected_file_sha256':doc['sha256'],
            'verified_file_sha256':full.hexdigest(),
            'verified_bytes':actual_total,'verified_parts':len(doc['parts']),
            'strict_directory':reject_unlisted,
            'evidence_modified':False,'native_models_launched':False,
            'canonical_gate_pass':False,'phone_measured':False}


def publish_report(receipt, target):
    """Publish verified receipt without ever overwriting an existing one."""
    target = Path(target)
    if target.is_symlink() or target.is_dir():
        raise ValueError('Output must not be a symlink/directory')
    target.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(receipt, indent=2, sort_keys=True)+'\n').encode()
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError('Existing integrity receipt differs; refusing overwrite')
        return
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(tmp,target)
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != data:
                raise ValueError('Concurrent integrity receipt conflicts')
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--strict-directory',action='store_true')
    args=parser.parse_args()
    try:
        receipt=audit(args.manifest,reject_unlisted=args.strict_directory)
        if args.out:publish_report(receipt,args.out)
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as exc:
        print(json.dumps({'status':'INTEGRITY_FAIL','error_type':type(exc).__name__,
                          'error':str(exc)[:400],'canonical_gate_pass':False}),file=sys.stderr)
        return 1
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
