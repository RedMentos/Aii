"""Bounded zlib archive reads for source blobs.

Archive format is unchanged. This is deliberately an in-memory API compatible
with Store.blob_bytes; the limit bounds decompressed allocation on mobile.
"""
import zlib

MAX_ARCHIVED_SOURCE_BYTES = 128 * 1024 * 1024
CHUNK_BYTES = 64 * 1024


def read_archived_blob(path, *, limit=MAX_ARCHIVED_SOURCE_BYTES):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("Ungültiges Archiv-Limit")
    decoder = zlib.decompressobj()
    chunks = []
    total = 0
    try:
        with open(path, "rb") as stream:
            while True:
                compressed = stream.read(CHUNK_BYTES)
                if not compressed:
                    break
                remaining = limit - total
                decoded = decoder.decompress(compressed, remaining + 1)
                total += len(decoded)
                if total > limit or decoder.unconsumed_tail:
                    raise ValueError("Archiv-Blob zu groß")
                chunks.append(decoded)
                if decoder.eof:
                    if decoder.unused_data or stream.read(1):
                        raise ValueError("Archiv-Blob enthält zusätzliche Daten")
                    break
        if not decoder.eof:
            raise ValueError("Archiv-Blob beschädigt oder zu groß")
        tail = decoder.flush()
        if total + len(tail) > limit:
            raise ValueError("Archiv-Blob zu groß")
        chunks.append(tail)
    except zlib.error as exc:
        raise ValueError("Archiv-Blob beschädigt") from exc
    return b"".join(chunks)
