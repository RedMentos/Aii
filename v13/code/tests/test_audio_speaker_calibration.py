import hashlib
import json
import random

import pytest

from v13.audio_speaker_calibration import (
    MANIFEST_SCHEMA,
    SpeakerCalibrationError,
    build_calibration_artifact,
    load_approved_calibration,
    validate_calibration_artifact,
)

MODEL = {
    "model_id": "fixture/campp-plus",
    "model_revision": "fixture-r1",
    "model_sha256": "a" * 64,
    "embedding_dim": 8,
    "frame_step_ms": 80,
    "lookback_frames": 10,
}
DATASET = {
    "dataset_id": "fixture-speaker-corpus",
    "dataset_revision": "fixture-r1",
    "dataset_license": "TEST_ONLY",
    "dataset_use_basis": "PUBLIC_DATASET_LICENSE",
    "dataset_authorization_ref": "d" * 64,
}
BINDING = {**MODEL}


def samples(*, noise=0.025, seed=7, leak=False):
    rng = random.Random(seed)
    rows = []
    for speaker in range(6):
        center = [0.0] * 8
        center[speaker] = 1.0
        for session in range(4):
            for utterance in range(2):
                vector = [value + rng.uniform(-noise, noise) for value in center]
                source = f"src-{speaker}-{session}-{utterance}"
                session_id = f"session-{speaker}-{session}"
                if leak and speaker >= 3 and session == 0:
                    source = "shared-source"
                    session_id = "shared-session"
                rows.append({
                    "sample_id": f"utt-{speaker}-{session}-{utterance}",
                    "source_id": source,
                    "session_id": session_id,
                    "speaker_id": f"spk-{speaker}",
                    "vector": vector,
                })
    return rows


def build(dataset_kind="SYNTHETIC_TEST", noise=0.025, seed=7, leak=False):
    return build_calibration_artifact(
        samples(noise=noise, seed=seed, leak=leak),
        **MODEL, **DATASET, dataset_kind=dataset_kind,
    )


def test_synthetic_report_fixture_is_model_and_temporal_bound_and_hash_stable():
    artifact = build()
    assert artifact["status"] == "HELDOUT_PASS"
    assert artifact["dataset_kind"] == "SYNTHETIC_TEST"
    assert artifact["source_disjoint"] is True
    assert artifact["session_disjoint"] is True
    assert artifact["speaker_disjoint"] is True
    assert artifact["heldout_metrics"]["false_accept_rate"] <= artifact["max_false_accept_rate"]
    assert artifact["heldout_metrics"]["false_reject_rate"] <= artifact["max_false_reject_rate"]
    assert validate_calibration_artifact(artifact, **BINDING, allow_synthetic_test=True) == artifact


def test_synthetic_report_never_becomes_runtime_eligible():
    artifact = build()
    assert artifact["status"] == "HELDOUT_PASS"
    with pytest.raises(SpeakerCalibrationError, match="real-local"):
        validate_calibration_artifact(artifact, **BINDING)


def test_source_or_session_leakage_across_speaker_splits_is_rejected():
    with pytest.raises(SpeakerCalibrationError, match="leakage"):
        build(leak=True)


def test_overlapping_embeddings_fail_the_heldout_gate():
    artifact = build(noise=0.85, seed=41)
    assert artifact["status"] == "HELDOUT_FAIL"
    with pytest.raises(SpeakerCalibrationError, match="held-out-passing"):
        validate_calibration_artifact(artifact, **BINDING, allow_synthetic_test=True)


def test_model_revision_or_temporal_mismatch_is_rejected():
    artifact = build()
    with pytest.raises(SpeakerCalibrationError, match="binding mismatch"):
        validate_calibration_artifact(artifact, **{**BINDING, "model_revision": "fixture-r2"}, allow_synthetic_test=True)
    with pytest.raises(SpeakerCalibrationError, match="binding mismatch"):
        validate_calibration_artifact(artifact, **{**BINDING, "lookback_frames": 9}, allow_synthetic_test=True)


def test_artifact_hash_tampering_is_rejected():
    artifact = build()
    tampered = dict(artifact, threshold=artifact["threshold"] - 0.1)
    with pytest.raises(SpeakerCalibrationError, match="hash mismatch"):
        validate_calibration_artifact(tampered, **BINDING, allow_synthetic_test=True)


