"""FASTDIAR adapter and RAW EAR A5→A4→C3 consumer regressions."""
from contextlib import contextmanager
import hashlib
import json
import math
import struct
from types import SimpleNamespace

import pytest

from v13.audio_fastdiar_adapter import (
    EMBEDDING_DIM,
    FRAME_STEP_MS,
    LOOKBACK_FRAMES,
    MODEL_ID,
    MODEL_REVISION,
    build_fastdiar_diagnostic_batch,
)
from v13.audio_speaker_evidence import SCHEMA
from v13.audio_voice_cues import consume_pcm16_voice_window
from v13.store import Store


SOURCE = "fixture:fastdiar-source"
RECEIPT = "fixture:fastdiar-consent"


class NumpyLikeMatrix:
    """Minimal stand-in for ndarray.tolist(); no NumPy runtime dependency."""

    def __init__(self, rows):
        self.rows = rows

    def tolist(self):
        return self.rows


def vector_a():
    return [1.0] + [0.0] * (EMBEDDING_DIM - 1)


def vector_b():
    return [0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2)


def matrix(rows):
    return NumpyLikeMatrix(rows)


def make_checkpoint(tmp_path, payload=b"synthetic FASTDIAR checkpoint fixture"):
    root = tmp_path / "models"
    model_dir = root / "fastdiar"
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / "checkpoint.bin"
    path.write_bytes(payload)
    return root, path, hashlib.sha256(payload).hexdigest()


def make_batch(rows, *, start_ms, end_ms, first_end_ms, checkpoint_root,
               checkpoint_path, generation_id="gen-a", model_revision=MODEL_REVISION,
               consent_receipt_ref=RECEIPT, current_chunk_sha256=None):
    if current_chunk_sha256 is None:
        current_chunk_sha256 = hashlib.sha256(tone()).hexdigest()
    return build_fastdiar_diagnostic_batch(
        matrix(rows),
        source_id=SOURCE,
        generation_id=generation_id,
        consent_receipt_ref=consent_receipt_ref,
        current_chunk_sha256=current_chunk_sha256,
        model_revision=model_revision,
        checkpoint_path=checkpoint_path,
        checkpoint_root=checkpoint_root,
        window_start_ms=start_ms,
        window_end_ms=end_ms,
        first_frame_end_ms=first_end_ms,
    )


