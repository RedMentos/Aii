import hashlib
import zlib
import pytest
from v13.source_slice import verified_source_slice


@pytest.mark.parametrize("compressed", [False, True])
def test_streamed_source_utf8_crosses_chunks_and_checks_full_hash(tmp_path, compressed):
    raw = ("x" * 65535 + "ä🙂" + "y" * 100000).encode()
    sha = hashlib.sha256(raw).hexdigest()
    path = tmp_path / "source"
    path.write_bytes(zlib.compress(raw) if compressed else raw)
    assert verified_source_slice(path, sha, 65535, 65538, compressed=compressed) == "ä🙂y"
    with pytest.raises(ValueError, match="Source-Hash"):
        verified_source_slice(path, "0" * 64, 65535, 65538, compressed=compressed)


def test_streamed_source_rejects_bad_archive_even_for_short_slice(tmp_path):
    path = tmp_path / "source.z"
    raw = b"hello world"
    path.write_bytes(zlib.compress(raw) + b"garbage")
    with pytest.raises(ValueError, match="zusätzliche"):
        verified_source_slice(path, hashlib.sha256(raw).hexdigest(), 0, 2, compressed=True)


def test_streamed_source_limit_and_range(tmp_path):
    raw = b"a" * 5000
    path = tmp_path / "source"
    path.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="zu groß"):
        verified_source_slice(path, sha, 0, 1, limit=1024)
    with pytest.raises(ValueError, match="außerhalb"):
        verified_source_slice(path, sha, 0, 5001)
    with pytest.raises(ValueError, match="außerhalb"):
        verified_source_slice(path, sha, -1, 2)


def test_store_read_source_uses_streamed_archived_slice(tmp_path):
    from v13.store import Store
    raw = ("V13 " + "ä🙂" * 20000).encode()
    sha = hashlib.sha256(raw).hexdigest()
    blobs = tmp_path / "data" / "blobs"
    blobs.mkdir(parents=True)
    (blobs / (sha + ".z")).write_bytes(zlib.compress(raw))
    store = Store.__new__(Store)
    store.home = tmp_path
    store.one = lambda query, args: {"hash": sha, "deleted": 0}
    assert store.read_source({"source_id":"src","sha256":sha,"char_start":4,"char_end":6}) == "ä🙂"
