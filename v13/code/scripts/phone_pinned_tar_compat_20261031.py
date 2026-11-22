#!/usr/bin/env python3
"""Software-only compatibility check of original pinned llama.cpp tarballs.

No GGUF download, native process execution, training or Redmi claim.
The catalog's exact SHA256, sizes and URLs remain the sole source of truth.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from v13.bootstrap import extract
from v13.common import file_hash
from v13.models import catalog, download_file


def tree_fingerprint(root):
    rows = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            rows.append(['symlink', relative, os.readlink(path)])
        elif path.is_file():
            rows.append(['file', relative, path.stat().st_size, file_hash(path)])
        elif path.is_dir():
            rows.append(['dir', relative])
        else:
            raise ValueError('Unexpected extracted member type: ' + relative)
    if not rows:
        raise ValueError('Empty extracted tree')
    raw = json.dumps(rows, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return {'sha256': hashlib.sha256(raw).hexdigest(),
            'entries': len(rows),
            'regular_files': sum(row[0] == 'file' for row in rows),
            'symlinks': sum(row[0] == 'symlink' for row in rows)}


def verify(work):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    runner = catalog()['runner']
    tag = runner['tag']
    if tag != 'b10964':
        raise ValueError('Pinned b10964 cohort changed: ' + tag)
    sources = [
        ('source', {'url': runner['source_url'],
                    'size': runner['source_size'],
                    'sha256': runner['source_sha256']}),
        ('linux-x86_64', runner['linux_binaries']['linux-x86_64']),
    ]
    result = {'schema': 'v13.phone_pinned_tar_compat.linux_software.v1',
              'runner_tag': tag, 'native_executed': False,
              'model_downloaded': False, 'redmi_measured': False,
              'step2_promoted': False, 'body_jepa_promoted': False,
              'b3_promoted': False, 'age_promoted': False, 'archives': {}}
    for name, spec in sources:
        archive = work / (name + '.tar.gz')
        download_file(spec, archive, print)
        actual_size = archive.stat().st_size
        actual_hash = file_hash(archive)
        if actual_size != spec['size'] or actual_hash != spec['sha256']:
            raise ValueError('Pinned archive hash/size mismatch: ' + name)
        target = work / (name + '-tree')
        extract(archive, target)
        first = tree_fingerprint(target)
        if name == 'source':
            cmake = target / ('llama.cpp-' + tag) / 'CMakeLists.txt'
            if not cmake.is_file() or cmake.is_symlink():
                raise ValueError('Pinned source CMakeLists.txt missing')
            proof_path = cmake.relative_to(target).as_posix()
        else:
            matches = list(target.rglob('llama-server'))
            if len(matches) != 1 or not matches[0].is_file() or matches[0].is_symlink():
                raise ValueError('Pinned Linux llama-server not a unique regular file')
            with matches[0].open('rb') as stream:
                if stream.read(4) != b'\x7fELF':
                    raise ValueError('Pinned Linux llama-server is not ELF')
            proof_path = matches[0].relative_to(target).as_posix()
        extract(archive, target)
        second = tree_fingerprint(target)
        if first != second:
            raise ValueError('Pinned extraction retry tree changed: ' + name)
        result['archives'][name] = {
            'source_url': spec['url'], 'source_sha256': actual_hash,
            'source_size': actual_size, 'proof_path': proof_path,
            'first_tree': first, 'retry_tree': second, 'retry_identical': True}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.work)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