def tone(sample_rate=16000, frequency=140, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [
        int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
        for i in range(count)
    ]
    return struct.pack("<" + "h" * len(samples), *samples)


def make_runtime(tmp_path):
    (tmp_path / "data" / "db").mkdir(parents=True)
    store = Store(tmp_path)
    store.ensure_generation_snapshot({}, {})
    session = store.new_session("FASTDIAR adapter consumer test")
    event = store.event(session, "synthetic frame-embedding fixture")
    return SimpleNamespace(home=tmp_path, store=store), event


def consent_ok(source_id, receipt):
    return source_id == SOURCE and receipt == RECEIPT


def consent_guard(check):
    @contextmanager
    def lease(source_id, receipt):
        yield check(source_id, receipt)
    return lease


def test_adapter_emits_exact_raw_ear_schema_and_fastdiar_geometry(tmp_path):
    root, checkpoint, expected_sha = make_checkpoint(tmp_path)
    rows = [vector_a() for _ in range(12)]
    batch = make_batch(
        rows, start_ms=100, end_ms=1100, first_end_ms=180,
        checkpoint_root=root, checkpoint_path=checkpoint,
    )
    assert set(batch) == {
        "schema", "source_id", "generation_id", "model_id", "model_revision",
        "model_sha256", "consent_receipt_ref", "current_chunk_sha256", "embedding_dim", "frame_step_ms",
        "lookback_frames", "confidence_threshold", "calibration_id", "frames",
    }
    assert batch["schema"] == SCHEMA
    assert batch["model_id"] == MODEL_ID
    assert batch["model_revision"] == MODEL_REVISION
    assert batch["model_sha256"] == expected_sha
    assert batch["current_chunk_sha256"] == hashlib.sha256(tone()).hexdigest()
    assert batch["consent_receipt_ref"] == RECEIPT
    assert batch["embedding_dim"] == EMBEDDING_DIM == 192
    assert batch["frame_step_ms"] == FRAME_STEP_MS == 80
    assert batch["lookback_frames"] == LOOKBACK_FRAMES == 10
    assert batch["confidence_threshold"] is None
    assert batch["calibration_id"] is None
    assert len(batch["frames"]) == 12
    assert batch["frames"][0]["end_ms"] == 180
    assert batch["frames"][-1]["end_ms"] == 1060


def test_actual_numpy_float16_matrix_is_accepted(tmp_path):
    numpy = pytest.importorskip("numpy")
    root, checkpoint, _ = make_checkpoint(tmp_path)
    rows = numpy.asarray([vector_a() for _ in range(12)], dtype=numpy.float16)
    batch = build_fastdiar_diagnostic_batch(
        rows, source_id=SOURCE, generation_id="gen-a",
        consent_receipt_ref=RECEIPT,
        current_chunk_sha256=hashlib.sha256(tone()).hexdigest(),
        model_revision=MODEL_REVISION,
        checkpoint_path=checkpoint, checkpoint_root=root,
        window_start_ms=100, window_end_ms=1100, first_frame_end_ms=180,
    )
    assert len(batch["frames"]) == 12
    assert len(batch["frames"][0]["vector"]) == 192


def test_adapter_rejects_noncanonical_current_chunk_sha256(tmp_path):
    root, checkpoint, _ = make_checkpoint(tmp_path)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        build_fastdiar_diagnostic_batch(
            matrix([vector_a()]), source_id=SOURCE, generation_id="gen-a",
            consent_receipt_ref=RECEIPT,
            current_chunk_sha256="A" * 64, model_revision=MODEL_REVISION,
            checkpoint_path=checkpoint, checkpoint_root=root,
            window_start_ms=100, window_end_ms=300, first_frame_end_ms=180,
        )


def test_adapter_rejects_missing_or_unbounded_consent_receipt(tmp_path):
    root, checkpoint, _ = make_checkpoint(tmp_path)
    common = {
        "source_id": SOURCE,
        "generation_id": "gen-a",
        "current_chunk_sha256": hashlib.sha256(tone()).hexdigest(),
        "model_revision": MODEL_REVISION,
        "checkpoint_path": checkpoint,
        "checkpoint_root": root,
        "window_start_ms": 100,
        "window_end_ms": 300,
        "first_frame_end_ms": 180,
    }
    with pytest.raises(ValueError, match="consent_receipt_ref"):
        build_fastdiar_diagnostic_batch(
            matrix([vector_a()]), consent_receipt_ref="", **common,
        )
    with pytest.raises(ValueError, match="consent_receipt_ref"):
        build_fastdiar_diagnostic_batch(
            matrix([vector_a()]), consent_receipt_ref="x" * 257, **common,
        )


def test_adapter_rejects_bad_dimensions_nonfinite_and_boolean_values(tmp_path):
    root, checkpoint, _ = make_checkpoint(tmp_path)
    args = {"checkpoint_root": root, "checkpoint_path": checkpoint}
    with pytest.raises(ValueError, match="192"):
        make_batch([[1.0] * 191], start_ms=100, end_ms=1100, first_end_ms=180, **args)
    invalid = [1.0] * 192
    invalid[7] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        make_batch([invalid], start_ms=100, end_ms=1100, first_end_ms=180, **args)
    invalid_bool = [1.0] * 192
    invalid_bool[4] = True
    with pytest.raises(ValueError, match="numeric scalars"):
        make_batch([invalid_bool], start_ms=100, end_ms=1100, first_end_ms=180, **args)


def test_adapter_rejects_unbounded_batches_bad_revision_and_timestamp_overflow(tmp_path):
    root, checkpoint, _ = make_checkpoint(tmp_path)
    args = {"checkpoint_root": root, "checkpoint_path": checkpoint}
    with pytest.raises(ValueError, match="1..32"):
        make_batch([], start_ms=100, end_ms=1100, first_end_ms=180, **args)
    with pytest.raises(ValueError, match="1..32"):
        make_batch([vector_a() for _ in range(33)], start_ms=100, end_ms=4000, first_end_ms=180, **args)
    with pytest.raises(ValueError, match="pinned"):
        make_batch([vector_a()], start_ms=100, end_ms=1100, first_end_ms=180,
                   model_revision="main", **args)
    with pytest.raises(ValueError, match="exceed"):
        make_batch([vector_a() for _ in range(12)], start_ms=100, end_ms=1100, first_end_ms=1080, **args)


def test_checkpoint_hash_rejects_outside_paths_empty_files_and_symlinks(tmp_path):
    root, checkpoint, _ = make_checkpoint(tmp_path)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    with pytest.raises(ValueError, match="unsafe"):
        make_batch([vector_a()], start_ms=100, end_ms=300, first_end_ms=180,
                   checkpoint_root=root, checkpoint_path=outside)

    empty = root / "fastdiar" / "empty.bin"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="size"):
        make_batch([vector_a()], start_ms=100, end_ms=300, first_end_ms=180,
                   checkpoint_root=root, checkpoint_path=empty)

    link = root / "fastdiar" / "link.bin"
    try:
        link.symlink_to(checkpoint)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this test platform")
    with pytest.raises(ValueError, match="unsafe"):
        make_batch([vector_a()], start_ms=100, end_ms=300, first_end_ms=180,
                   checkpoint_root=root, checkpoint_path=link)


