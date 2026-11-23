"""Synthetic and consumer tests for source-bound speaker-similarity diagnostics."""
from array import array
from contextlib import contextmanager
import hashlib
import json
import math
import random
import struct
from types import SimpleNamespace

import pytest

from v13.audio_speaker_evidence import (
    SCHEMA, SpeakerChangeEvidenceRegistry, SpeakerEvidenceError,
)
from v13.audio_teacher_ear import (
    SCHEMA as TEACHER_EAR_SCHEMA, validate_teacher_ear_result,
)
from v13 import audio_voice_cues as audio_voice_module
from v13.audio_voice_cues import (
    _runtime_speaker_evidence_registry,
    _speaker_change_decision,
    consume_pcm16_voice_window,
    reset_runtime_temporal_voice_states,
)
from v13.store import Store


SOURCE = "fixture:raw-ear-speaker"
RECEIPT = "fixture:consented-speaker"
MODEL_SHA = "a" * 64


def tone(sample_rate=16000, frequency=140, seconds=1.0, amplitude=6000, phase=0.0):
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate + phase))
               for i in range(count)]
    return struct.pack("<" + "h" * len(samples), *samples)


CURRENT_CHUNK_SHA256 = hashlib.sha256(tone()).hexdigest()


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
                  *, revision="fixture-embedding-v1", threshold=0.8,
                  current_chunk_sha256=CURRENT_CHUNK_SHA256,
                  frame_step_ms=80, lookback_frames=10):
    frames = [
        {"end_ms": end, "vector": list(vector_at(end))}
        for end in range(start_ms + frame_step_ms, end_ms + 1, frame_step_ms)
    ]
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "generation_id": generation_id,
        "model_id": "fixture/three-dim-encoder",
        "model_revision": revision,
        "model_sha256": MODEL_SHA,
        "current_chunk_sha256": current_chunk_sha256,
        "embedding_dim": 3,
        "frame_step_ms": frame_step_ms,
        "lookback_frames": lookback_frames,
        "confidence_threshold": threshold,
        "calibration_id": "fixture:caller-asserted-unverified" if threshold is not None else None,
        "frames": frames,
    }


def test_audio_window_hash_mismatch_is_rejected_before_history_changes():
    registry = SpeakerChangeEvidenceRegistry()
    batch = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    batch["current_chunk_sha256"] = "b" * 64
    with pytest.raises(SpeakerEvidenceError, match="current PCM chunk hash"):
        registry.update(
            source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
            activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256,
            embeddings=batch,
        )
    assert len(registry) == 0


def test_same_speaker_embedding_remains_unclassified_without_calibration():
    registry = SpeakerChangeEvidenceRegistry()
    warmup = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    first = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=warmup,
    )
    assert first["status"] == "WARMUP"

    batch = speaker_batch(SOURCE, "gen-a", 1100, 2100, lambda _: (1.0, 0.0, 0.0))
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=batch,
    )
    assert evidence["status"] == "MEASURED"
    reference_end = warmup["frames"][-1]["end_ms"]
    tolerance = max(40, int(batch["frame_step_ms"] * 1.5))
    lookback_ms = batch["lookback_frames"] * batch["frame_step_ms"]
    comparable_frame_ends = [
        frame["end_ms"] for frame in batch["frames"]
        if abs(frame["end_ms"] - lookback_ms - reference_end) <= tolerance
    ]
    assert comparable_frame_ends
    expected_reference_age_ms = max(comparable_frame_ends) - reference_end
    assert evidence["frame_end_ms"] == max(comparable_frame_ends)
    assert evidence["reference_age_ms"] == expected_reference_age_ms
    assert evidence["cosine_similarity"] == 1.0
    assert evidence["threshold_status"] == "CALLER_ASSERTED_UNVERIFIED"
    assert evidence["confidence_gate_passed"] is None
    assert evidence["speaker_change_candidate"] is None
    assert evidence["peak_speaker_change_candidate"] is None
    assert evidence["candidate_count"] == 0
    assert evidence["speaker_label"] is None
    assert evidence["identity_authority"] is False
    assert evidence["learning_authority"] is False
    assert evidence["action_authority"] is False


