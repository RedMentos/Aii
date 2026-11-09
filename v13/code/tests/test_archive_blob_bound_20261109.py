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
