import zlib

import pytest

from v13.archive_blob import read_archived_blob


def test_archive_reader_preserves_source_larger_than_legacy_64_mib(tmp_path):
    raw = b"V13-source-" * (64 * 1024 * 1024 // 11 + 1)
    path = tmp_path / "source.z"
    path.write_bytes(zlib.compress(raw, level=1))
    assert len(raw) > 64 * 1024 * 1024
    assert read_archived_blob(path) == raw


@pytest.mark.parametrize("payload", [
    zlib.compress(b"hello") + b"trailing",
    zlib.compress(b"hello") + zlib.compress(b"world"),
    zlib.compress(b"hello")[:-2],
    b"not zlib",
])
def test_archive_reader_rejects_corruption_and_trailing_bytes(tmp_path, payload):
    path = tmp_path / "source.z"
    path.write_bytes(payload)
    with pytest.raises(ValueError):
        read_archived_blob(path)


def test_archive_reader_rejects_bomb_without_unbounded_allocation(tmp_path):
    path = tmp_path / "bomb.z"
    path.write_bytes(zlib.compress(b"x" * 100_000))
    with pytest.raises(ValueError, match="zu groß"):
        read_archived_blob(path, limit=1024)


def test_archive_reader_accepts_exact_limit(tmp_path):
    path = tmp_path / "exact.z"
    path.write_bytes(zlib.compress(b"x" * 1024))
    assert read_archived_blob(path, limit=1024) == b"x" * 1024


def test_store_blob_bytes_reads_archived_source_and_preserves_hash(tmp_path):
    import hashlib
    from v13.store import Store

    raw = b"source-linked memory"
    sha = hashlib.sha256(raw).hexdigest()
    blobs = tmp_path / "data" / "blobs"
    blobs.mkdir(parents=True)
    (blobs / (sha + ".z")).write_bytes(zlib.compress(raw))
    store = Store.__new__(Store)
    store.home = tmp_path
    assert store.blob_bytes(sha) == raw


def test_store_blob_bytes_rejects_corrupt_archive(tmp_path):
    from v13.store import Store

    blobs = tmp_path / "data" / "blobs"
    blobs.mkdir(parents=True)
    (blobs / ("a" * 64 + ".z")).write_bytes(zlib.compress(b"content") + b"garbage")
    store = Store.__new__(Store)
    store.home = tmp_path
    with pytest.raises(ValueError):
        store.blob_bytes("a" * 64)


def test_read_source_roundtrip_from_archived_blob_with_verified_provenance(tmp_path):
    import hashlib
    from v13.store import Store

    raw = "V13 archived ä source text".encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    blobs = tmp_path / "data" / "blobs"
    blobs.mkdir(parents=True)
    (blobs / (sha + ".z")).write_bytes(zlib.compress(raw))
    store = Store.__new__(Store)
    store.home = tmp_path
    store.one = lambda query, args: {"hash": sha, "deleted": 0}
    ref = {"source_id": "src_test", "sha256": sha, "char_start": 4, "char_end": 12}
    assert store.read_source(ref) == "archived"


def test_read_source_rejects_archive_with_wrong_content_hash(tmp_path):
    import hashlib
    from v13.store import Store

    original = b"trusted original"
    sha = hashlib.sha256(original).hexdigest()
    blobs = tmp_path / "data" / "blobs"
    blobs.mkdir(parents=True)
    (blobs / (sha + ".z")).write_bytes(zlib.compress(b"tampered archive"))
    store = Store.__new__(Store)
    store.home = tmp_path
    store.one = lambda query, args: {"hash": sha, "deleted": 0}
    ref = {"source_id": "src_test", "sha256": sha, "char_start": 0, "char_end": 7}
    with pytest.raises(ValueError, match="Source-Hash"):
        store.read_source(ref)
