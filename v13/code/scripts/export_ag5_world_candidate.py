#!/usr/bin/env python3
"""Export exact staged AG5/World merge delta for independent review.

Runs only in disposable CI after safe conflict resolution; does not commit/push.
Outputs changed paths + stage-0 Git blob SHA/mode and a tar of their bytes.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile


def git(*args):
    return subprocess.check_output(['git', *args])


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths = [x.decode('utf-8') for x in git('diff', '--cached', '--name-only', '-z').split(b'\0') if x]
    index = {}
    for line in git('ls-files', '-s', '-z').split(b'\0'):
        if not line:
            continue
        header, path = line.split(b'\t', 1)
        mode, sha, stage = header.decode('ascii').split()
        if stage == '0':
            index[path.decode('utf-8')] = (mode, sha)
    entries = []
    tar_path = out / 'CANDIDATE_CHANGED_FILES.tar.gz'
    with tarfile.open(tar_path, 'w:gz') as tar:
        for path in paths:
            if path in index:
                mode, sha = index[path]
                file = Path(path)
                if not (file.is_file() or file.is_symlink()):
                    raise ValueError('Staged blob path missing: ' + path)
                tar.add(file, arcname=path, recursive=False)
                entries.append({'path': path, 'mode': mode, 'type': 'blob',
                                'sha': sha, 'deleted': False})
            else:
                entries.append({'path': path, 'sha': None, 'deleted': True})
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    result = {
        'schema': 'V13_AG5_WORLD_DISPOSABLE_DELTA_V1',
        'world_parent_sha': 'aab74aa900bfbd767f2983ba40a16fc0b8b95a3b',
        'ag5_parent_sha': 'c615497384dc5519be59232451895ca443ce9e45',
        'candidate_tree_sha': git('write-tree').decode().strip(),
        'changed_paths': len(entries), 'entries': entries,
        'changed_files_tar_sha256': digest,
        'remote_commit_created': False,
    }
    (out / 'CANDIDATE_DELTA.json').write_text(json.dumps(
        result, sort_keys=True, indent=2) + '\n')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: export_ag5_world_candidate.py /proof-directory')
    print(json.dumps(export(sys.argv[1]), sort_keys=True))
