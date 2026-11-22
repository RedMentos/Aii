"""Keep a verified text archive when another text reference shares its bytes.

Called only while Store holds its source-publication transaction. Image ingest
continues to require a plain file through the original lifecycle helper.
"""
import hashlib
import os
from pathlib import Path
import stat
import zlib

from . import source_lifecycle_candidate as lifecycle

CHUNK = 64 * 1024
READER_LIMIT = 64 * 1024 * 1024


def verify_or_create_text_blob(path, data, expected_hash, kind='USER'):
    key = lifecycle._key(expected_hash)
    path = Path(path)
    if type(data) is not bytes or hashlib.sha256(data).hexdigest() != key or path.name != key:
        raise ValueError('text source does not match expected hash')
    from .archive import COLD_KINDS
    if (kind not in COLD_KINDS and kind != 'C3_OUTPUT_HISTORY_CONTEXT'
            or path.exists() or path.is_symlink() or len(data) > READER_LIMIT):
        return lifecycle.verify_or_create_blob(path, data, key)
    dir_fd = lifecycle._directory(path.parent)
    fd = None
    try:
        try:
            fd = lifecycle._open_existing(dir_fd, key + '.z')
        except FileNotFoundError:
            return lifecycle.verify_or_create_blob(path, data, key)
        first = os.fstat(fd)
        input_limit = len(data) + len(data) // 1000 + CHUNK
        if not stat.S_ISREG(first.st_mode) or first.st_size > input_limit:
            raise ValueError('text archive is not a bounded regular file')
        inflater = zlib.decompressobj()
        consumed = produced = 0
        while True:
            block = os.read(fd, min(CHUNK, input_limit - consumed + 1))
            if not block:
                break
            consumed += len(block)
            if consumed > input_limit or inflater.eof:
                raise ValueError('text archive exceeds input budget or has trailing data')
            while block:
                previous = len(block)
                output = inflater.decompress(block, min(CHUNK, len(data) - produced + 1))
                block = inflater.unconsumed_tail
                if produced + len(output) > len(data) or output != data[produced:produced + len(output)]:
                    raise ValueError('text archive differs from source bytes')
                produced += len(output)
                if inflater.eof:
                    if inflater.unused_data or block:
                        raise ValueError('text archive has trailing data')
                    break
                if not output and len(block) >= previous:
                    raise ValueError('text archive makes no progress')
        last = os.fstat(fd)
        named = os.stat(key + '.z', dir_fd=dir_fd, follow_symlinks=False)
        if (not inflater.eof or produced != len(data) or consumed != first.st_size
                or lifecycle._identity(first) != lifecycle._identity(last)
                or lifecycle._identity(last) != lifecycle._identity(named)):
            raise ValueError('text archive is incomplete or changed')
        return 'VERIFIED_ARCHIVE_REUSED'
    except zlib.error as exc:
        raise ValueError('corrupt text archive') from exc
    finally:
        if fd is not None:
            os.close(fd)
        os.close(dir_fd)
