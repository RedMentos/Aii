"""Synthetic and consumer tests for source-bound speaker-similarity diagnostics."""
from array import array
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
    _speaker_change_decision,
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
                  *, revision="fixture-embedding-v1", threshold=0.8):
    frames = [
        {"end_ms": end, "vector": list(vector_at(end))}
        for end in range(start_ms + 80, end_ms + 1, 80)
    ]
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "generation_id": generation_id,
        "model_id": "fixture/three-dim-encoder",
        "model_revision": revision,
        "model_sha256": MODEL_SHA,
        "embedding_dim": 3,
        "frame_step_ms": 80,
        "lookback_frames": 10,
        "confidence_threshold": threshold,
        "calibration_id": "fixture:caller-asserted-unverified" if threshold is not None else None,
        "frames": frames,
    }


def test_same_speaker_embedding_remains_unclassified_without_calibration():
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
    assert short["speaker_change_candidate"] is None
    assert long["speaker_change_candidate"] is None
    assert long["peak_speaker_change_candidate"] is None
    assert long["candidate_count"] == 0
    assert all(frame["speaker_change_candidate"] is None for frame in long["frame_evidence"])
    assert long["frame_end_ms"] == short["frame_end_ms"]
    assert long["cosine_similarity"] == short["cosine_similarity"] == 0.0
    assert long["change_score"] == short["change_score"] == 0.5
    assert long["candidate_kind"] is None


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
                          revision="fixture-embedding-v2")
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

        changed = speaker_batch(
            SOURCE, event["brain_generation_id"], 2100, 3100,
            lambda _: (0.0, 1.0, 0.0),
        )
        silent = consume_pcm16_voice_window(
            runtime, b"\x00\x00" * 16000, sample_rate=16000, start_ms=2100,
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
        activity_hint="VOICED", embeddings=batch,
    )
    stored = registry._states[(SOURCE, "gen-compact")].frames[0][1]
    assert isinstance(stored, array)
    assert stored.typecode == "f"
    assert stored.itemsize == 4
