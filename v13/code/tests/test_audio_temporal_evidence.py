import pytest

from v13.audio_temporal_evidence import TemporalVoiceEvidence, TemporalVoiceEvidenceRegistry


def cue(hint, score=1.0):
    return {"activity_hint": hint, "activity_score": score}


def step(state, t, hint, score=1.0, source="mic-a", generation="g1", receipt=None):
    return state.update(
        source_id=source,
        generation_id=generation,
        start_ms=t,
        end_ms=t + 40,
        cues=cue(hint, score),
        consent_receipt_ref=receipt,
    )


def test_sustained_voice_onset_and_release_are_temporally_bounded():
    state = TemporalVoiceEvidence()
    first = step(state, 0, "VOICED")
    second = step(state, 40, "VOICED")
    assert first["voice_evidence"] == pytest.approx(0.393469, abs=1e-6)
    assert first["voice_active"] is False and first["voice_onset"] is False
    assert second["voice_evidence"] == pytest.approx(0.632121, abs=1e-6)
    assert second["voice_active"] is True and second["voice_onset"] is True

    offset = None
    for t in range(80, 400, 40):
        result = step(state, t, "SILENCE")
        if result["voice_offset"]:
            offset = t + 40
            break
    assert offset == 360
    assert state._active is False


def test_single_window_voice_burst_does_not_open_attention_gate():
    state = TemporalVoiceEvidence()
    burst = step(state, 0, "VOICED")
    tail = step(state, 40, "SILENCE")
    assert burst["voice_active"] is False
    assert burst["voice_onset"] is False
    assert tail["voice_active"] is False
    assert tail["voice_evidence"] < burst["voice_evidence"]


def test_unvoiced_noise_and_impulses_never_become_voice_evidence():
    state = TemporalVoiceEvidence()
    results = [step(state, t, "UNVOICED_NOISE", 1.0) for t in (0, 40, 80, 120)]
    results += [step(state, t, "IMPULSIVE", 1.0) for t in (160, 200)]
    assert all(result["voice_evidence"] == 0 for result in results)
    assert all(not result["voice_active"] and not result["voice_onset"] for result in results)


def test_source_generation_and_long_gaps_reset_the_filter():
    state = TemporalVoiceEvidence()
    step(state, 0, "VOICED")
    changed = step(state, 40, "VOICED", source="mic-b")
    assert changed["state_reset"] is True
    assert changed["reset_reason"] == "SOURCE_OR_GENERATION_CHANGED"
    assert changed["voice_evidence"] == pytest.approx(0.393469, abs=1e-6)

    gap = step(state, 2000, "VOICED", source="mic-b")
    assert gap["state_reset"] is True
    assert gap["reset_reason"] == "STREAM_GAP"
    assert gap["voice_evidence"] == pytest.approx(0.393469, abs=1e-6)


def test_nonmonotonic_and_malformed_inputs_fail_closed():
    state = TemporalVoiceEvidence()
    step(state, 0, "VOICED")
    with pytest.raises(ValueError, match="advance monotonically"):
        step(state, 0, "VOICED")
    with pytest.raises(ValueError, match="activity_score"):
        state.update(
            source_id="mic-a",
            generation_id="g1",
            start_ms=80,
            end_ms=120,
            cues=cue("VOICED", float("nan")),
        )


def test_invalid_filter_configuration_is_rejected():
    with pytest.raises(ValueError, match="offset_threshold"):
        TemporalVoiceEvidence(onset_threshold=0.5, offset_threshold=0.6)
    with pytest.raises(ValueError, match="attack_tau_ms"):
        TemporalVoiceEvidence(attack_tau_ms=0)


def test_unobserved_gap_decays_before_new_voice_window():
    state = TemporalVoiceEvidence()
    state.update(source_id="mic-a", generation_id="g1", start_ms=0, end_ms=40, cues=cue("VOICED"))
    active = state.update(source_id="mic-a", generation_id="g1", start_ms=40, end_ms=80, cues=cue("VOICED"))
    assert active["voice_active"] is True

    resumed = state.update(
        source_id="mic-a", generation_id="g1", start_ms=580, end_ms=660,
        cues=cue("VOICED"),
    )
    assert resumed["gap_ms"] == 500
    assert resumed["gap_decay_ms"] == 500
    assert resumed["observed_ms"] == 80
    assert resumed["gap_offset"] is True
    assert resumed["voice_offset"] is True
    assert resumed["voice_onset"] is True
    assert resumed["voice_active"] is True


def test_unobserved_gap_is_not_filled_by_current_silence():
    state = TemporalVoiceEvidence()
    state.update(source_id="mic-a", generation_id="g1", start_ms=0, end_ms=40, cues=cue("VOICED"))
    state.update(source_id="mic-a", generation_id="g1", start_ms=40, end_ms=80, cues=cue("VOICED"))

    resumed = state.update(
        source_id="mic-a", generation_id="g1", start_ms=580, end_ms=620,
        cues=cue("SILENCE"),
    )
    assert resumed["gap_ms"] == 500
    assert resumed["voice_offset"] is True
    assert resumed["voice_onset"] is False
    assert resumed["voice_active"] is False
    assert resumed["voice_evidence"] < 0.22


