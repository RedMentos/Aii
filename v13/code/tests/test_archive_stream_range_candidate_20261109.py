"""Exact streaming spans must validate the whole live source before release."""
import zlib
import sqlite3

import pytest

from v13 import archive
from v13 import archive_stream_range_candidate as stream
from v13.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    r = Runtime(tmp_path)
    r.sleep.cycle.set_policy('enabled', 'off')
    try:
        yield r
    finally:
        r.close()


def make_ref(r, text):
    return r.store.source(text, 'USER')


def partial(ref, start, end):
    return dict(ref, char_start=start, char_end=end)


def test_plain_unicode_character_offsets_across_byte_chunk_boundary(runtime):
    text = 'a' * (stream.CHUNK_BYTES - 1) + '😀äΩ中' + 'end'
    ref = make_ref(runtime, text)
    assert stream.read_span(runtime.store, partial(ref, stream.CHUNK_BYTES - 2, stream.CHUNK_BYTES + 4)) == 'a😀äΩ中e'
    assert stream.read_span(runtime.store, partial(ref, len(text), len(text))) == ''


def test_compressed_unicode_and_empty_span(runtime):
    text = ('alpha 😀 Deutsch Ω 你好\n' * 10000) + 'THE END'
    ref = make_ref(runtime, text)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    start = len(text) - 14
    assert stream.read_span(runtime.store, partial(ref, start, len(text))) == text[start:]
    assert stream.read_span(runtime.store, partial(ref, 0, 0)) == ''


def test_trailing_data_or_second_stream_is_rejected_even_if_old_reader_accepts(runtime):
    text = 'valid synthetic source ' * 1000
    ref = make_ref(runtime, text)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    path = runtime.home / 'data/blobs' / (ref['sha256'] + '.z')
    compressed = path.read_bytes()
    for suffix in (b'junk', zlib.compress(b'another stream')):
        path.write_bytes(compressed + suffix)
        assert runtime.store.read_source(ref) == text  # the frozen reader ignores unused_data
        with pytest.raises(stream.ArchiveReadError, match='trailing'):
            stream.read_span(runtime.store, partial(ref, 0, 5))


def test_truncated_or_modified_archive_never_returns_a_partial_result(runtime):
    text = 'valid synthetic source ' * 1000
    ref = make_ref(runtime, text)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    path = runtime.home / 'data/blobs' / (ref['sha256'] + '.z')
    compressed = path.read_bytes()
    path.write_bytes(compressed[:-2])
    with pytest.raises(stream.ArchiveReadError, match='truncated'):
        stream.read_span(runtime.store, partial(ref, 0, 5))
    path.write_bytes(zlib.compress(b'x' * len(text)))
    with pytest.raises(stream.ArchiveReadError, match='hash'):
        stream.read_span(runtime.store, partial(ref, 0, 5))


def test_budgets_and_bounds_fail_closed(runtime):
    text = 'valid source ' * 1000
    ref = make_ref(runtime, text)
    for invalid in (partial(ref, -1, 2), partial(ref, True, 2), partial(ref, 2, 1), partial(ref, 0, len(text) + 1)):
        with pytest.raises(stream.ArchiveReadError):
            stream.read_span(runtime.store, invalid)
    with pytest.raises(stream.ArchiveReadError, match='oversized'):
        stream.read_span(runtime.store, partial(ref, 0, 10), max_chars=9)
    with pytest.raises(stream.ArchiveReadError, match='budget'):
        stream.read_span(runtime.store, partial(ref, 0, 3), max_source_bytes=len(text) - 1)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    with pytest.raises(stream.ArchiveReadError, match='bounded'):
        stream.read_span(runtime.store, partial(ref, 0, 3), max_archive_bytes=1)


def test_deleted_or_mismatched_reference_never_read(runtime):
    text = 'valid synthetic source ' * 100
    ref = make_ref(runtime, text)
    with pytest.raises(stream.ArchiveReadError):
        stream.read_span(runtime.store, dict(ref, sha256='0' * 64))
    with runtime.store.tx() as c:
        c.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
    with pytest.raises(stream.ArchiveReadError, match='deleted'):
        stream.read_span(runtime.store, partial(ref, 0, 5))


