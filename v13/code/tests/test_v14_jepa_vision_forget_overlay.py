"""JEPA source-lifecycle overlay must revoke every projector trained on a forgotten image."""
import hashlib
import io
import threading
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



@pytest.fixture
def staged_vision(runtime, monkeypatch):
    """Mirror the exact vision wrappers installed by the staged lifecycle composer."""
    monkeypatch.setattr(vision, "load", lifecycle.load_vision_state)
    monkeypatch.setattr(vision, "save", lifecycle.save_vision_state)
    monkeypatch.setattr(vision, "ingest", lifecycle.vision_ingest)
    monkeypatch.setattr(vision, "forget", lifecycle.vision_forget)
    return runtime


def _png(colour, box=(10, 10, 40, 40), size=(64, 48)):
    from PIL import Image, ImageDraw
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).rectangle(box, fill=colour)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class _FakeTeacher:
    def describe(self, image, prompt=vision.PROMPT, cancel=None):
        np = vision._np()
        pixels = np.asarray(image).reshape(-1, 3)
        if pixels.mean() > 250:
            caption = "an empty white area"
        else:
            red, green, blue = pixels.min(0)
            name = ("red" if red > 150 and green < 100 else
                    "blue" if blue > 150 and red < 100 else "green")
            caption = "a %s box on white" % name
        return {
            "text": caption,
            "authority": vision.AUTHORITY,
            "teacher": "synthetic-test-only",
            "revision": None,
            "prompt": prompt,
            "seconds": 0.0,
        }


@pytest.mark.parametrize("projector_key", ["projector", "tile_projector"])
@pytest.mark.parametrize("bad_reference", ["missing_source", "mismatched_hash"])
def test_save_rejects_non_live_training_lineage_for_both_projectors(
    runtime, projector_key, bad_reference
):
    rec = vision.ingest(runtime.store, _ppm(59))
    source_id = rec["ref"]["source_id"]
    source_sha = rec["ref"]["sha256"]
    if bad_reference == "missing_source":
        bad_id = "src_missing_vision_lineage_test"
        bad_sha = "a" * 64
    else:
        bad_id = source_id
        bad_sha = "f" * 64 if source_sha != "f" * 64 else "e" * 64

    state = lifecycle.load_vision_state(runtime.store)
    projector = {
        "training_sources": [{"source_id": bad_id, "sha256": bad_sha}],
        "authority": "LAB_SHADOW_ONLY",
    }
    if projector_key == "projector":
        projector["captions"] = {}
    state[projector_key] = projector

    with pytest.raises(ValueError, match="lineage"):
        lifecycle.save_vision_state(runtime.store, state)


def test_staged_versioned_snapshot_cannot_overwrite_a_completed_forget(staged_vision):
    rec = vision.ingest(staged_vision.store, _ppm(61))
    stale = vision.load(staged_vision.store)
    vision.forget(staged_vision.store, rec)
    stale["teacher_removed"] = True

    with pytest.raises(ValueError, match="Stale state write"):
        vision.save(staged_vision.store, stale)
    current = vision.load(staged_vision.store)
    assert rec["ref"]["source_id"] not in current["images"]
    assert not current.get("teacher_removed", False)