def test_checkpoint_hash_rejects_symlinked_parent_directory(tmp_path):
    root, _, _ = make_checkpoint(tmp_path)
    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    (outside_dir / "checkpoint.bin").write_bytes(b"outside")
    link_dir = root / "redirect"
    try:
        link_dir.symlink_to(outside_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this test platform")
    with pytest.raises(ValueError, match="unsafe"):
        make_batch([vector_a()], start_ms=100, end_ms=300, first_end_ms=180,
                   checkpoint_root=root, checkpoint_path=link_dir / "checkpoint.bin")


def test_fastdiar_current_chunk_hash_mismatch_is_rejected_by_real_consumer(tmp_path):
    runtime, event = make_runtime(tmp_path)
    root, checkpoint, _ = make_checkpoint(tmp_path)
    generation = event["brain_generation_id"]
    wrong_pcm = tone(frequency=220)
    batch = make_batch(
        [vector_a() for _ in range(12)],
        start_ms=100, end_ms=1100, first_end_ms=180,
        checkpoint_root=root, checkpoint_path=checkpoint,
        generation_id=generation,
        current_chunk_sha256=hashlib.sha256(wrong_pcm).hexdigest(),
    )
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=generation,
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=batch,
        )
        evidence = result["speaker_change_evidence"]
        assert evidence["status"] == "REJECTED"
        assert evidence["error"] == "SpeakerEvidenceError"
        assert result["a4"]["speaker_change_decision"] == "DEFER"
        assert "speaker_similarity_delta=" not in result["c3_admission"].selected[0].summary
        assert "vector" not in json.dumps(result["packet"])
    finally:
        runtime.store.close()


def test_fastdiar_matrix_reaches_real_raw_ear_a5_a4_c3_consumer_without_identity(tmp_path):
    runtime, event = make_runtime(tmp_path)
    root, checkpoint, _ = make_checkpoint(tmp_path)
    generation = event["brain_generation_id"]
    try:
        first = make_batch(
            [vector_a() for _ in range(12)],
            start_ms=100, end_ms=1100, first_end_ms=180,
            checkpoint_root=root, checkpoint_path=checkpoint,
            generation_id=generation,
        )
        warmup = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=generation,
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=first,
        )
        assert warmup["a4"]["speaker_change_decision"] == "DEFER"

        changed_rows = [vector_a() for _ in range(6)] + [vector_b() for _ in range(6)]
        second = make_batch(
            changed_rows,
            start_ms=1100, end_ms=2100, first_end_ms=1180,
            checkpoint_root=root, checkpoint_path=checkpoint,
            generation_id=generation,
        )
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=1100,
            event_id=event["event_id"], generation_id=generation,
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=second,
        )
        evidence = result["speaker_change_evidence"]
        assert evidence["status"] == "MEASURED"
        assert evidence["source_binding_status"] == "CURRENT_PCM_CHUNK_SHA256_MATCH"
        assert evidence["current_chunk_sha256"] == hashlib.sha256(tone()).hexdigest()
        assert evidence["threshold_status"] == "NOT_CONFIGURED"
        assert evidence["speaker_label"] is None
        assert evidence["identity_authority"] is False
        assert result["a4"]["speaker_change_decision"] == "DEFER"
        assert result["a4"]["learning_authority"] is False
        assert result["a4"]["action_authority"] is False
        summary = result["c3_admission"].selected[0].summary
        assert "speaker_similarity_delta=0.50" in summary
        assert "spk_cal=UNAVAILABLE" in summary
        assert "spk_dec=DEFER" in summary
        persisted = json.dumps(result["packet"], sort_keys=True)
        assert '"vector"' not in persisted
        assert '"speaker_label": null' in persisted
    finally:
        runtime.store.close()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
