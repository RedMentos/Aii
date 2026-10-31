#!/usr/bin/env python3
"""Fail-closed, read-only no-export preflight for *future* V13 raw artifacts.

The original Run117BJ ZIP remains immutable RED evidence. This scanner does not
sanitize or delete artifacts. Call before upload; preserve raw logs on failure.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

ALLOWED_SUFFIXES = frozenset({'.json', '.jsonl', '.txt', '.log', '.csv', '.tsv', '.md', '.sha256'})
ALLOWED_BASENAMES = frozenset({'SHA256SUMS'})
MAX_FILE_BYTES = 20_000_000
MAX_FILES = 512


def inspect(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        return {'status': 'EXPORT_BOUNDARY_RED', 'violations': ['ROOT_NOT_REGULAR_DIRECTORY'], 'files': 0}
    violations = []
    count = 0
    def walk_error(_):
        violations.append("WALK_ERROR")
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=walk_error):
        # Never follow links, including directory links.
        for name in list(dirs):
            p = Path(base) / name
            if p.is_symlink():
                violations.append('LINK_DIR:' + p.relative_to(root).as_posix())
                dirs.remove(name)
        for name in files:
            p = Path(base) / name
            rel = p.relative_to(root).as_posix()
            count += 1
            if count > MAX_FILES:
                violations.append('TOO_MANY_FILES')
                break
            try:
                st = p.lstat()
                if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                    violations.append('NOT_EXCLUSIVE_REGULAR_FILE:' + rel)
                    continue
                if p.suffix.lower() not in ALLOWED_SUFFIXES and p.name not in ALLOWED_BASENAMES:
                    violations.append('NOT_RAW_TELEMETRY:' + rel)
                    continue
                if st.st_size > MAX_FILE_BYTES:
                    violations.append('RAW_FILE_TOO_LARGE:' + rel)
                    continue
                with p.open('rb') as f:
                    data = f.read(MAX_FILE_BYTES + 1)
                if b'\x00' in data:
                    violations.append('BINARY_CONTENT:' + rel)
                    continue
                data.decode('utf-8')
            except (OSError, UnicodeError):
                violations.append('UNREADABLE_OR_NONUTF8:' + rel)
        if count > MAX_FILES:
            break
    return {'status': 'EXPORT_BOUNDARY_RED' if violations else 'RAW_TELEMETRY_ONLY',
            'violations': sorted(set(violations)), 'files': count,
            'no_export_authority': True, 'no_files_deleted': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact_directory', type=Path)
    args = parser.parse_args(argv)
    result = inspect(args.artifact_directory)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'RAW_TELEMETRY_ONLY' else 1


if __name__ == '__main__':
    sys.exit(main())
