"""Review-only, source-bound guard for archiving cold source blobs.

The frozen runtime does not import this candidate. A separate materializer
wires it into a disposable copy after checking the exact reviewed sources.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import zlib

from . import archive
from .common import now
from .store import Store

# Matches the 64 MiB limit in the reviewed Store.blob_bytes implementation.
READER_LIMIT = 64 * 1024 * 1024
CHUNK = 1024 * 1024
SOURCE_PINS = {
    'archive.py': {'adbdd844c2275d527a689eda789a3f247759967677e573b92bf7af7ad68404bf',
                   '3f421423ce890b90033470e15150b1ba9830642e6b5e92e61b654801602e90b4'},
    'store.py': {'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980'},
    'common.py': {'0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a'},
}


def _check_sources():
    directory = Path(__file__).resolve().parent
    for name, allowed in SOURCE_PINS.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() not in allowed:
            raise ValueError('archive guard source changed: ' + name)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        n = os.write(fd, view)
        if n <= 0:
            raise OSError('short archive write')
        view = view[n:]


def _read_bounded(fd, limit):
    parts = []
    remaining = limit + 1
    while remaining:
        part = os.read(fd, min(CHUNK, remaining))
        if not part:
            break
        parts.append(part)
        remaining -= len(part)
    value = b''.join(parts)
    if len(value) > limit:
        return None
    return value


def _still_eligible(conn, key, size, clock):
    """Repeat the cold-source admission inside the same transaction as publication."""
    rows = conn.execute('SELECT id,kind,bytes,created FROM sources WHERE hash=? AND deleted=0', (key,)).fetchall()
    if not rows:
        return 'SOURCE_DELETED'
    cutoff = clock() - archive.ARCHIVE_DAYS * 86400
    if (size < archive.MIN_BYTES or any(r['bytes'] != size or r['created'] >= cutoff for r in rows)):
        return 'SOURCE_NO_LONGER_COLD'
    for row in rows:
        if row['kind'] in archive.COLD_KINDS:
            continue
        if row['kind'] != 'HUMAN_DECISION':
            return 'SOURCE_NO_LONGER_COLD'
        states = conn.execute('SELECT active FROM memories WHERE source_id=?', (row['id'],)).fetchall()
        if not states or any(r['active'] != 0 for r in states):
            return 'SOURCE_NO_LONGER_COLD'
    hot = conn.execute(
        'SELECT 1 FROM memories m LEFT JOIN events e ON e.id=m.event_id '
        'WHERE m.active=1 AND (m.source_id IN (SELECT id FROM sources WHERE hash=? AND deleted=0) '
        'OR e.source_id IN (SELECT id FROM sources WHERE hash=? AND deleted=0)) LIMIT 1', (key, key)).fetchone()
    return 'SOURCE_NO_LONGER_COLD' if hot else None


def archive_blob(store, key, clock=now):
    """Archive only if the reviewed reader can decode it and the source stays live.

    Compress outside the DB lock, then recheck coldness and publish under
    BEGIN IMMEDIATE. Existing plain or compressed paths are never replaced.
    """
    _check_sources()
    if type(store) is not Store:
        raise ValueError('reviewed Store instance required')
    if not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key):
        raise ValueError('invalid source hash')
    if not all(hasattr(os, name) for name in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')):
        raise OSError('safe archive primitives unavailable')
    dir_fd = os.open(store.home / 'data/blobs', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    source_fd = None
    try:
        source_fd = os.open(key, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
        initial = os.fstat(source_fd)
        if not stat.S_ISREG(initial.st_mode):
            raise OSError('source blob is not a regular file')
        if initial.st_size > READER_LIMIT:
            return 'READER_LIMIT'
        raw = _read_bounded(source_fd, READER_LIMIT)
        if raw is None:
            return 'READER_LIMIT'
        if _identity(os.fstat(source_fd)) != _identity(initial):
            return 'SOURCE_CHANGED'
        if hashlib.sha256(raw).hexdigest() != key:
            return 'HASH_MISMATCH'
        encoded = zlib.compress(raw, archive.LEVEL)
        if len(encoded) > (1 - archive.MIN_SAVING) * len(raw):
            return 'NO_SAVING'
        # Match the exact size/eof behavior of the reviewed Store reader.
        reader = zlib.decompressobj()
        decoded = reader.decompress(encoded, READER_LIMIT)
        if (reader.unconsumed_tail or not reader.eof or reader.unused_data
                or hashlib.sha256(decoded).hexdigest() != key):
            return 'READER_VERIFY_FAILED'
        del decoded
        with store.tx() as conn:
            reason = _still_eligible(conn, key, len(raw), clock)
            if reason:
                return reason
            try:
                current = os.stat(key, dir_fd=dir_fd, follow_symlinks=False)
            except FileNotFoundError:
                return 'SOURCE_CHANGED'
            if _identity(current) != _identity(initial) or _identity(os.fstat(source_fd)) != _identity(initial):
                return 'SOURCE_CHANGED'
            # The final name is created exclusively: a crash during the write
            # leaves the original plain file readable and no anonymous orphan.
            try:
                out_fd = os.open(key + '.z', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=dir_fd)
            except FileExistsError:
                return 'EXISTING_ARCHIVE'
            try:
                _write_all(out_fd, encoded)
                os.fsync(out_fd)
                os.lseek(out_fd, 0, os.SEEK_SET)
                written = _read_bounded(out_fd, len(encoded))
                if written != encoded:
                    return 'VERIFY_FAILED'
                verified_archive = _identity(os.fstat(out_fd))
                named_archive = os.stat(key + '.z', dir_fd=dir_fd, follow_symlinks=False)
                if (not stat.S_ISREG(named_archive.st_mode)
                        or _identity(named_archive) != verified_archive
                        or _identity(os.fstat(out_fd)) != verified_archive):
                    return 'ARCHIVE_CHANGED'
                # Persist the archive's directory entry before dropping the plain source.
                os.fsync(dir_fd)
                current = os.stat(key, dir_fd=dir_fd, follow_symlinks=False)
                if _identity(current) != _identity(initial) or _identity(os.fstat(source_fd)) != _identity(initial):
                    return 'SOURCE_CHANGED'
                named_archive = os.stat(key + '.z', dir_fd=dir_fd, follow_symlinks=False)
                if (not stat.S_ISREG(named_archive.st_mode)
                        or _identity(named_archive) != verified_archive
                        or _identity(os.fstat(out_fd)) != verified_archive):
                    return 'ARCHIVE_CHANGED'
                os.unlink(key, dir_fd=dir_fd)
                os.fsync(dir_fd)
                return 'ARCHIVED'
            finally:
                # Never remove this archive on failure: an interruption can
                # occur immediately after unlinking the only plain source.
                # A partial file blocks further archiving until reviewed.
                os.close(out_fd)
    finally:
        if source_fd is not None:
            os.close(source_fd)
        os.close(dir_fd)