def test_invalid_utf8_or_plain_corruption_does_not_fall_back(runtime):
    ref = make_ref(runtime, 'valid synthetic source ' * 100)
    path = runtime.home / 'data/blobs' / ref['sha256']
    path.write_bytes(b'\xff' * path.stat().st_size)
    # A valid-looking alternate archive must not silently override a corrupt plain file.
    path.with_name(path.name + '.z').write_bytes(zlib.compress(b'other'))
    with pytest.raises(stream.ArchiveReadError):
        stream.read_span(runtime.store, partial(ref, 0, 5))


def test_decompressed_output_cannot_exceed_source_metadata(runtime):
    ref = make_ref(runtime, 'small original ' * 100)
    path = runtime.home / 'data/blobs' / ref['sha256']
    path.unlink()
    path.with_name(path.name + '.z').write_bytes(zlib.compress(b'x' * (1024 * 1024)))
    with pytest.raises(stream.ArchiveReadError, match='exceeds budget'):
        stream.read_span(runtime.store, partial(ref, 0, 5))


def test_inflater_allocates_at_most_one_byte_over_declared_size(runtime, monkeypatch):
    text = 'small original ' * 100
    ref = make_ref(runtime, text)
    path = runtime.home / 'data/blobs' / ref['sha256']
    path.unlink()
    path.with_name(path.name + '.z').write_bytes(zlib.compress(b'x' * (1024 * 1024)))
    original = stream.zlib.decompressobj
    limits = []
    class WatchingInflater:
        def __init__(self):
            self.inner = original()
        def decompress(self, data, limit):
            limits.append(limit)
            return self.inner.decompress(data, limit)
        def __getattr__(self, key):
            return getattr(self.inner, key)
    monkeypatch.setattr(stream.zlib, 'decompressobj', WatchingInflater)
    with pytest.raises(stream.ArchiveReadError, match='exceeds budget'):
        stream.read_span(runtime.store, partial(ref, 0, 5))
    assert limits and max(limits) <= len(text) + 1


def test_input_growth_reads_at_most_one_byte_over_limit(runtime, monkeypatch):
    ref = make_ref(runtime, 'synthetic source ' * 100)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    path = runtime.home / 'data/blobs' / (ref['sha256'] + '.z')
    original_size = path.stat().st_size
    original_read = stream.os.read
    requested = []
    def grow_then_read(fd, size):
        if not requested:
            with path.open('ab') as handle:
                handle.write(b'x' * (2 * stream.CHUNK_BYTES))
        requested.append(size)
        return original_read(fd, size)
    monkeypatch.setattr(stream.os, 'read', grow_then_read)
    with pytest.raises(stream.ArchiveReadError, match='budget'):
        stream.read_span(runtime.store, partial(ref, 0, 5), max_archive_bytes=original_size)
    assert requested == [original_size + 1]


def test_stream_reader_rejects_unreviewed_store(runtime, monkeypatch):
    ref = make_ref(runtime, 'synthetic source ' * 100)
    monkeypatch.setattr(stream, 'STORE_SHA256', '0' * 64)
    with pytest.raises(stream.ArchiveReadError, match='Store source changed'):
        stream.read_span(runtime.store, partial(ref, 0, 5))


def test_nested_store_transaction_is_not_supported(runtime):
    ref = make_ref(runtime, 'synthetic source ' * 100)
    with runtime.store.tx():
        with pytest.raises(sqlite3.OperationalError, match='transaction'):
            stream.read_span(runtime.store, partial(ref, 0, 5))


def test_symlink_to_source_is_rejected(runtime, tmp_path):
    ref = make_ref(runtime, 'synthetic source ' * 100)
    path = runtime.home / 'data/blobs' / ref['sha256']
    other = tmp_path / 'other'
    path.rename(other)
    path.symlink_to(other)
    with pytest.raises(stream.ArchiveReadError):
        stream.read_span(runtime.store, partial(ref, 0, 5))
