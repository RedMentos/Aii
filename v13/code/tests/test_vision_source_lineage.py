"""Pure filesystem/lineage tests for the shadow vision source-forget contract."""
import os

from v13.vision_source_lineage import (
    invalidate_projectors, projector_uses_source, source_lineage,
    unlink_projector_artifact, unlink_source_blob,
)


def test_training_keys_are_bound_to_live_source_hashes():
    images = {
        "src_a": {"ref": {"source_id": "src_a", "sha256": "a" * 64}},
        "src_b": {"ref": {"source_id": "src_b", "sha256": "b" * 64}},
    }
    assert source_lineage(images, ["src_b:r00", "src_a:g", "src_b:r01"]) == [
        {"source_id": "src_a", "sha256": "a" * 64},
        {"source_id": "src_b", "sha256": "b" * 64},
    ]


def test_training_lineage_rejects_unknown_or_malformed_source():
    import pytest
    with pytest.raises(ValueError):
        source_lineage({}, ["missing:g"])
    with pytest.raises(ValueError):
        source_lineage({"src_a": {"ref": {"source_id": "src_b", "sha256": "a" * 64}}}, ["src_a:g"])


def test_invalidation_is_selective_and_legacy_fails_closed():
    state = {
        "projector": {"training_sources": [{"source_id": "src_a", "sha256": "a" * 64}], "captions": {}},
        "tile_projector": {"training_sources": [{"source_id": "src_b", "sha256": "b" * 64}]},
    }
    invalidated = invalidate_projectors(state, "src_a")
    assert [key for key, _ in invalidated] == ["projector"]
    assert state["projector"] is None
    assert state["tile_projector"] is not None
    assert projector_uses_source({"path": "legacy.npz"}, "src_a") is True


def test_caption_lineage_cannot_be_hidden_by_an_inconsistent_source_list():
    record = {
        "training_sources": [{"source_id": "src_b", "sha256": "b" * 64}],
        "captions": {"src_a:r00": "teacher reference"},
    }
    assert projector_uses_source(record, "src_a") is True


def test_safe_unlink_removes_only_expected_artifacts(tmp_path):
    home = tmp_path
    vision_dir = home / "data" / "vision"
    blob_dir = home / "data" / "blobs"
    vision_dir.mkdir(parents=True)
    blob_dir.mkdir(parents=True)
    projector = vision_dir / "tiles-test.npz"
    projector.write_bytes(b"weights")
    sha = "c" * 64
    blob = blob_dir / sha
    blob.write_bytes(b"image")
    assert unlink_projector_artifact(home, {"path": "data/vision/tiles-test.npz"}) is True
    assert unlink_source_blob(home, sha) is True
    assert not projector.exists()
    assert not blob.exists()


def test_safe_unlink_rejects_symlinked_parent_without_touching_outside_file(tmp_path):
    if not hasattr(os, "symlink"):
        return
    home = tmp_path
    (home / "data").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "projector-escape.npz"
    target.write_bytes(b"must survive")
    (home / "data" / "vision").symlink_to(outside, target_is_directory=True)
    assert unlink_projector_artifact(home, {"path": "data/vision/projector-escape.npz"}) is False
    assert target.read_bytes() == b"must survive"


def test_blob_unlink_rejects_bad_hash_and_path_traversal(tmp_path):
    assert unlink_source_blob(tmp_path, "../" + "a" * 64) is False
    assert unlink_projector_artifact(tmp_path, {"path": "data/vision/../../escape.npz"}) is False


def test_exact_source_stats_must_match_every_projector_source():
    lineage = [
        {"source_id": "src_a", "sha256": "a" * 64},
        {"source_id": "src_b", "sha256": "b" * 64},
    ]
    stats = [
        {"source_id": "src_a", "source_sha256": "a" * 64,
         "path": "data/vision/projector-stats-a.npz", "sha256": "c" * 64, "n": 4},
        {"source_id": "src_b", "source_sha256": "b" * 64,
         "path": "data/vision/projector-stats-b.npz", "sha256": "d" * 64, "n": 4},
    ]
    valid = {"training_sources": lineage, "source_stats_mode": "EXACT_SOURCE_STATS_V1",
             "source_stats": stats}
    assert projector_uses_source(valid, "src_c") is False
    assert projector_uses_source(valid, "src_a") is True

    missing = dict(valid, source_stats=stats[:1])
    assert projector_uses_source(missing, "src_c") is True
    malformed = dict(valid, source_stats=[dict(stats[0], path="data/vision/../../outside.npz"), stats[1]])
    assert projector_uses_source(malformed, "src_c") is True

    capped = {"training_sources": lineage, "source_stats_mode": "SOURCE_CAP_EXCEEDED",
              "source_stats": []}
    assert projector_uses_source(capped, "src_a") is True
    assert projector_uses_source(capped, "src_c") is False
