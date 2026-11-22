"""Synthetic and consumer tests for source-bound speaker-change evidence."""
from contextlib import contextmanager
import json
import math
import struct
from types import SimpleNamespace

import pytest

from v13.audio_speaker_evidence import (
    SCHEMA, SpeakerChangeEvidenceRegistry, SpeakerEvidenceError,
)
from v13 import audio_voice_cues as audio_voice_module
from v13.audio_voice_cues import (
    _runtime_speaker_evidence_registry,
    consume_pcm16_voice_window,
    reset_runtime_temporal_voice_states,
)
from v13.store import Store


SOURCE = "fixture:raw-ear-speaker"
RECEIPT = "fixture:consented-speaker"
MODEL_SHA = "a" * 64


def tone(sample_rate=16000, frequency=140, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
               for i in range(count)]
    return struct.pack("<" + "h" * len(samples), *samples)


def make_runtime(tmp_path):
    (tmp_path / "data" / "db").mkdir(parents=True)
    store = Store(tmp_path)
    store.ensure_generation_snapshot({}, {})
    session = store.new_session("RAW EAR speaker evidence test")
    event = store.event(session, "synthetic speaker embedding fixture")
    return SimpleNamespace(home=tmp_path, store=store), event


def consent_ok(source_id, receipt):
    return source_id == SOURCE and receipt == RECEIPT


def consent_guard(check):
    @contextmanager
    def lease(source_id, receipt):
        yield check(source_id, receipt)
    return lease


def speaker_batch(source_id, generation_id, start_ms, end_ms, vector_at,
                  *, revision="fastdiar-small-test-rev", threshold=0.8):
    frames = [
        {"end_ms": end, "vector": list(vector_at(end))}
        for end in range(start_ms + 80, end_ms + 1, 80)
    ]
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "generation_id": generation_id,
        "model_id": "microsoft/fastdiar-small",
        "model_revision": revision,
        "model_sha256": MODEL_SHA,
        "embedding_dim": 3,
        "frame_step_ms": 80,
        "lookback_frames": 10,
        "confidence_threshold": threshold,
        "calibration_id": "FASTDIAR_ARXIV_2610.02941V1_DEV" if threshold is not None else None,
        "frames": frames,
    }


def test_same_speaker_embedding_stays_confident_and_has_no_identity_label():
    registry = SpeakerChangeEvidenceRegistry()
    warmup = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    first = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", embeddings=warmup,
    )
    assert first["status"] == "WARMUP"

    batch = speaker_batch(SOURCE, "gen-a", 1100, 2100, lambda _: (1.0, 0.0, 0.0))
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="VOICED", embeddings=batch,
    )
    assert evidence["status"] == "MEASURED"
    assert evidence["reference_age_ms"] >= 800
    assert evidence["reference_age_ms"] <= 920
    assert evidence["cosine_similarity"] == 1.0
    assert evidence["confidence_gate_passed"] is True
    assert evidence["speaker_change_candidate"] is False
    assert evidence["peak_speaker_change_candidate"] is False
    assert evidence["candidate_count"] == 0
    assert evidence["speaker_label"] is None
    assert evidence["identity_authority"] is False
    assert evidence["learning_authority"] is False
    assert evidence["action_authority"] is False


def test_embedding_shift_is_only_a_change_candidate_during_voiced_activity():
    registry = SpeakerChangeEvidenceRegistry()
    first = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", embeddings=first,
    )
    second = speaker_batch(
        SOURCE, "gen-a", 1100, 2100,
        lambda end: (1.0, 0.0, 0.0) if end < 1660 else (0.0, 1.0, 0.0),
    )
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="VOICED", embeddings=second,
    )
    assert evidence["status"] == "MEASURED"
    # The nearest retained frame can be up to 1.5 frame steps from the
    # requested look-back timestamp; report the measured age, not the target.
    assert abs(evidence["reference_age_ms"] - 800) <= 120
    assert evidence["cosine_similarity"] == 0.0
    assert evidence["change_score"] == 0.5
    assert evidence["speaker_change_candidate"] is True
    assert evidence["interpretation"] == "LOW_SIMILARITY_DURING_VOICED_ACTIVITY_CHANGE_OR_OVERLAP"
    assert evidence["candidate_kind"] == "SPEAKER_CHANGE_OR_OVERLAP"