def test_embedding_shift_remains_similarity_only_until_calibrated():
    registry = SpeakerChangeEvidenceRegistry()
    first = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=first,
    )
    second = speaker_batch(
        SOURCE, "gen-a", 1100, 2100,
        lambda end: (1.0, 0.0, 0.0) if end < 1660 else (0.0, 1.0, 0.0),
    )
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=second,
    )
    assert evidence["status"] == "MEASURED"
    # The nearest retained frame can be up to 1.5 frame steps from the
    # requested look-back timestamp; report the measured age, not the target.
    assert abs(evidence["reference_age_ms"] - 800) <= 120
    assert evidence["cosine_similarity"] == 0.0
    assert evidence["change_score"] == 0.5
    assert evidence["threshold_status"] == "CALLER_ASSERTED_UNVERIFIED"
    assert evidence["speaker_change_candidate"] is None
    assert evidence["peak_speaker_change_candidate"] is None
    assert evidence["candidate_count"] == 0
    assert evidence["interpretation"] == "SIMILARITY_ONLY_UNCALIBRATED"
    assert evidence["candidate_kind"] is None


def test_same_batch_tail_cannot_overwrite_cross_window_change_evidence():
    def run(end_ms):
        registry = SpeakerChangeEvidenceRegistry()
        warmup = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
        registry.update(
            source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
            activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=warmup,
        )
        current = speaker_batch(
            SOURCE, "gen-a", 1100, end_ms,
            lambda end: (1.0, 0.0, 0.0) if end < 1660 else (0.0, 1.0, 0.0),
        )
        return registry.update(
            source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=end_ms,
            activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=current,
        )

    # The longer batch adds many later frames from the new speaker. Those
    # frames must not become their own look-back references in this same call.
    short = run(2100)
    long = run(3100)
    assert short["speaker_change_candidate"] is None
    assert long["speaker_change_candidate"] is None
    assert long["peak_speaker_change_candidate"] is None
    assert long["candidate_count"] == 0
    assert all(frame["speaker_change_candidate"] is None for frame in long["frame_evidence"])
    assert long["frame_end_ms"] == short["frame_end_ms"]
    assert long["cosine_similarity"] == short["cosine_similarity"] == 0.0
    assert long["change_score"] == short["change_score"] == 0.5
    assert long["candidate_kind"] is None



@pytest.mark.parametrize("lookback_frames", [10, 20])
def test_one_and_two_second_reference_timestamps_are_batch_length_invariant(lookback_frames):
    frame_step_ms = 100
    warmup_end_ms = 2100
    common_frame_end_ms = 3100

    def run(current_end_ms):
        registry = SpeakerChangeEvidenceRegistry()
        warmup = speaker_batch(
            SOURCE, "gen-time", 100, warmup_end_ms,
            lambda _: (1.0, 0.0, 0.0),
            frame_step_ms=frame_step_ms, lookback_frames=lookback_frames,
        )
        registry.update(
            source_id=SOURCE, generation_id="gen-time",
            start_ms=100, end_ms=warmup_end_ms,
            activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256,
            embeddings=warmup,
        )
        current = speaker_batch(
            SOURCE, "gen-time", warmup_end_ms, current_end_ms,
            lambda _: (0.0, 1.0, 0.0),
            frame_step_ms=frame_step_ms, lookback_frames=lookback_frames,
        )
        evidence = registry.update(
            source_id=SOURCE, generation_id="gen-time",
            start_ms=warmup_end_ms, end_ms=current_end_ms,
            activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256,
            embeddings=current,
        )
        return next(
            frame for frame in evidence["frame_evidence"]
            if frame["frame_end_ms"] == common_frame_end_ms
        )

    one_second_batch = run(common_frame_end_ms)
    two_second_batch = run(4100)
    expected_target_ms = common_frame_end_ms - lookback_frames * frame_step_ms
    assert expected_target_ms == (2100 if lookback_frames == 10 else 1100)
    for frame in (one_second_batch, two_second_batch):
        assert frame["lookback_target_ms"] == expected_target_ms
        assert frame["reference_frame_end_ms"] == expected_target_ms
        assert frame["reference_age_ms"] == lookback_frames * frame_step_ms
        assert frame["cosine_similarity"] == 0.0
        assert frame["change_score"] == 0.5
    assert one_second_batch == two_second_batch

