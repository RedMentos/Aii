"""Read a bounded exact text span from a source, including large zlib archives.

This isolated candidate streams and verifies the *entire* source before
returning any text. It does not mutate the archive or connect to the runtime.
"""
from __future__ import annotations

import codecs
import hashlib
import os
from pathlib import Path
import re
import stat
import zlib

from .store import Store

CHUNK_BYTES = 64 * 1024
DEFAULT_SOURCE_LIMIT = 128 * 1024 * 1024
HARD_SOURCE_LIMIT = 1024 * 1024 * 1024
MAX_RETURN_CHARS = 64 * 1024
STORE_SHA256 = 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980'


class ArchiveReadError(ValueError):
    pass


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_span(store, ref, *, max_source_bytes=DEFAULT_SOURCE_LIMIT,
              max_archive_bytes=DEFAULT_SOURCE_LIMIT, max_chars=MAX_RETURN_CHARS):
    """Return a verified UTF-8 character span without materializing the source.

    SQLite stays write-locked while reading, so participating forget writers
    cannot commit midway. The cap is an input/output size bound, not a deadline.
    """
    if hashlib.sha256((Path(__file__).resolve().parent / 'store.py').read_bytes()).hexdigest() != STORE_SHA256:
        raise ArchiveReadError('reviewed Store source changed')
    if type(store) is not Store:
        raise ArchiveReadError('reviewed Store instance required')
    if (not isinstance(ref, dict) or not isinstance(ref.get('source_id'), str)
            or not isinstance(ref.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', ref['sha256'])
            or ref.get('modality') != 'text'):
        raise ArchiveReadError('invalid source reference')
    if (not _int(max_source_bytes, 1, HARD_SOURCE_LIMIT)
            or not _int(max_archive_bytes, 1, HARD_SOURCE_LIMIT)
            or not _int(max_chars, 0, MAX_RETURN_CHARS)):
        raise ArchiveReadError('invalid streaming budget')
    start, end = ref.get('char_start'), ref.get('char_end')
    if not _int(start, 0, HARD_SOURCE_LIMIT) or not _int(end, start, HARD_SOURCE_LIMIT) or end - start > max_chars:
        raise ArchiveReadError('invalid or oversized character span')
    if not all(hasattr(os, flag) for flag in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')):
        raise ArchiveReadError('safe source streaming unavailable')
    key = ref['sha256']
    try:
        with store.tx() as conn:
            source = conn.execute('SELECT hash,bytes,chars,deleted FROM sources WHERE id=?', (ref['source_id'],)).fetchone()
            if (source is None or source['deleted'] or source['hash'] != key
                    or not _int(source['bytes'], 0, max_source_bytes)
                    or not _int(source['chars'], 0, HARD_SOURCE_LIMIT) or end > source['chars']):
                raise ArchiveReadError('source missing, deleted, mismatched or over budget')
            dir_fd = os.open(store.home / 'data/blobs', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            data_fd = None
            try:
                name = key
                try:
                    data_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
                    compressed = False
                except FileNotFoundError:
                    name = key + '.z'
                    data_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
                    compressed = True
                initial = os.fstat(data_fd)
                if (not stat.S_ISREG(initial.st_mode)
                        or initial.st_size > (max_archive_bytes if compressed else max_source_bytes)):
                    raise ArchiveReadError('source file is not a bounded regular file')
                digest = hashlib.sha256()
                decoder = codecs.getincrementaldecoder('utf-8')('strict')
                pieces = []
                n_bytes = n_chars = n_input = 0

                def accept(value, final=False):
                    nonlocal n_bytes, n_chars
                    n_bytes += len(value)
                    if n_bytes > source['bytes'] or n_bytes > max_source_bytes:
                        raise ArchiveReadError('decompressed source exceeds budget')
                    digest.update(value)
                    text = decoder.decode(value, final=final)
                    lo, hi = max(start - n_chars, 0), min(end - n_chars, len(text))
                    if lo < hi:
                        pieces.append(text[lo:hi])
                    n_chars += len(text)
                    if n_chars > source['chars']:
                        raise ArchiveReadError('source character count mismatch')

                inflater = zlib.decompressobj() if compressed else None
                while True:
                    input_budget = max_archive_bytes if compressed else max_source_bytes
                    # One extra byte is sufficient to detect a concurrent growth.
                    data = os.read(data_fd, min(CHUNK_BYTES, input_budget - n_input + 1))
                    if not data:
                        break
                    n_input += len(data)
                    if n_input > (max_archive_bytes if compressed else max_source_bytes):
                        raise ArchiveReadError('input source exceeds budget')
                    if not compressed:
                        accept(data)
                        continue
                    if inflater.eof:
                        raise ArchiveReadError('trailing compressed data')
                    while data:
                        old_len = len(data)
                        # zlib treats max_length=0 as unlimited; one extra byte
                        # detects a stream that exceeds its declared size.
                        output_budget = min(CHUNK_BYTES, source['bytes'] - n_bytes + 1,
                                            max_source_bytes - n_bytes + 1)
                        chunk = inflater.decompress(data, output_budget)
                        data = inflater.unconsumed_tail
                        accept(chunk)
                        if inflater.eof:
                            if inflater.unused_data or data:
                                raise ArchiveReadError('trailing compressed data')
                            break
                        if not chunk and len(data) >= old_len:
                            raise ArchiveReadError('compressed stream made no progress')
                if inflater is not None and not inflater.eof:
                    raise ArchiveReadError('truncated compressed source')
                accept(b'', final=True)
                if (n_bytes != source['bytes'] or n_chars != source['chars'] or digest.hexdigest() != key
                        or _identity(os.fstat(data_fd)) != _identity(initial)
                        or _identity(os.stat(name, dir_fd=dir_fd, follow_symlinks=False)) != _identity(initial)):
                    raise ArchiveReadError('source hash, size or identity mismatch')
                result = ''.join(pieces)
                if len(result) != end - start:
                    raise ArchiveReadError('incomplete source span')
                return result
            finally:
                if data_fd is not None:
                    os.close(data_fd)
                os.close(dir_fd)
    except ArchiveReadError:
        raise
    except (OSError, UnicodeError, zlib.error) as exc:
        raise ArchiveReadError('source streaming failed') from exc