def test_overlapping_windows_only_advance_newly_observed_suffix():
    state = TemporalVoiceEvidence()
    state.update(source_id="mic-a", generation_id="g1", start_ms=100, end_ms=140, cues=cue("VOICED"))
    resumed = state.update(
        source_id="mic-a", generation_id="g1", start_ms=120, end_ms=160,
        cues=cue("VOICED"),
    )
    assert resumed["observed_ms"] == 20
    assert resumed["elapsed_ms"] == 20
    assert resumed["voice_evidence"] == pytest.approx(0.527633, abs=1e-6)
    assert resumed["voice_onset"] is False


def test_gap_beyond_reset_threshold_does_not_infer_an_offset():
    state = TemporalVoiceEvidence()
    state.update(source_id="mic-a", generation_id="g1", start_ms=0, end_ms=40, cues=cue("VOICED"))
    state.update(source_id="mic-a", generation_id="g1", start_ms=40, end_ms=80, cues=cue("VOICED"))
    resumed = state.update(
        source_id="mic-a", generation_id="g1", start_ms=1181, end_ms=1221,
        cues=cue("VOICED"),
    )
    assert resumed["state_reset"] is True
    assert resumed["reset_reason"] == "STREAM_GAP"
    assert resumed["gap_ms"] == 1101
    assert resumed["gap_decay_ms"] == 0
    assert resumed["voice_offset"] is False
    assert resumed["voice_onset"] is False
    assert resumed["voice_active"] is False


def test_registry_is_bounded_lru_and_preserves_recent_stream_state():
    registry = TemporalVoiceEvidenceRegistry(max_streams=2)
    first_a = registry.update(
        source_id="mic-a", generation_id="g1", start_ms=0, end_ms=40,
        cues=cue("VOICED"),
    )
    registry.update(
        source_id="mic-b", generation_id="g1", start_ms=0, end_ms=40,
        cues=cue("VOICED"),
    )
    second_a = registry.update(
        source_id="mic-a", generation_id="g1", start_ms=40, end_ms=80,
        cues=cue("VOICED"),
    )
    registry.update(
        source_id="mic-c", generation_id="g1", start_ms=0, end_ms=40,
        cues=cue("VOICED"),
    )
    resumed_b = registry.update(
        source_id="mic-b", generation_id="g1", start_ms=40, end_ms=80,
        cues=cue("VOICED"),
    )
    assert first_a["voice_active"] is False
    assert second_a["voice_active"] is True
    assert resumed_b["voice_evidence"] == pytest.approx(0.393469, abs=1e-6)
    assert resumed_b["voice_active"] is False
    assert len(registry) == 2


def test_registry_replaces_old_generation_and_supports_explicit_reset():
    registry = TemporalVoiceEvidenceRegistry(max_streams=4)
    registry.update(
        source_id="mic-a", generation_id="g1", start_ms=0, end_ms=40,
        cues=cue("VOICED"),
    )
    new_generation = registry.update(
        source_id="mic-a", generation_id="g2", start_ms=0, end_ms=40,
        cues=cue("VOICED"),
    )
    assert new_generation["voice_evidence"] == pytest.approx(0.393469, abs=1e-6)
    assert len(registry) == 1
    assert registry.reset(source_id="mic-a", generation_id="g2") == 1
    assert len(registry) == 0
    registry.update(
        source_id="mic-a", generation_id="g2", start_ms=0, end_ms=40,
        cues=cue("VOICED"),
    )
    assert registry.reset() == 1
    assert len(registry) == 0



def test_explicit_temporal_state_resets_when_consent_receipt_changes():
    state = TemporalVoiceEvidence()
    step(state, 0, "VOICED", receipt="fixture:receipt-a")
    active = step(state, 40, "VOICED", receipt="fixture:receipt-a")
    assert active["voice_active"] is True

    renewed = step(state, 80, "SILENCE", receipt="fixture:receipt-b")
    assert renewed["state_reset"] is True
    assert renewed["reset_reason"] == "CONSENT_RECEIPT_CHANGED"
    assert renewed["voice_evidence"] == 0.0
    assert renewed["voice_active"] is False
    assert renewed["voice_onset"] is False


def test_registry_starts_fresh_for_a_new_consent_receipt():
    registry = TemporalVoiceEvidenceRegistry(max_streams=4)
    registry.update(
        source_id="mic-a", generation_id="g1",
        consent_receipt_ref="fixture:receipt-a",
        start_ms=0, end_ms=40, cues=cue("VOICED"),
    )
    active = registry.update(
        source_id="mic-a", generation_id="g1",
        consent_receipt_ref="fixture:receipt-a",
        start_ms=40, end_ms=80, cues=cue("VOICED"),
    )
    assert active["voice_active"] is True

    renewed = registry.update(
        source_id="mic-a", generation_id="g1",
        consent_receipt_ref="fixture:receipt-b",
        start_ms=80, end_ms=120, cues=cue("SILENCE"),
    )
    assert renewed["state_reset"] is True
    assert renewed["reset_reason"] == "CONSENT_RECEIPT_CHANGED"
    assert renewed["voice_evidence"] == 0.0
    assert renewed["voice_active"] is False
    assert len(registry) == 1