def test_local_manifest_requires_exact_allowlisted_hash_and_model_binding(tmp_path):
    artifact = build(dataset_kind="REAL_LOCAL")
    root = tmp_path / "models" / "speaker_calibration"
    root.mkdir(parents=True)
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    (root / (artifact["calibration_id"] + ".json")).write_bytes(raw)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "entries": [{
            "calibration_id": artifact["calibration_id"],
            "artifact_sha256": hashlib.sha256(raw).hexdigest(),
            "enabled": True,
        }],
    }
    (root / "approved.json").write_text(json.dumps(manifest), encoding="utf-8")
    loaded = load_approved_calibration(tmp_path, artifact["calibration_id"], **BINDING)
    assert loaded["artifact_sha256"] == artifact["artifact_sha256"]

    manifest["entries"][0]["artifact_sha256"] = "0" * 64
    (root / "approved.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SpeakerCalibrationError, match="file hash mismatch"):
        load_approved_calibration(tmp_path, artifact["calibration_id"], **BINDING)


def test_disabled_or_missing_manifest_entry_stays_off(tmp_path):
    artifact = build(dataset_kind="REAL_LOCAL")
    root = tmp_path / "models" / "speaker_calibration"
    root.mkdir(parents=True)
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    (root / (artifact["calibration_id"] + ".json")).write_bytes(raw)
    manifest = {"schema": MANIFEST_SCHEMA, "entries": [{
        "calibration_id": artifact["calibration_id"],
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "enabled": False,
    }]}
    (root / "approved.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SpeakerCalibrationError, match="disabled"):
        load_approved_calibration(tmp_path, artifact["calibration_id"], **BINDING)


def test_duplicate_sample_ids_and_zero_vectors_fail_closed():
    data = samples()
    data[1]["sample_id"] = data[0]["sample_id"]
    with pytest.raises(SpeakerCalibrationError, match="duplicate"):
        build_calibration_artifact(data, **MODEL, **DATASET)
    data = samples()
    data[0]["vector"] = [0.0] * 8
    with pytest.raises(SpeakerCalibrationError, match="zero"):
        build_calibration_artifact(data, **MODEL, **DATASET)


def test_artifact_contains_no_embeddings_or_speaker_labels():
    artifact = build()
    serialized = json.dumps(artifact, sort_keys=True)
    assert '"vector"' not in serialized
    assert '"speaker_id"' not in serialized
    assert '"speaker_label"' not in serialized


def test_symlinked_model_root_and_artifact_are_rejected(tmp_path):
    artifact = build(dataset_kind="REAL_LOCAL")
    outside = tmp_path / "outside"
    outside.mkdir()
    models = tmp_path / "models"
    models.mkdir()
    (models / "speaker_calibration").symlink_to(outside, target_is_directory=True)
    with pytest.raises(SpeakerCalibrationError, match="unsafe"):
        load_approved_calibration(tmp_path, artifact["calibration_id"], **BINDING)

    root = models / "speaker_calibration"
    root.unlink()
    root.mkdir()
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    (outside / (artifact["calibration_id"] + ".json")).write_bytes(raw)
    (root / "approved.json").write_text(json.dumps({"schema": MANIFEST_SCHEMA, "entries": [{
        "calibration_id": artifact["calibration_id"],
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "enabled": True,
    }]}), encoding="utf-8")
    (root / (artifact["calibration_id"] + ".json")).symlink_to(outside / (artifact["calibration_id"] + ".json"))
    with pytest.raises(SpeakerCalibrationError, match="unsafe"):
        load_approved_calibration(tmp_path, artifact["calibration_id"], **BINDING)


def test_duplicate_manifest_ids_are_rejected(tmp_path):
    artifact = build(dataset_kind="REAL_LOCAL")
    root = tmp_path / "models" / "speaker_calibration"
    root.mkdir(parents=True)
    entry = {
        "calibration_id": artifact["calibration_id"],
        "artifact_sha256": "a" * 64,
        "enabled": True,
    }
    (root / "approved.json").write_text(json.dumps({
        "schema": MANIFEST_SCHEMA,
        "entries": [entry, dict(entry)],
    }), encoding="utf-8")
    with pytest.raises(SpeakerCalibrationError, match="duplicated"):
        load_approved_calibration(tmp_path, artifact["calibration_id"], **BINDING)