def test_same_batch_tail_cannot_overwrite_cross_window_change_evidence():
    def run(end_ms):
        registry = SpeakerChangeEvidenceRegistry()
        warmup = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
        registry.update(
            source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
            activity_hint="VOICED", embeddings=warmup,
        )
        current = speaker_batch(
            SOURCE, "gen-a", 1100, end_ms,
            lambda end: (1.0, 0.0, 0.0) if end < 1660 else (0.0, 1.0, 0.0),
        )
        return registry.update(
            source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=end_ms,
            activity_hint="VOICED", embeddings=current,
        )

    # The longer batch adds many later frames from the new speaker. Those
    # frames must not become their own look-back references in this same call.
    short = run(2100)
    long = run(3100)
    assert short["speaker_change_candidate"] is True
    assert long["speaker_change_candidate"] is True
    assert long["frame_end_ms"] == short["frame_end_ms"]
    assert long["cosine_similarity"] == short["cosine_similarity"] == 0.0
    assert long["change_score"] == short["change_score"] == 0.5
    assert long["candidate_kind"] == short["candidate_kind"] == "SPEAKER_CHANGE_OR_OVERLAP"


def test_low_similarity_without_voiced_activity_is_not_speaker_change():
    registry = SpeakerChangeEvidenceRegistry()
    first = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", embeddings=first,
    )
    second = speaker_batch(SOURCE, "gen-a", 1100, 2100, lambda _: (0.0, 1.0, 0.0))
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="UNVOICED_NOISE", embeddings=second,
    )
    assert evidence["confidence_gate_passed"] is False
    assert evidence["speaker_change_candidate"] is False
    assert evidence["peak_speaker_change_candidate"] is False
    assert evidence["candidate_count"] == 0
    assert evidence["interpretation"] == "LOW_SIMILARITY_WITHOUT_VOICED_ACTIVITY"


def test_missing_threshold_emits_score_without_a_decision():
    registry = SpeakerChangeEvidenceRegistry()
    first = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0), threshold=None)
    registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", embeddings=first,
    )
    second = speaker_batch(SOURCE, "gen-a", 1100, 2100, lambda _: (0.0, 1.0, 0.0), threshold=None)
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="VOICED", embeddings=second,
    )
    assert evidence["change_score"] == 0.5
    assert evidence["speaker_change_candidate"] is None
    assert evidence["threshold_status"] == "NOT_CONFIGURED"
    assert evidence["peak_speaker_change_candidate"] is None
    assert evidence["candidate_count"] == 0
    assert all(frame["speaker_change_candidate"] is None for frame in evidence["frame_evidence"])


def test_model_revision_change_resets_history_before_comparison():
    registry = SpeakerChangeEvidenceRegistry()
    first = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", embeddings=first,
    )
    second = speaker_batch(SOURCE, "gen-a", 1100, 1340, lambda _: (0.0, 1.0, 0.0),
                          revision="fastdiar-small-new-rev")
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=1340,
        activity_hint="VOICED", embeddings=second,
    )
    assert evidence["reset_reason"] == "MODEL_OR_CALIBRATION_CHANGED"
    assert evidence["status"] == "WARMUP"
    assert evidence["speaker_change_candidate"] is None


@pytest.mark.parametrize("mutate", [
    lambda batch: batch.update(source_id="other-source"),
    lambda batch: batch.update(model_sha256="not-a-sha"),
    lambda batch: batch.update(embedding_dim=4),
    lambda batch: batch["frames"][0].update(vector=[float("nan"), 0.0, 1.0]),
    lambda batch: batch["frames"][1].update(end_ms=batch["frames"][0]["end_ms"]),
])
def test_invalid_embedding_packets_are_rejected(mutate):
    batch = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    mutate(batch)
    registry = SpeakerChangeEvidenceRegistry()
    with pytest.raises(SpeakerEvidenceError):
        registry.update(
            source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
            activity_hint="VOICED", embeddings=batch,
        )


def test_runtime_reset_clears_in_memory_embedding_history(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        batch = speaker_batch(SOURCE, event["brain_generation_id"], 100, 1100,
                              lambda _: (1.0, 0.0, 0.0))
        consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=batch,
        )
        registry = _runtime_speaker_evidence_registry(runtime)
        assert len(registry) == 1
        reset_runtime_temporal_voice_states(
            runtime, source_id=SOURCE, generation_id=event["brain_generation_id"],
        )
        assert len(registry) == 0
    finally:
        runtime.store.close()


