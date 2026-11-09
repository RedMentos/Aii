"""Verified bounded UTF-8 SourceRef slices without materializing whole archives.

The full source is hashed before any selected characters are returned.
"""
import codecs
import hashlib
import zlib
from .archive_blob import CHUNK_BYTES, MAX_ARCHIVED_SOURCE_BYTES


def verified_source_slice(path, expected_sha, start, end, *, compressed=False,
                          limit=MAX_ARCHIVED_SOURCE_BYTES):
    if (not isinstance(start, int) or isinstance(start, bool)
            or not isinstance(end, int) or isinstance(end, bool)
            or start < 0 or end < start):
        raise ValueError("SourceRef außerhalb Text")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("Ungültiges Archiv-Limit")
    digest = hashlib.sha256()
    utf8 = codecs.getincrementaldecoder("utf-8")("strict")
    selected = []
    chars = 0
    total = 0

    def consume(raw):
        nonlocal chars, total
        total += len(raw)
        if total > limit:
            raise ValueError("Source-Blob zu groß")
        digest.update(raw)
        text = utf8.decode(raw)
        next_chars = chars + len(text)
        if chars < end and next_chars > start:
            selected.append(text[max(0, start - chars):min(len(text), end - chars)])
        chars = next_chars

    with open(path, "rb") as stream:
        if compressed:
            decoder = zlib.decompressobj()
            try:
                while True:
                    chunk = stream.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    raw = decoder.decompress(chunk, limit - total + 1)
                    consume(raw)
                    if decoder.unconsumed_tail:
                        raise ValueError("Source-Blob zu groß")
                    if decoder.eof:
                        if decoder.unused_data or stream.read(1):
                            raise ValueError("Archiv-Blob enthält zusätzliche Daten")
                        break
                if not decoder.eof:
                    raise ValueError("Archiv-Blob beschädigt")
                consume(decoder.flush())
            except zlib.error as exc:
                raise ValueError("Archiv-Blob beschädigt") from exc
        else:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                consume(chunk)
    trailing = utf8.decode(b"", final=True)
    chars += len(trailing)
    if chars < end:
        raise ValueError("SourceRef außerhalb Text")
    if digest.hexdigest() != expected_sha:
        raise ValueError("Source-Hash falsch")
    return "".join(selected)
