"""FASTDIAR adapter and RAW EAR A5→A4→C3 consumer regressions."""
from contextlib import contextmanager
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
MODEL_SHA = "a" * 64


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


def make_batch(rows, *, start_ms, end_ms, first_end_ms, generation_id="gen-a"):
    return build_fastdiar_diagnostic_batch(
        matrix(rows),
        source_id=SOURCE,
        generation_id=generation_id,
        model_revision=MODEL_REVISION,
        model_sha256=MODEL_SHA,
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


def test_adapter_emits_exact_raw_ear_schema_and_fastdiar_geometry():
    rows = [vector_a() for _ in range(12)]
    batch = make_batch(rows, start_ms=100, end_ms=1100, first_end_ms=180)
    assert set(batch) == {
        "schema", "source_id", "generation_id", "model_id", "model_revision",
        "model_sha256", "embedding_dim", "frame_step_ms", "lookback_frames",
        "confidence_threshold", "calibration_id", "frames",
    }
    assert batch["schema"] == SCHEMA
    assert batch["model_id"] == MODEL_ID
    assert batch["model_revision"] == MODEL_REVISION
    assert batch["embedding_dim"] == EMBEDDING_DIM == 192
    assert batch["frame_step_ms"] == FRAME_STEP_MS == 80
    assert batch["lookback_frames"] == LOOKBACK_FRAMES == 10
    assert batch["confidence_threshold"] is None
    assert batch["calibration_id"] is None
    assert len(batch["frames"]) == 12
    assert batch["frames"][0]["end_ms"] == 180
    assert batch["frames"][-1]["end_ms"] == 1060


def test_actual_numpy_float16_matrix_is_accepted():
    numpy = pytest.importorskip("numpy")
    rows = numpy.asarray([vector_a() for _ in range(12)], dtype=numpy.float16)
    batch = build_fastdiar_diagnostic_batch(
        rows, source_id=SOURCE, generation_id="gen-a",
        model_revision=MODEL_REVISION, model_sha256=MODEL_SHA,
        window_start_ms=100, window_end_ms=1100, first_frame_end_ms=180,
    )
    assert len(batch["frames"]) == 12
    assert len(batch["frames"][0]["vector"]) == 192


def test_adapter_rejects_bad_dimensions_nonfinite_and_boolean_values():
    with pytest.raises(ValueError, match="192"):
        make_batch([[1.0] * 191], start_ms=100, end_ms=1100, first_end_ms=180)
    invalid = [1.0] * 192
    invalid[7] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        make_batch([invalid], start_ms=100, end_ms=1100, first_end_ms=180)
    invalid_bool = [1.0] * 192
    invalid_bool[4] = True
    with pytest.raises(ValueError, match="numeric scalars"):
        make_batch([invalid_bool], start_ms=100, end_ms=1100, first_end_ms=180)


def test_adapter_rejects_unbounded_batches_bad_hash_revision_and_timestamp_overflow():
    with pytest.raises(ValueError, match="1..32"):
        make_batch([], start_ms=100, end_ms=1100, first_end_ms=180)
    with pytest.raises(ValueError, match="1..32"):
        make_batch([vector_a() for _ in range(33)], start_ms=100, end_ms=4000, first_end_ms=180)
    with pytest.raises(ValueError, match="SHA256"):
        build_fastdiar_diagnostic_batch(
            matrix([vector_a()]), source_id=SOURCE, generation_id="gen-a",
            model_revision=MODEL_REVISION, model_sha256="bad",
            window_start_ms=100, window_end_ms=1100, first_frame_end_ms=180,
        )
    with pytest.raises(ValueError, match="pinned"):
        build_fastdiar_diagnostic_batch(
            matrix([vector_a()]), source_id=SOURCE, generation_id="gen-a",
            model_revision="main", model_sha256=MODEL_SHA,
            window_start_ms=100, window_end_ms=1100, first_frame_end_ms=180,
        )
    with pytest.raises(ValueError, match="exceed"):
        make_batch([vector_a() for _ in range(12)], start_ms=100, end_ms=1100, first_end_ms=1080)


def test_fastdiar_matrix_reaches_real_raw_ear_a5_a4_c3_consumer_without_identity(tmp_path):
    runtime, event = make_runtime(tmp_path)
    generation = event["brain_generation_id"]
    try:
        first = make_batch(
            [vector_a() for _ in range(12)],
            start_ms=100, end_ms=1100, first_end_ms=180,
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