def test_a5_a4_c3_consumer_uses_change_evidence_without_persisting_vectors(tmp_path):
    runtime, event = make_runtime(tmp_path)
    generation = event["brain_generation_id"]
    try:
        first = speaker_batch(SOURCE, generation, 100, 1100, lambda _: (1.0, 0.0, 0.0))
        consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=generation,
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=first,
        )
        second = speaker_batch(
            SOURCE, generation, 1100, 2100,
            lambda end: (1.0, 0.0, 0.0) if end < 1660 else (0.0, 1.0, 0.0),
        )
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=1100,
            event_id=event["event_id"], generation_id=generation,
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=second,
        )
        evidence = result["speaker_change_evidence"]
        assert evidence["speaker_change_candidate"] is True
        assert result["a4"]["speaker_change_evidence"]["change_score"] == 0.5
        assert result["a4"]["learning_authority"] is False
        assert result["a4"]["action_authority"] is False
        summary = result["c3_admission"].selected[0].summary
        assert "speaker_change_score=0.50" in summary
        assert "speaker_change_candidate=1" in summary
        assert "speaker_change_kind=CHANGE_OR_OVERLAP" in summary
        persisted = json.dumps(result["packet"], sort_keys=True)
        assert '"vector"' not in persisted
        assert '"speaker_label": null' in persisted
        assert result["packet"]["segments"][0]["acoustic"]["speaker_change_evidence"]["threshold_status"] == "CALLER_ASSERTED_UNVERIFIED"
    finally:
        runtime.store.close()


def test_batch_peak_change_survives_return_to_prior_speaker_for_a4_and_c3(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    generation = event["brain_generation_id"]
    captured = {}

    class CapturingAttention:
        def modulate(self, event_id, sal):
            captured["sal"] = dict(sal)
            return {"sal": dict(sal)}

    monkeypatch.setattr(
        audio_voice_module.attctl,
        "controller",
        lambda current_runtime: CapturingAttention(),
    )
    try:
        first = speaker_batch(SOURCE, generation, 100, 1100, lambda _: (1.0, 0.0, 0.0))
        consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=generation,
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=first,
        )
        # The batch contains a brief B interval followed by a return to A.
        # The last measured frame is stable, but the earlier transition must
        # remain visible to A4 and the bounded C3 summary.
        second = speaker_batch(
            SOURCE, generation, 1100, 2100,
            lambda end: (0.0, 1.0, 0.0) if 1660 <= end < 1820 else (1.0, 0.0, 0.0),
        )
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=1100,
            event_id=event["event_id"], generation_id=generation,
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=second,
        )
        evidence = result["speaker_change_evidence"]
        assert evidence["speaker_change_candidate"] is False
        assert evidence["peak_speaker_change_candidate"] is True
        assert evidence["candidate_count"] >= 1
        assert evidence["peak_candidate_change_score"] == 0.5
        assert any(frame["speaker_change_candidate"] is True for frame in evidence["frame_evidence"])
        assert result["a4"]["speaker_change_evidence"]["peak_speaker_change_candidate"] is True
        assert captured["sal"]["external_interrupt"] >= 0.125
        summary = result["c3_admission"].selected[0].summary
        assert "speaker_change_candidate=1" in summary
        assert "speaker_change_score=0.50" in summary
        assert "speaker_change_kind=CHANGE_OR_OVERLAP" in summary
        persisted = json.dumps(result["packet"], sort_keys=True)
        assert '"vector"' not in persisted
        assert '"speaker_label": null' in persisted
    finally:
        runtime.store.close()


def test_invalid_speaker_embedding_does_not_break_base_audio_path(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        batch = speaker_batch(SOURCE, event["brain_generation_id"], 100, 1100,
                              lambda _: (1.0, 0.0, 0.0))
        batch["frames"][0]["vector"] = [0.0]
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=batch,
        )
        assert result["status"] == "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION"
        assert result["speaker_change_evidence"]["status"] == "REJECTED"
        assert result["c3_admission"].status == "ADMITTED"
        assert "speaker_change" in result["packet"]["segments"][0]["unmeasured"]
    finally:
        runtime.store.close()