def test_low_similarity_without_voiced_activity_is_not_speaker_change():
    registry = SpeakerChangeEvidenceRegistry()
    first = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=first,
    )
    second = speaker_batch(SOURCE, "gen-a", 1100, 2100, lambda _: (0.0, 1.0, 0.0))
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="UNVOICED_NOISE", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=second,
    )
    assert evidence["confidence_gate_passed"] is None
    assert evidence["speaker_change_candidate"] is None
    assert evidence["peak_speaker_change_candidate"] is None
    assert evidence["candidate_count"] == 0
    assert evidence["interpretation"] == "SIMILARITY_ONLY_UNCALIBRATED"


def test_missing_threshold_emits_score_without_a_decision():
    registry = SpeakerChangeEvidenceRegistry()
    first = speaker_batch(SOURCE, "gen-a", 100, 1100, lambda _: (1.0, 0.0, 0.0), threshold=None)
    registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=100, end_ms=1100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=first,
    )
    second = speaker_batch(SOURCE, "gen-a", 1100, 2100, lambda _: (0.0, 1.0, 0.0), threshold=None)
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=2100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=second,
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
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=first,
    )
    second = speaker_batch(SOURCE, "gen-a", 1100, 1340, lambda _: (0.0, 1.0, 0.0),
                          revision="fixture-embedding-v2")
    evidence = registry.update(
        source_id=SOURCE, generation_id="gen-a", start_ms=1100, end_ms=1340,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=second,
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
            activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=batch,
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


def test_a5_a4_c3_consumer_preserves_unverified_similarity_without_vectors(tmp_path):
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
        assert evidence["speaker_change_candidate"] is None
        assert evidence["peak_speaker_change_candidate"] is None
        assert evidence["candidate_count"] == 0
        assert evidence["threshold_status"] == "CALLER_ASSERTED_UNVERIFIED"
        assert result["a4"]["speaker_change_decision"] == "DEFER"
        assert result["a4"]["learning_authority"] is False
        assert result["a4"]["action_authority"] is False
        summary = result["c3_admission"].selected[0].summary
        assert "speaker_similarity_delta=0.50" in summary
        assert "spk_cal=UNVERIFIED" in summary
        assert "speaker_change_candidate=" not in summary
        assert "speaker_change_kind=" not in summary
        assert "spk_dec=DEFER" in summary
        persisted = json.dumps(result["packet"], sort_keys=True)
        assert '"vector"' not in persisted
        assert '"speaker_label": null' in persisted
        assert result["packet"]["segments"][0]["acoustic"]["speaker_change_evidence"]["threshold_status"] == "CALLER_ASSERTED_UNVERIFIED"
    finally:
        runtime.store.close()


def test_batch_similarity_diagnostic_does_not_trigger_a4_interrupt_or_c3_candidate(tmp_path, monkeypatch):
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
        # The raw per-frame delta remains diagnostic; without verified
        # calibration it must not become a speaker decision or attention gain.
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
        assert evidence["speaker_change_candidate"] is None
        assert evidence["peak_speaker_change_candidate"] is None
        assert evidence["candidate_count"] == 0
        assert evidence["peak_candidate_change_score"] == 0.0
        assert all(frame["speaker_change_candidate"] is None for frame in evidence["frame_evidence"])
        assert any(frame["change_score"] == 0.5 for frame in evidence["frame_evidence"])
        assert result["a4"]["speaker_change_evidence"]["peak_speaker_change_candidate"] is None
        assert result["a4"]["speaker_change_decision"] == "DEFER"
        summary = result["c3_admission"].selected[0].summary
        assert "speaker_change_candidate=" not in summary
        assert "speaker_change_kind=" not in summary
        assert "spk_cal=UNVERIFIED" in summary
        assert "spk_dec=DEFER" in summary
        with_speaker_interrupt = captured["sal"]["external_interrupt"]
        persisted = json.dumps(result["packet"], sort_keys=True)
        assert '"vector"' not in persisted
        assert '"speaker_label": null' in persisted

        # Negative control: the same audio without any speaker embedding input
        # must produce the same A4 interrupt; uncalibrated similarity is inert.
        baseline_runtime, baseline_event = make_runtime(tmp_path / "baseline")
        try:
            baseline_generation = baseline_event["brain_generation_id"]
            consume_pcm16_voice_window(
                baseline_runtime, tone(), sample_rate=16000, start_ms=100,
                event_id=baseline_event["event_id"], generation_id=baseline_generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
                finality="FINAL",
            )
            consume_pcm16_voice_window(
                baseline_runtime, tone(), sample_rate=16000, start_ms=1100,
                event_id=baseline_event["event_id"], generation_id=baseline_generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
                finality="FINAL",
            )
            assert captured["sal"]["external_interrupt"] == with_speaker_interrupt
        finally:
            baseline_runtime.store.close()
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


def _decision_cues(activity="VOICED", frame_count=50, voiced_fraction=0.8):
    return {
        "activity_hint": activity,
        "frame_count": frame_count,
        "voiced_fraction": voiced_fraction,
    }


def _decision_evidence(*, candidate=False, gate=True, calibration="fixture-cal-v1", status="MEASURED"):
    return {
        "status": status,
        "threshold_status": "CALLER_ASSERTED_UNVERIFIED",
        "calibration_receipt_sha256": None,
        "calibration_id": calibration,
        "confidence_threshold": 0.65,
        "peak_speaker_change_candidate": candidate,
        "speaker_change_candidate": candidate,
        "confidence_gate_passed": gate,
    }


def test_three_regime_gate_defers_caller_asserted_threshold_even_with_calibration_label():
    assert _speaker_change_decision(
        _decision_evidence(), _decision_cues()
    ) == "DEFER"
    assert _speaker_change_decision(
        _decision_evidence(candidate=True, gate=False), _decision_cues()
    ) == "DEFER"


@pytest.mark.parametrize("activity", ["SILENCE", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"])
def test_three_regime_gate_defers_nonvoiced_low_similarity(activity):
    evidence = _decision_evidence(candidate=False, gate=False)
    assert _speaker_change_decision(
        evidence, _decision_cues(activity=activity)
    ) == "DEFER"


def test_three_regime_gate_defers_missing_rejected_or_uncalibrated_evidence():
    cues = _decision_cues()
    assert _speaker_change_decision(None, cues) == "DEFER"
    assert _speaker_change_decision(
        _decision_evidence(status="REJECTED"), cues
    ) == "DEFER"
    assert _speaker_change_decision(
        _decision_evidence(calibration=None), cues
    ) == "DEFER"
    assert _speaker_change_decision(
        dict(_decision_evidence(), confidence_threshold=None), cues
    ) == "DEFER"


def test_three_regime_gate_defers_short_or_insufficient_voiced_windows():
    evidence = _decision_evidence()
    assert _speaker_change_decision(
        evidence, _decision_cues(frame_count=1, voiced_fraction=1.0)
    ) == "DEFER"
    assert _speaker_change_decision(
        evidence, _decision_cues(frame_count=50, voiced_fraction=0.02)
    ) == "DEFER"
    assert _speaker_change_decision(
        evidence, _decision_cues(frame_count=100, voiced_fraction=0.8)
    ) == "DEFER"


def test_a4_and_c3_receive_explicit_defer_instead_of_false_stability_on_silence(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        first = speaker_batch(
            SOURCE, event["brain_generation_id"], 100, 1100,
            lambda _: (1.0, 0.0, 0.0),
        )
        warmup = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=first,
        )
        assert warmup["a4"]["speaker_change_decision"] == "DEFER"

        stable = speaker_batch(
            SOURCE, event["brain_generation_id"], 1100, 2100,
            lambda _: (1.0, 0.0, 0.0),
        )
        supported = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=1100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=stable,
        )
        assert supported["a4"]["speaker_change_decision"] == "DEFER"
        assert supported["packet"]["segments"][0]["acoustic"]["speaker_change_decision"] == "DEFER"
        assert supported["speaker_change_evidence"]["decision"] == "DEFER"

        silent_pcm = b"\x00\x00" * 16000
        changed = speaker_batch(
            SOURCE, event["brain_generation_id"], 2100, 3100,
            lambda _: (0.0, 1.0, 0.0),
            current_chunk_sha256=hashlib.sha256(silent_pcm).hexdigest(),
        )
        silent = consume_pcm16_voice_window(
            runtime, silent_pcm, sample_rate=16000, start_ms=2100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL", speaker_embeddings=changed,
        )
        assert silent["a4"]["voice_activity_hint"] == "SILENCE"
        assert silent["speaker_change_evidence"]["confidence_gate_passed"] is None
        assert silent["speaker_change_evidence"]["speaker_change_candidate"] is None
        assert silent["a4"]["speaker_change_decision"] == "DEFER"
        assert silent["packet"]["segments"][0]["acoustic"]["speaker_change_decision"] == "DEFER"
        assert any(
            "spk_dec=DEFER" in percept.summary
            for percept in silent["c3_admission"].selected
        )
    finally:
        runtime.store.close()


def test_registry_stores_compact_float32_vectors_in_memory():
    registry = SpeakerChangeEvidenceRegistry()
    batch = speaker_batch(SOURCE, "gen-compact", 100, 1100, lambda _: (1.0, 0.0, 0.0))
    registry.update(
        source_id=SOURCE, generation_id="gen-compact", start_ms=100, end_ms=1100,
        activity_hint="VOICED", current_chunk_sha256=CURRENT_CHUNK_SHA256, embeddings=batch,
    )
    stored = registry._states[(SOURCE, "gen-compact")].frames[0][1]
    assert isinstance(stored, array)
    assert stored.typecode == "f"
    assert stored.itemsize == 4



def test_low_gain_periodic_window_reaches_runtime_a4_despite_absolute_silence_floor(tmp_path):
    pcm = tone(amplitude=100)
    samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    overall_rms = math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768.0
    assert overall_rms < 0.003

    cues = audio_voice_module.extract_voice_cues(pcm, 16000)
    assert cues["voiced_fraction"] >= 0.25
    assert cues["voicing_confidence"] >= 0.55
    assert cues["activity_hint"] == "VOICED"

    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, pcm, sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL",
        )
        assert result["a4"]["voice_activity_hint"] == "VOICED"
        assert result["a4"]["temporal_voice"]["voice_active"] is True
        assert "attention" in result["a4"]
    finally:
        runtime.store.close()


def test_low_level_noise_does_not_become_voiced_when_window_floor_is_relaxed():
    rng = random.Random(17)
    samples = [rng.randint(-50, 50) for _ in range(16000)]
    pcm = struct.pack("<" + "h" * len(samples), *samples)
    cues = audio_voice_module.extract_voice_cues(pcm, 16000)
    assert cues["voiced_fraction"] == 0.0
    assert cues["activity_hint"] == "SILENCE"


@pytest.mark.parametrize(
    ("sample_rate", "frequency", "phase"),
    [
        (rate, frequency, phase)
        for rate, frequency in ((16000, 7800), (22050, 10825), (44100, 8620), (48000, 7800))
        for phase in (0.0, 1.0, 2.4)
    ],
)
def test_high_frequency_alias_is_not_misclassified_as_voiced(sample_rate, frequency, phase):
    cues = audio_voice_module.extract_voice_cues(
        tone(sample_rate=sample_rate, frequency=frequency, amplitude=32767, phase=phase),
        sample_rate,
    )
    assert cues["activity_hint"] == "UNVOICED_NOISE"
    assert cues["voiced_fraction"] < 0.25


@pytest.mark.parametrize("sample_rate", [16000, 22050, 44100, 48000])
def test_antialias_filter_preserves_low_fundamental_pitch(sample_rate):
    cues = audio_voice_module.extract_voice_cues(
        tone(sample_rate=sample_rate, frequency=140), sample_rate,
    )
    assert cues["activity_hint"] == "VOICED"
    assert cues["f0_median_hz"] == pytest.approx(140, abs=5)


def _direct_antialias_reference(samples, sample_rate, factor):
    coefficients = audio_voice_module._voice_decimator_coefficients(sample_rate, factor)
    half = len(coefficients) // 2
    sample_count = len(samples)
    output = []
    for output_index in range(sample_count // factor):
        center = output_index * factor
        filtered = 0.0
        for tap_index, coefficient in enumerate(coefficients):
            source_index = center + tap_index - half
            if 0 <= source_index < sample_count:
                source_value = float(samples[source_index])
            elif sample_count <= half:
                source_value = float(samples[0] if source_index < 0 else samples[-1])
            elif source_index < 0:
                source_value = 2.0 * float(samples[0]) - float(samples[-source_index])
            else:
                mirror_index = 2 * sample_count - 2 - source_index
                source_value = 2.0 * float(samples[-1]) - float(samples[mirror_index])
            filtered += source_value * coefficient
        output.append(filtered)
    return output


@pytest.mark.parametrize("sample_rate", [16000, 22050, 44100, 48000])
@pytest.mark.parametrize("sample_count", [1, 10, 11, 257, 1001])
def test_symmetric_antialias_matches_direct_reference(sample_rate, sample_count):
    rng = random.Random(sample_rate * 10000 + sample_count)
    samples = [rng.randint(-32768, 32767) for _ in range(sample_count)]
    factor = max(1, sample_rate // 8000)
    actual, effective_rate = audio_voice_module._anti_alias_decimate(
        samples, sample_rate, factor,
    )
    expected = _direct_antialias_reference(samples, sample_rate, factor)
    assert effective_rate == sample_rate / factor
    assert actual == pytest.approx(expected, abs=1e-7)


def test_alias_rejection_reaches_the_real_a5_a4_c3_consumer(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(sample_rate=44100, frequency=8620, amplitude=32767, phase=1.0), sample_rate=44100,
            start_ms=100, event_id=event["event_id"],
            generation_id=event["brain_generation_id"], source_id=SOURCE,
            consent_receipt=RECEIPT, consent_check=consent_ok,
            consent_guard=consent_guard(consent_ok), finality="FINAL",
        )
        assert result["a4"]["voice_activity_hint"] == "UNVOICED_NOISE"
        assert result["temporal_voice"]["voice_evidence"] == 0.0
        assert result["a4"]["speaker_change_decision"] == "DEFER"
        assert "activity=UNVOICED_NOISE" in result["c3_admission"].selected[0].summary
    finally:
        runtime.store.close()


def test_provisional_audio_is_persisted_but_not_admitted_until_final(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        provisional = consume_pcm16_voice_window(
            runtime, tone(sample_rate=16000, frequency=140, phase=0.0),
            sample_rate=16000, start_ms=100,
            event_id=event["event_id"],
            generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok,
            consent_guard=consent_guard(consent_ok),
            finality="PROVISIONAL",
        )
        provisional_segment = provisional["packet"]["segments"][0]
        assert provisional_segment["finality"] == "PROVISIONAL"
        assert provisional_segment["learning_authority"] is False
        assert provisional_segment["action_authority"] is False
        assert provisional["c3_admission"].selected == ()
        assert SOURCE in provisional["c3_admission"].omitted
        stored = runtime.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
            (provisional["packet"]["packet_id"],),
        )
        assert stored is not None
        assert json.loads(stored["payload"])["segments"][0]["finality"] == "PROVISIONAL"

        final = consume_pcm16_voice_window(
            runtime, tone(sample_rate=16000, frequency=140, phase=0.4),
            sample_rate=16000, start_ms=1100,
            event_id=event["event_id"],
            generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok,
            consent_guard=consent_guard(consent_ok),
            finality="FINAL",
        )
        assert final["packet"]["segments"][0]["finality"] == "FINAL"
        assert len(final["c3_admission"].selected) == 1
        assert final["c3_admission"].selected[0].source_id == SOURCE
        assert final["learning_authority"] is False
        assert final["action_authority"] is False
    finally:
        runtime.store.close()


def _teacher_ear_result(generation_id, *, finality="FINAL", **overrides):
    value = {
        "schema": TEACHER_EAR_SCHEMA,
        "source_id": SOURCE,
        "generation_id": generation_id,
        "source_sha256": CURRENT_CHUNK_SHA256,
        "model_id": "fixture/local-asr",
        "model_revision": "fixture-r1",
        "model_sha256": "b" * 64,
        "language": "en",
        "start_ms": 100,
        "end_ms": 1100,
        "finality": finality,
        "network_used": False,
        "raw_audio_persisted": False,
        "words": [
            {"text": "hello", "start_ms": 120, "end_ms": 280},
            {"text": "world", "start_ms": 320, "end_ms": 500},
        ],
    }
    value.update(overrides)
    return value


def _validate_teacher_fixture(value, *, finality="FINAL", **flags):
    options = {
        "source_id": SOURCE,
        "generation_id": value["generation_id"],
        "source_sha256": CURRENT_CHUNK_SHA256,
        "start_ms": 100,
        "end_ms": 1100,
        "finality": finality,
        "consent_active": True,
        "teacher_opt_in": True,
        "transcript_consent": True,
    }
    options.update(flags)
    return validate_teacher_ear_result(value, **options)


def test_teacher_ear_result_is_source_bound_bounded_and_ephemeral():
    evidence = _validate_teacher_fixture(_teacher_ear_result("gen-teacher"))
    assert evidence["status"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert evidence["authority"] == "TEACHER_HYPOTHESIS"
    assert evidence["truth_authority"] == 0
    assert evidence["persistence"] == "EPHEMERAL_ONLY"
    assert evidence["word_count"] == 2
    assert "120-280" in evidence["summary"] and "hello" in evidence["summary"]
    assert len(evidence["summary"]) <= 512
    assert evidence["teacher_source_id"].startswith("audio_teacher_")


def test_teacher_ear_requires_both_opt_ins_and_exact_pcm_source():
    value = _teacher_ear_result("gen-teacher")
    with pytest.raises(PermissionError, match="separate opt-ins"):
        _validate_teacher_fixture(value, transcript_consent=False)
    with pytest.raises(PermissionError, match="consent lease"):
        _validate_teacher_fixture(value, consent_active=False)
    stale = _teacher_ear_result("gen-teacher", source_sha256="c" * 64)
    with pytest.raises(PermissionError, match="exact current PCM"):
        _validate_teacher_fixture(stale)


def test_teacher_ear_rejects_network_raw_persistence_and_bad_word_times():
    with pytest.raises(PermissionError, match="local"):
        _validate_teacher_fixture(_teacher_ear_result("gen-teacher", network_used=True))
    with pytest.raises(PermissionError, match="local"):
        _validate_teacher_fixture(_teacher_ear_result("gen-teacher", raw_audio_persisted=True))
    bad_time = _teacher_ear_result(
        "gen-teacher",
        words=[{"text": "late", "start_ms": 1090, "end_ms": 1110}],
    )
    with pytest.raises(ValueError, match="timestamps"):
        _validate_teacher_fixture(bad_time)


def test_teacher_ear_hypothesis_reaches_c3_without_entering_persisted_raw_packet(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL",
            teacher_result=_teacher_ear_result(event["brain_generation_id"]),
            teacher_opt_in=True, teacher_transcript_consent=True,
        )
        assert result["teacher_ear"]["authority"] == "TEACHER_HYPOTHESIS"
        assert result["a4"]["teacher_ear_status"] == "CALLER_SUPPLIED_UNVERIFIED"
        assert any("teacher_hypothesis" in item.summary and "hello" in item.summary
                   for item in result["c3_admission"].selected)
        stored = runtime.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
            (result["packet"]["packet_id"],),
        )
        assert stored is not None
        payload = json.loads(stored["payload"])
        assert payload["segments"][0]["asr_transcript"] is None
        assert "hello" not in json.dumps(payload, sort_keys=True)
    finally:
        runtime.store.close()


def test_teacher_ear_provisional_hypothesis_is_not_admitted_to_c3(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="PROVISIONAL",
            teacher_result=_teacher_ear_result(
                event["brain_generation_id"], finality="PROVISIONAL",
            ),
            teacher_opt_in=True, teacher_transcript_consent=True,
        )
        assert result["teacher_ear"]["finality"] == "PROVISIONAL"
        assert result["c3_admission"].selected == ()
    finally:
        runtime.store.close()


def test_teacher_ear_denial_happens_before_packet_persistence(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        with pytest.raises(PermissionError, match="separate opt-ins"):
            consume_pcm16_voice_window(
                runtime, tone(), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
                finality="FINAL",
                teacher_result=_teacher_ear_result(event["brain_generation_id"]),
                teacher_opt_in=True, teacher_transcript_consent=False,
            )
        stored = runtime.store.one(
            "SELECT id FROM packets WHERE kind='PerceptPacket'",
            (),
        )
        assert stored is None
    finally:
        runtime.store.close()


def test_teacher_ear_summary_truncates_without_unbounded_prompt_growth():
    words = [
        {"text": "longphrase" * 10, "start_ms": 100 + i, "end_ms": 101 + i}
        for i in range(64)
    ]
    evidence = _validate_teacher_fixture(_teacher_ear_result("gen-teacher", words=words))
    assert evidence["summary_truncated"] is True
    assert len(evidence["summary"]) <= 512


def test_teacher_ear_rejects_finality_mismatch_before_c3():
    provisional = _teacher_ear_result("gen-teacher", finality="PROVISIONAL")
    with pytest.raises(ValueError, match="finality differs"):
        _validate_teacher_fixture(provisional, finality="FINAL")


def test_optional_teacher_module_absence_preserves_acoustic_path_and_blocks_transcript(
    monkeypatch, tmp_path,
):
    import builtins

    runtime, event = make_runtime(tmp_path)
    real_import = builtins.__import__

    def without_optional_teacher(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 1 and name == "audio_teacher_ear":
            raise ModuleNotFoundError(
                "optional Teacher Ear module is absent", name="v13.audio_teacher_ear",
            )
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", without_optional_teacher)
    try:
        assert audio_voice_module._load_teacher_ear_validator() is None
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
            finality="FINAL",
            teacher_result=_teacher_ear_result(event["brain_generation_id"]),
            teacher_opt_in=True, teacher_transcript_consent=True,
        )
        assert result["status"] == "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION"
        assert result["teacher_ear"] is None
        assert result["teacher_ear_status"] == "UNAVAILABLE_MODULE"
        assert result["a4"]["teacher_ear_status"] == "UNAVAILABLE_MODULE"
        assert all("teacher_hypothesis" not in item.summary
                   for item in result["c3_admission"].selected)
        stored = runtime.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
            (result["packet"]["packet_id"],),
        )
        assert stored is not None
        payload = json.loads(stored["payload"])
        assert payload["segments"][0]["asr_transcript"] is None
        assert "hello" not in json.dumps(payload, sort_keys=True)

        denied_runtime, denied_event = make_runtime(tmp_path / "denied")
        try:
            with pytest.raises(PermissionError, match="separate opt-ins"):
                consume_pcm16_voice_window(
                    denied_runtime, tone(), sample_rate=16000, start_ms=100,
                    event_id=denied_event["event_id"],
                    generation_id=denied_event["brain_generation_id"],
                    source_id=SOURCE, consent_receipt=RECEIPT,
                    consent_check=consent_ok, consent_guard=consent_guard(consent_ok),
                    finality="FINAL",
                    teacher_result=_teacher_ear_result(denied_event["brain_generation_id"]),
                    teacher_opt_in=True, teacher_transcript_consent=False,
                )
            denied_packet = denied_runtime.store.one(
                "SELECT id FROM packets WHERE kind='PerceptPacket'", (),
            )
            assert denied_packet is None
        finally:
            denied_runtime.store.close()
    finally:
        runtime.store.close()


def test_audio_voice_cues_module_imports_without_optional_teacher_file(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    source_package = Path(audio_voice_module.__file__).parent
    staged_package = tmp_path / "v13"
    shutil.copytree(
        source_package, staged_package,
        ignore=shutil.ignore_patterns("__pycache__", "audio_teacher_ear.py"),
    )
    assert not (staged_package / "audio_teacher_ear.py").exists()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", "import v13.audio_voice_cues"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
