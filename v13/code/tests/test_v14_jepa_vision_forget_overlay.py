"""JEPA source-lifecycle overlay must revoke every projector trained on a forgotten image."""
import hashlib
import time

import pytest

from v13 import source_lifecycle_candidate as lifecycle
from v13 import vision
from v13.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    value = Runtime(tmp_path)
    value.sleep.cycle.set_policy("enabled", "off")
    try:
        yield value
    finally:
        value.close()


def _ppm(seed):
    pixels = []
    for index in range(16 * 16):
        pixels.append(f"{(seed + index) % 256} {(seed * 3 + index * 7) % 256} {(seed * 5 + index * 11) % 256}")
    return ("P3\n16 16\n255\n" + "\n".join(pixels) + "\n").encode("ascii")


def _install_projector(runtime, state, key, filename, training_sources, captions=None):
    directory = runtime.home / "data" / "vision"
    directory.mkdir(parents=True, exist_ok=True)
    artifact = directory / filename
    payload = ("synthetic-" + filename).encode("ascii")
    artifact.write_bytes(payload)
    record = {
        "path": str(artifact.relative_to(runtime.home)),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "n": 2,
        "encoder": "synthetic-fixture",
        "created": time.time(),
        "training_sources": training_sources,
        "authority": "LAB_SHADOW_ONLY",
    }
    if key == "projector":
        record["captions"] = captions or {}
    state[key] = record
    return artifact, record


def test_forget_revokes_global_and_tile_projectors_and_cleans_artifacts(runtime):
    rec = vision.ingest(runtime.store, _ppm(3))
    sid, sha = rec["ref"]["source_id"], rec["ref"]["sha256"]
    state = vision.load(runtime.store)
    global_path, _ = _install_projector(
        runtime, state, "projector", "projector-forget.npz",
        [{"source_id": sid, "sha256": sha}], {sid + ":g": "synthetic caption"},
    )
    tile_path, _ = _install_projector(
        runtime, state, "tile_projector", "tiles-forget.npz",
        [{"source_id": sid, "sha256": sha}],
    )
    vision.save(runtime.store, state)

    result = lifecycle.vision_forget(runtime.store, rec)
    after = vision.load(runtime.store)
    source = runtime.store.one("SELECT deleted FROM sources WHERE id=?", (sid,))
    blob = runtime.home / "data" / "blobs" / sha

    assert result["invalidated_projectors"] == ["projector", "tile_projector"]
    assert after["projector"] is None and after["tile_projector"] is None
    assert result["projector_files_deleted"] == {"projector": True, "tile_projector": True}
    assert not global_path.exists() and not tile_path.exists()
    assert source["deleted"] == 1
    assert result["blob_deleted"] is True and not blob.exists()
    assert result["cleanup_failed"] == []
    assert after.get("pending_projector_cleanup") == []


def test_forget_invalidates_unknown_legacy_lineage_but_preserves_proven_disjoint_tile(runtime):
    forgotten = vision.ingest(runtime.store, _ppm(7))
    retained = vision.ingest(runtime.store, _ppm(19))
    sid, sha = forgotten["ref"]["source_id"], forgotten["ref"]["sha256"]
    retained_sid, retained_sha = retained["ref"]["source_id"], retained["ref"]["sha256"]
    state = vision.load(runtime.store)
    legacy_path, _ = _install_projector(
        runtime, state, "projector", "projector-legacy.npz",
        [], {sid + ":g": "legacy caption"},
    )
    tile_path, tile_record = _install_projector(
        runtime, state, "tile_projector", "tiles-disjoint.npz",
        [{"source_id": retained_sid, "sha256": retained_sha}],
    )
    # Empty/legacy lineage is unknown and must fail closed.
    state["projector"].pop("training_sources", None)
    vision.save(runtime.store, state)

    result = lifecycle.vision_forget(runtime.store, forgotten)
    after = vision.load(runtime.store)

    assert result["invalidated_projectors"] == ["projector"]
    assert after["projector"] is None
    assert after["tile_projector"] == tile_record
    assert not legacy_path.exists() and tile_path.exists()
    assert not (runtime.home / "data" / "blobs" / sha).exists()
    assert (runtime.home / "data" / "blobs" / retained_sha).exists()
    assert result["cleanup_failed"] == []


def test_forget_keeps_failed_projector_cleanup_durable_and_retries(runtime, monkeypatch):
    from v13 import vision_source_lineage

    rec = vision.ingest(runtime.store, _ppm(31))
    sid, sha = rec["ref"]["source_id"], rec["ref"]["sha256"]
    state = vision.load(runtime.store)
    artifact, _ = _install_projector(
        runtime, state, "projector", "projector-retry.npz",
        [{"source_id": sid, "sha256": sha}], {sid + ":g": "synthetic caption"},
    )
    vision.save(runtime.store, state)

    original = vision_source_lineage.unlink_projector_artifact
    calls = {"n": 0}

    def fail_once(home, record):
        calls["n"] += 1
        if calls["n"] == 1:
            return False
        return original(home, record)

    monkeypatch.setattr(vision_source_lineage, "unlink_projector_artifact", fail_once)
    first = lifecycle.vision_forget(runtime.store, rec)
    pending = vision.load(runtime.store).get("pending_projector_cleanup")

    assert first["cleanup_failed"] == ["projector_artifact"]
    assert pending and pending[0]["source_id"] == sid
    assert artifact.exists()

    second = lifecycle.vision_forget(runtime.store, rec)
    after = vision.load(runtime.store)
    assert second["cleanup_failed"] == []
    assert second["projector_files_deleted"] == {"projector": True}
    assert not artifact.exists()
    assert after.get("pending_projector_cleanup") == []


def test_forget_retains_blob_still_referenced_by_another_live_source(runtime):
    data = _ppm(43)
    rec = vision.ingest(runtime.store, data)
    sid, sha = rec["ref"]["source_id"], rec["ref"]["sha256"]
    with runtime.store.tx() as conn:
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,0)",
            ("src_shared_test", sha, "USER", len(data), len(data), time.time()),
        )

    result = lifecycle.vision_forget(runtime.store, rec)
    assert runtime.store.one("SELECT deleted FROM sources WHERE id=?", (sid,))["deleted"] == 1
    assert result["blob_retained_shared"] is True
    assert result["blob_deleted"] is False
    assert (runtime.home / "data" / "blobs" / sha).exists()
