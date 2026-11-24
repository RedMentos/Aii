#!/usr/bin/env python3
"""Lossless, hash-verified storage of closed evidence in small Git objects.

This changes storage only. Never invoke it on an open collector artifact.
Integrated 2026-10-12 from the reviewed streaming candidate
(`sealed_storage_streaming_candidate.py`): 1 MiB streaming, immutable
no-replace publication, symlink/mutation rejection. Same v1 wire format;
both published part sets restore byte-identically with old and new code.
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
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def _sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(CHUNK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def _real_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Evidence directory must be an actual directory')
    return path.resolve()


def _immutable_create(path, content):
    """Install without replacing another writer, validate an existing copy."""
    if path.is_symlink():
        raise ValueError('Evidence path must not be a symlink')
    if path.exists():
        if not path.is_file() or path.stat().st_size != len(content) or _sha_file(path) != hashlib.sha256(content).hexdigest():
            raise ValueError('Refusing to overwrite different evidence bytes')
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != len(content) or _sha_file(path) != hashlib.sha256(content).hexdigest():
                raise ValueError('Evidence path concurrently changed')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def split(source, directory):
    """One MiB maximum read at once, with full source-stability binding."""
    source = Path(source)
    if source.is_symlink() or not source.is_file():
        raise ValueError('Source must be an existing regular file')
    directory = _real_directory(directory)
    before = source.stat()
    fingerprint = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    total = 0
    whole = hashlib.sha256()
    parts = []
    with source.open('rb') as stream:
        i = 0
        while block := stream.read(CHUNK_BYTES):
            whole.update(block)
            total += len(block)
            name = f'part-{i:05d}.bin'
            _immutable_create(directory / name, block)
            parts.append({'index': i, 'name': name, 'bytes': len(block),
                          'sha256': hashlib.sha256(block).hexdigest()})
            i += 1
    if fingerprint(before) != fingerprint(source.stat()) or before.st_size != total:
        raise ValueError('Source changed during split: manifest not published')
    manifest = {'schema': SCHEMA, 'file_name': source.name, 'bytes': total,
                'sha256': whole.hexdigest(), 'chunk_bytes': CHUNK_BYTES,
                'parts': parts}
    data = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    _immutable_create(directory / 'manifest.json', data)
    return manifest


def restore(manifest_path, destination):
    """Verify all parts and full SHA256 before publishing, without replacement."""
    manifest_path, destination = Path(manifest_path), Path(destination)
    if manifest_path.is_symlink():
        raise ValueError('Manifest path must not be a symlink')
    doc = json.loads(manifest_path.read_text())
    if (doc.get('schema') != SCHEMA or type(doc.get('bytes')) is not int
        or doc['bytes'] < 0 or doc.get('chunk_bytes') != CHUNK_BYTES
        or not isinstance(doc.get('parts'), list)
        or not isinstance(doc.get('sha256'), str) or not HEX64.fullmatch(doc['sha256'])):
        raise ValueError('Invalid storage manifest')
    part_items = doc['parts']
    if len(part_items) != (doc['bytes'] + CHUNK_BYTES - 1) // CHUNK_BYTES:
        raise ValueError('Incorrect part count')
    expected_bytes = 0
    for index, item in enumerate(part_items):
        last = index == len(part_items) - 1
        expected_size = doc['bytes'] - index * CHUNK_BYTES if last else CHUNK_BYTES
        if (not isinstance(item, dict) or type(item.get('index')) is not int or item['index'] != index
            or item.get('name') != f'part-{index:05d}.bin'
            or type(item.get('bytes')) is not int or item['bytes'] != expected_size
            or not isinstance(item.get('sha256'), str) or not HEX64.fullmatch(item['sha256'])):
            raise ValueError('Invalid evidence part descriptor')
        expected_bytes += expected_size
    if expected_bytes != doc['bytes']:
        raise ValueError('Manifest part total mismatch')
    base = manifest_path.parent.resolve()
    if destination.is_symlink():
        raise ValueError('Destination must not be a symlink')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        whole = hashlib.sha256()
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as out:
            temporary = Path(out.name)
            for item in part_items:
                path = base / item['name']
                if path.is_symlink() or not path.is_file():
                    raise ValueError('Missing or linked evidence part')
                # Exactly one read of each bounded-size part; reject mid-read expansion.
                with path.open('rb') as part:
                    block = part.read(CHUNK_BYTES + 1)
                if len(block) != item['bytes'] or hashlib.sha256(block).hexdigest() != item['sha256']:
                    raise ValueError('Evidence part bytes differ from manifest')
                out.write(block)
                whole.update(block)
            out.flush()
            os.fsync(out.fileno())
        if whole.hexdigest() != doc['sha256']:
            raise ValueError('Restored file differs from original hash')
        if destination.exists():
            if not destination.is_file() or _sha_file(destination) != doc['sha256']:
                raise ValueError('Refusing to overwrite different destination')
        else:
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if destination.is_symlink() or not destination.is_file() or _sha_file(destination) != doc['sha256']:
                    raise ValueError('Destination concurrently changed')
        return doc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    split_parser = commands.add_parser('split')
    split_parser.add_argument('--source', required=True)
    split_parser.add_argument('--parts-dir', required=True)
    restore_parser = commands.add_parser('restore')
    restore_parser.add_argument('--manifest', required=True)
    restore_parser.add_argument('--out', required=True)
    args = parser.parse_args()
    doc = (split(args.source, args.parts_dir) if args.command == 'split'
           else restore(args.manifest, args.out))
    print(json.dumps({'command': args.command, 'bytes': doc['bytes'],
                      'sha256': doc['sha256'], 'parts': len(doc['parts'])}))


if __name__ == '__main__':
    main()