def _assert_training_commit_rejected_after_forget(runtime, monkeypatch, trainer, state_key, prefix):
    np = vision._np()
    teacher = _FakeTeacher()
    encoder = ("hashed_bow", lambda texts: np.stack([vision.hashed_embed(value) for value in texts]))
    records = []
    colours = [(220, 20, 20), (20, 20, 220), (20, 180, 20)] * 2
    for index, colour in enumerate(colours):
        record = vision.ingest(
            runtime.store, _png(colour, box=(5 + index, 5, 30 + index, 30))
        )
        for region in ("g", "qtl", "qtr"):
            vision.describe(runtime, record, region, teacher)
        records.append(record)

    entered = threading.Event()
    release = threading.Event()
    outcome = {}
    original_save = vision.save

    def delayed_save(store, state):
        entered.set()
        if not release.wait(30):
            raise TimeoutError("test did not release delayed vision save")
        return original_save(store, state)

    monkeypatch.setattr(vision, "save", delayed_save)

    def train_worker():
        try:
            outcome["result"] = trainer(runtime, encoder)
        except BaseException as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=train_worker)
    worker.start()
    assert entered.wait(30), "training never reached its state commit"
    vision.forget(runtime.store, records[-1])
    release.set()
    worker.join(30)

    assert not worker.is_alive(), "training worker did not finish"
    assert isinstance(outcome.get("error"), ValueError)
    assert "Stale state write" in str(outcome["error"])
    assert vision.load(runtime.store).get(state_key) is None
    assert list((runtime.home / "data" / "vision").glob(prefix + "*.npz")) == []


@pytest.mark.parametrize(
    ("trainer", "state_key", "prefix"),
    [
        (vision.train, "projector", "projector-"),
        (vision.train_tiles, "tile_projector", "tiles-"),
    ],
)
def test_global_and_tile_training_cannot_publish_after_source_forget(
    staged_vision, monkeypatch, trainer, state_key, prefix
):
    _assert_training_commit_rejected_after_forget(
        staged_vision, monkeypatch, trainer, state_key, prefix
    )


def test_reingest_waits_for_last_source_blob_cleanup_under_store_lock(staged_vision, monkeypatch):
    data = _ppm(67)
    original = vision.ingest(staged_vision.store, data)
    source_sha = original["ref"]["sha256"]
    cleanup_entered = threading.Event()
    release_cleanup = threading.Event()
    ingest_started = threading.Event()
    ingest_done = threading.Event()
    forget_result = {}
    ingest_result = {}
    original_cleanup = lifecycle._cleanup_pending_fd

    def delayed_cleanup(dir_fd, key=None):
        if key == source_sha and not cleanup_entered.is_set():
            cleanup_entered.set()
            if not release_cleanup.wait(30):
                raise TimeoutError("test did not release Store-locked blob cleanup")
        return original_cleanup(dir_fd, key)

    monkeypatch.setattr(lifecycle, "_cleanup_pending_fd", delayed_cleanup)

    def forget_worker():
        try:
            forget_result["result"] = vision.forget(staged_vision.store, original)
        except BaseException as exc:
            forget_result["error"] = exc

    def ingest_worker():
        ingest_started.set()
        try:
            ingest_result["record"] = vision.ingest(staged_vision.store, data)
        except BaseException as exc:
            ingest_result["error"] = exc
        finally:
            ingest_done.set()

    forget_thread = threading.Thread(target=forget_worker)
    forget_thread.start()
    assert cleanup_entered.wait(30), "forget did not enter Store-locked blob cleanup"
    ingest_thread = threading.Thread(target=ingest_worker)
    ingest_thread.start()
    assert ingest_started.wait(2)
    time.sleep(0.05)
    assert not ingest_done.is_set(), "re-ingest crossed the active Store cleanup lock"

    release_cleanup.set()
    forget_thread.join(30)
    ingest_thread.join(30)

    assert not forget_thread.is_alive()
    assert not ingest_thread.is_alive()
    assert "error" not in forget_result, str(forget_result.get("error"))
    assert "error" not in ingest_result, str(ingest_result.get("error"))
    assert forget_result["result"]["blob_deleted"] is True
    recreated = ingest_result["record"]
    assert recreated["ref"]["source_id"] != original["ref"]["source_id"]
    row = staged_vision.store.one(
        "SELECT hash,kind,deleted FROM sources WHERE id=?",
        (recreated["ref"]["source_id"],),
    )
    assert row["kind"] == "IMAGE" and row["hash"] == source_sha and row["deleted"] == 0
    blob = staged_vision.home / "data" / "blobs" / source_sha
    assert blob.is_file()
    assert hashlib.sha256(blob.read_bytes()).hexdigest() == source_sha
