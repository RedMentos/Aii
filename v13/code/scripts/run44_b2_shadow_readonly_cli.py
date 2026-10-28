"""Run44 offline-only immutable V13 Store B2 eligibility SHADOW diagnostic.

NEVER open a production Store/Runtime here: their constructors mutate state.
Refuses active coordinator owner or nonempty WAL, and writes output only
outside installed-home. Not a live, native, or device proof.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote
import zlib

from scripts import run42_b2_eligibility_source_shadow as study

MAX_BLOB = 64 * 1024 * 1024
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def _read_bounded_regular_file(path, *, cap_error='RUN44_BLOB_CAP'):
    """Read only the opened regular inode, never following a final symlink.

    A pathname stat followed by Path.read_bytes() is not a resource cap: a
    concurrent replacement/growth can evade it. Keep the descriptor open and
    enforce the byte limit on the actual stream, including after fstat().
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError('RUN44_BLOB_FILE_UNSAFE') from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('RUN44_BLOB_FILE_UNSAFE')
        if info.st_size > MAX_BLOB:
            raise ValueError(cap_error)
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, MAX_BLOB + 1 - total))
            if not chunk:
                return b''.join(chunks)
            total += len(chunk)
            if total > MAX_BLOB:
                raise ValueError(cap_error)
            chunks.append(chunk)
    finally:
        os.close(fd)


class OfflineView:
    def __init__(self, home):
        self.home = Path(home).resolve(strict=True)
        self.db = None
        self.lock = None
        if not self.home.is_dir():
            raise ValueError('RUN44_HOME_NOT_DIRECTORY')
        for directory in (self.home/'data', self.home/'data/db', self.home/'data/blobs'):
            if (directory.is_symlink() or not directory.is_dir() or
                    not directory.resolve().is_relative_to(self.home)):
                raise ValueError('RUN44_UNSAFE_HOME_DIRECTORY')
        db_path = self.home / 'data/db/brain.sqlite3'
        lock_path = self.home / 'data/coordinator.lock'
        wal = db_path.with_name(db_path.name + '-wal')
        if (db_path.is_symlink() or not db_path.is_file() or
                lock_path.is_symlink() or not lock_path.is_file() or
                (wal.exists() and (wal.is_symlink() or wal.stat().st_size != 0))):
            raise ValueError('RUN44_NOT_QUIESCENT_OR_INVALID_HOME')
        try:
            self.lock = lock_path.open('rb')
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError('RUN44_ACTIVE_COORDINATOR') from exc
            uri = 'file:' + quote(str(db_path), safe='/') + '?mode=ro&immutable=1'
            self.db = sqlite3.connect(uri, uri=True, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA query_only=ON')
            self.db.execute('SELECT 1 FROM events LIMIT 1')
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None
        if self.lock is not None:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()
            self.lock = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def rows(self, sql, args=()):
        if not sql.lstrip().upper().startswith('SELECT ') or ';' in sql:
            raise ValueError('RUN44_SELECT_ONLY')
        return [dict(row) for row in self.db.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def read_source(self, ref):
        if (type(ref) is not dict or type(ref.get('source_id')) is not str or
                type(ref.get('sha256')) is not str or not HEX64.fullmatch(ref['sha256']) or
                type(ref.get('char_start')) is not int or
                type(ref.get('char_end')) is not int or
                ref.get('modality') != 'text'):
            raise ValueError('RUN44_SOURCE_REF')
        row = self.one('SELECT hash,deleted FROM sources WHERE id=?', (ref['source_id'],))
        if not row or row['deleted'] or row['hash'] != ref['sha256']:
            raise ValueError('RUN44_REVOKED_SOURCE')
        h = row['hash']
        if not HEX64.fullmatch(h):
            raise ValueError('RUN44_SOURCE_HASH')
        plain = self.home / 'data/blobs' / h
        packed = plain.with_name(h + '.z')
        if plain.is_symlink() or packed.is_symlink():
            raise ValueError('RUN44_SYMLINK_BLOB')
        if plain.is_file():
            data = _read_bounded_regular_file(plain)
        elif packed.is_file():
            decoder = zlib.decompressobj()
            try:
                data = decoder.decompress(
                    _read_bounded_regular_file(packed, cap_error='RUN44_ARCHIVE_CAP'),
                    MAX_BLOB)
            except zlib.error as exc:
                raise ValueError('RUN44_ARCHIVE_CORRUPT') from exc
            if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
                raise ValueError('RUN44_ARCHIVE_INCOMPLETE')
        else:
            raise ValueError('RUN44_SOURCE_MISSING')
        if hashlib.sha256(data).hexdigest() != h:
            raise ValueError('RUN44_SOURCE_TAMPER')
        text = data.decode('utf-8')
        start, end = ref['char_start'], ref['char_end']
        if not 0 <= start <= end <= len(text):
            raise ValueError('RUN44_SOURCE_SPAN')
        return text[start:end]


def diagnose(home, event_id, model_revision):
    if (type(event_id) is not str or not 1 <= len(event_id) <= 128 or
            type(model_revision) is not str or not 1 <= len(model_revision) <= 256):
        raise ValueError('RUN44_INPUT')
    with OfflineView(home) as view:
        row = view.one('SELECT packet,session_id,generation_id FROM events WHERE id=?', (event_id,))
        if not row:
            raise ValueError('RUN44_EVENT_NOT_FOUND')
        event = json.loads(row['packet'])
        result = study.evaluate(view, event, row['session_id'],
                                row['generation_id'], model_revision)
        return {'schema': 'v13.run44.b2.offline.shadow.v1',
                'event_id': event_id, 'session_id': row['session_id'],
                'generation_id': row['generation_id'],
                'status': result['status'], 'decision': result['decision'],
                'source_refs': result['source_refs'],
                'authority': 'SHADOW_NO_AUTHORITY',
                'canonical_gate_pass': False, 'native_executed': False,
                'phone_measured': False, 'jepa_weight': 0,
                'whole_system_complete': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installed-home', type=Path, required=True)
    p.add_argument('--event-id', required=True)
    p.add_argument('--model-revision', required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    home = args.installed_home.resolve(strict=True)
    out = args.out.resolve(strict=False)
    if out.is_relative_to(home) or out.exists() or out.is_symlink():
        raise ValueError('RUN44_OUTPUT_PATH_REFUSED')
    result = diagnose(home, args.event_id, args.model_revision)
    data = (json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({'status': result['status'], 'sha256': hashlib.sha256(data).hexdigest(),
                      'authority': 'SHADOW_NO_AUTHORITY'}, sort_keys=True))


if __name__ == '__main__':
    main()
