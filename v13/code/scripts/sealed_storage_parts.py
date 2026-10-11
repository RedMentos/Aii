#!/usr/bin/env python3
"""Lossless, hash-verified storage of closed evidence in small Git objects.

This changes storage only. Never invoke it on an open collector artifact.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

SCHEMA = 'v13-sealed-storage-parts-v1'
CHUNK_BYTES = 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def split(source, directory):
    source, directory = Path(source), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # Freeze once; a caller must already have closed and sealed the original.
    data = source.read_bytes()
    manifest = {'schema': SCHEMA, 'file_name': source.name, 'bytes': len(data),
                'sha256': sha(data), 'chunk_bytes': CHUNK_BYTES, 'parts': []}
    for i, start in enumerate(range(0, len(data), CHUNK_BYTES)):
        block = data[start:start + CHUNK_BYTES]
        name = f'part-{i:05d}.bin'
        path = directory / name
        if path.exists():
            if path.read_bytes() != block:
                raise ValueError('Refusing to overwrite different evidence part')
        else:
            with path.open('xb') as out:
                out.write(block)
                out.flush()
                os.fsync(out.fileno())
        manifest['parts'].append({'index': i, 'name': name, 'bytes': len(block),
                                  'sha256': sha(block)})
    contents = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    path = directory / 'manifest.json'
    if path.exists() and path.read_bytes() != contents:
        raise ValueError('Refusing to overwrite different evidence manifest')
    if not path.exists():
        with path.open('xb') as out:
            out.write(contents)
            out.flush()
            os.fsync(out.fileno())
    return manifest


def restore(manifest_path, destination):
    manifest_path, destination = Path(manifest_path), Path(destination)
    doc = json.loads(manifest_path.read_text())
    if (doc.get('schema') != SCHEMA or type(doc.get('bytes')) is not int
            or doc['bytes'] < 0 or doc.get('chunk_bytes') != CHUNK_BYTES
            or not isinstance(doc.get('parts'), list)
            or not re.fullmatch('[0-9a-f]{64}', doc.get('sha256', ''))):
        raise ValueError('Invalid storage manifest')
    total = 0
    parts = []
    base = manifest_path.parent.resolve()
    for i, item in enumerate(doc['parts']):
        if (item.get('index') != i or item.get('name') != f'part-{i:05d}.bin'
                or type(item.get('bytes')) is not int
                or not 0 < item['bytes'] <= CHUNK_BYTES
                or (i < len(doc['parts']) - 1 and item['bytes'] != CHUNK_BYTES)
                or not re.fullmatch('[0-9a-f]{64}', item.get('sha256', ''))):
            raise ValueError('Invalid part order, size or identity')
        path = base / item['name']
        if path.is_symlink() or path.resolve().parent != base:
            raise ValueError('Evidence part escapes its directory')
        parts.append((path, item))
        total += item['bytes']
    if total != doc['bytes']:
        raise ValueError('Manifest total differs from declared file size')
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        whole = hashlib.sha256()
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as out:
            tmp = Path(out.name)
            for path, item in parts:
                block = path.read_bytes()
                if len(block) != item['bytes'] or sha(block) != item['sha256']:
                    raise ValueError('Evidence part bytes differ from binding')
                out.write(block)
                whole.update(block)
            out.flush()
            os.fsync(out.fileno())
        if whole.hexdigest() != doc['sha256']:
            raise ValueError('Restored file differs from original hash')
        if destination.exists():
            if sha(destination.read_bytes()) != doc['sha256']:
                raise ValueError('Refusing to replace different destination')
            tmp.unlink()
        else:
            # Link installs without replacing a concurrently created artifact.
            os.link(tmp, destination)
            tmp.unlink()
        tmp = None
        return doc
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('split'); p.add_argument('--source', required=True); p.add_argument('--parts-dir', required=True)
    p = sub.add_parser('restore'); p.add_argument('--manifest', required=True); p.add_argument('--out', required=True)
    args = parser.parse_args()
    doc = split(args.source, args.parts_dir) if args.command == 'split' else restore(args.manifest, args.out)
    print(json.dumps({'command': args.command, 'bytes': doc['bytes'], 'sha256': doc['sha256'], 'parts': len(doc['parts'])}))


if __name__ == '__main__':
    main()
