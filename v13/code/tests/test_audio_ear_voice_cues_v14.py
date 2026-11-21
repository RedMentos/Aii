"""Synthetic RAW EAR voice-cue extraction and real A4/C3 adapter regressions."""
from concurrent.futures import ThreadPoolExecutor
import math
import random
import struct
import threading
import time
from types import SimpleNamespace

import pytest

from v13 import audio_voice_cues as audio_voice_cues_module
from v13.audio_voice_cues import (
    consume_pcm16_voice_window,
    extract_voice_cues,
    reset_runtime_temporal_voice_states,
    validate_voice_cues,
)
from v13.store import Store
from v13.audio_temporal_evidence import TemporalVoiceEvidence


SOURCE_ID = "fixture:raw-ear-voice"
RECEIPT = "fixture:current-consent"


def tone(frequency=140, sample_rate=16000, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
               for i in range(count)]
    return struct.pack("<" + "h" * count, *samples)


def sweep_tone(start_hz=110, end_hz=240, sample_rate=16000, amplitude=6000):
    phase = 0.0
    samples = []
    for index in range(sample_rate):
        frequency = start_hz + (end_hz - start_hz) * (index / sample_rate)
        phase += 2 * math.pi * frequency / sample_rate
        samples.append(int(amplitude * math.sin(phase)))
    return struct.pack("<" + "h" * len(samples), *samples)


def amplitude_burst(sample_rate=16000):
    samples = [int((2000 if i < sample_rate // 2 else 10000)
                   * math.sin(2 * math.pi * 140 * i / sample_rate))
               for i in range(sample_rate)]
    return struct.pack("<" + "h" * len(samples), *samples)


def silence_padded_tone(sample_rate=16000):
    body = tone(frequency=140, sample_rate=sample_rate, seconds=0.5)
    silence = bytes(2 * int(sample_rate * 0.25))
    return silence + body + silence


def white_noise(sample_rate=16000, seconds=1.0, amplitude=4000):
    rng = random.Random(17)
    count = int(sample_rate * seconds)
    samples = [rng.randint(-amplitude, amplitude) for _ in range(count)]
    return struct.pack("<" + "h" * count, *samples)


def make_runtime(tmp_path):
    (tmp_path / "data" / "db").mkdir(parents=True)
    store = Store(tmp_path)
    store.ensure_generation_snapshot({}, {})
    session = store.new_session("RAW EAR voice cue test")
    event = store.event(session, "bounded synthetic acoustic fixture")
    return SimpleNamespace(home=tmp_path, store=store), event


def consent_ok(source_id, receipt):
    return source_id == SOURCE_ID and receipt == RECEIPT


def packet_count(store, event_id):
    return store.one("SELECT COUNT(*) AS n FROM packets WHERE event_id=?", (event_id,))["n"]


def attention_count(store, event_id):
    return store.one(
        "SELECT COUNT(*) AS n FROM telemetry WHERE kind='attention_gain' AND event_id=?",
        (event_id,),
    )["n"]



def test_runtime_registry_first_use_is_atomic_under_concurrency(monkeypatch):
    runtime = SimpleNamespace()
    original_registry = audio_voice_cues_module.TemporalVoiceEvidenceRegistry
    created = []
    created_lock = threading.Lock()

    class SlowRegistry(original_registry):
        def __init__(self, *args, **kwargs):
            # Let competing first-use calls reach the get/create boundary.
            time.sleep(0.03)
            super().__init__(*args, **kwargs)
            with created_lock:
                created.append(self)

    monkeypatch.setattr(
        audio_voice_cues_module, "TemporalVoiceEvidenceRegistry", SlowRegistry
    )
    barrier = threading.Barrier(8)

    def get_registry(_):
        barrier.wait(timeout=5)
        return audio_voice_cues_module._runtime_temporal_voice_registry(runtime)

    with ThreadPoolExecutor(max_workers=8) as pool:
        resolved = list(pool.map(get_registry, range(8)))

    assert len(created) == 1
    assert all(registry is created[0] for registry in resolved)
    assert runtime._raw_ear_temporal_registry is created[0]

def test_voiced_tone_yields_bounded_pitch_and_voicing_cues():
    cues = extract_voice_cues(tone(140), 16000)
    assert cues["activity_hint"] == "VOICED"
    assert 125 <= cues["f0_median_hz"] <= 155
    assert cues["voiced_fraction"] >= 0.8
    assert cues["voicing_confidence"] >= 0.55
    assert cues["frame_count"] <= 50


def test_noise_silence_and_impulse_are_not_misreported_as_voiced():
    silence_pcm = struct.pack("<" + "h" * 8000, *([0] * 8000))
    impulse_samples = [0] * 8000
    impulse_samples[1000] = 16000
    impulse_pcm = struct.pack("<" + "h" * 8000, *impulse_samples)
    assert extract_voice_cues(white_noise(), 16000)["activity_hint"] == "UNVOICED_NOISE"
    assert extract_voice_cues(silence_pcm, 8000)["activity_hint"] == "SILENCE"
    assert extract_voice_cues(impulse_pcm, 8000)["activity_hint"] == "IMPULSIVE"


def test_pitch_estimate_is_stable_across_supported_sample_rates():
    for sample_rate in (8000, 12000, 16000, 44100, 48000):
        cues = extract_voice_cues(tone(180, sample_rate=sample_rate), sample_rate)
        assert cues["f0_median_hz"] is not None and 160 <= cues["f0_median_hz"] <= 200


def test_prosody_change_tracks_pitch_and_energy_dynamics_not_noise():
    flat = extract_voice_cues(tone(140), 16000)
    sweep = extract_voice_cues(sweep_tone(), 16000)
    burst = extract_voice_cues(amplitude_burst(), 16000)
    noise = extract_voice_cues(white_noise(), 16000)
    assert flat["prosody_change_score"] < 0.05
    assert sweep["prosody_change_score"] > 0.6
    assert burst["prosody_change_score"] > 0.6
    assert burst["voiced_energy_range_db"] > 10.0
    assert noise["activity_hint"] == "UNVOICED_NOISE"
    assert noise["voiced_energy_range_db"] is None
    assert noise["prosody_change_score"] == 0.0

    padded = extract_voice_cues(silence_padded_tone(), 16000)
    assert padded["activity_hint"] == "VOICED"
    assert padded["energy_range_db"] > 60.0
    assert padded["voiced_energy_range_db"] < 2.0
    assert padded["prosody_change_score"] < 0.2


def test_single_voiced_frame_is_valid_but_cannot_claim_prosody_dynamics():
    fixtures = (
        (tone(140, sample_rate=16000, seconds=0.04), 1, 1.0),
        (
            tone(140, sample_rate=16000, seconds=0.01)
            + bytes(2 * int(16000 * 0.09)),
            4,
            0.25,
        ),
    )
    for pcm, expected_frames, expected_voiced_fraction in fixtures:
        cues = extract_voice_cues(pcm, 16000)
        assert cues["frame_count"] == expected_frames
        assert cues["voiced_fraction"] == pytest.approx(expected_voiced_fraction)
        assert cues["activity_hint"] == "VOICED"
        assert cues["f0_range_hz"] is None
        assert cues["voiced_energy_range_db"] == 0.0
        assert cues["prosody_change_score"] == 0.0

        malformed_energy = dict(cues, voiced_energy_range_db=1.0)
        with pytest.raises(ValueError, match="single voiced frame"):
            validate_voice_cues(malformed_energy)
        malformed_score = dict(cues, prosody_change_score=0.1)
        with pytest.raises(ValueError, match="single voiced frame"):
            validate_voice_cues(malformed_score)


def test_prosody_change_is_rejected_without_voiced_activity():
    cues = extract_voice_cues(white_noise(), 16000)
    cues["prosody_change_score"] = 0.2
    with pytest.raises(ValueError, match="prosody change requires voiced activity"):
        validate_voice_cues(cues)

    voiced = extract_voice_cues(tone(), 16000)
    for invalid in (-1.0, float("nan"), 121.0):
        malformed = dict(voiced, voiced_energy_range_db=invalid)
        with pytest.raises(ValueError, match="voice cue range is invalid"):
            validate_voice_cues(malformed)


def test_extractor_rejects_audio_windows_over_one_second():
    with pytest.raises(ValueError, match="limited to one second"):
        extract_voice_cues(tone(seconds=1.1), 16000)


def test_voice_cues_flow_to_real_a4_and_c3_without_raw_pcm_or_identity(tmp_path):
    runtime, event = make_runtime(tmp_path)
    pcm = tone(140)
    try:
        result = consume_pcm16_voice_window(
            runtime, pcm, sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
        )
        segment = result["packet"]["segments"][0]
        cues = segment["acoustic"]["voice_cues"]
        assert result["status"] == "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION"
        assert result["a4"]["voice_activity_hint"] == "VOICED"
        assert result["a4"]["prosody_change_score"] == cues["prosody_change_score"]
        assert result["a4"]["learning_authority"] is False
        assert result["a4"]["action_authority"] is False
        assert result["c3_admission"].status == "ADMITTED"
        summary = result["c3_admission"].selected[0].summary
        assert "activity=VOICED" in summary and "f0_med_hz=" in summary
        assert "voiced_energy_range_db=" in summary
        assert "prosody_change=" in summary
        assert segment["asr_transcript"] is None
        assert segment["learning_authority"] is False
        assert segment["action_authority"] is False
        assert "speaker_identity" in segment["unmeasured"]
        assert "speaker_id" not in cues and "speaker_identity" not in cues
        assert cues["method"] == "RAW_EAR_AUTOCORR_V3"
        assert cues["voiced_energy_range_db"] is not None
        assert packet_count(runtime.store, event["event_id"]) == 1
        assert attention_count(runtime.store, event["event_id"]) == 1
        digest = result["packet"]["source_ref"]["sha256"]
        assert not (tmp_path / "data" / "blobs" / digest).exists()
    finally:
        runtime.store.close()


def test_prosody_dynamics_reach_a4_attention_and_c3_summary(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    observed = {}

    class CaptureAttention:
        def modulate(self, event_id, sal=None):
            observed.update(sal or {})
            return {"captured": True}

    monkeypatch.setattr(audio_voice_cues_module.attctl, "controller", lambda runtime: CaptureAttention())
    try:
        result = consume_pcm16_voice_window(
            runtime, sweep_tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
        )
        score = result["a4"]["prosody_change_score"]
        assert score > 0.6
        assert observed["novelty"] >= 0.9 * score
        assert observed["external_interrupt"] >= 0.25 * score
        assert result["a4"]["attention"] == {"captured": True}
        assert "prosody_change=" in result["c3_admission"].selected[0].summary
    finally:
        runtime.store.close()


def test_provisional_voice_cues_remain_a4_only(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(140), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="PROVISIONAL", token_budget=512,
        )
        assert result["a4"]["finality"] == "PROVISIONAL"
        assert result["a4"]["voice_activity_hint"] == "VOICED"
        assert result["c3_admission"].status == "EMPTY_OR_UNAUTHORIZED"
        assert result["c3_admission"].selected == ()
        assert packet_count(runtime.store, event["event_id"]) == 1
        assert attention_count(runtime.store, event["event_id"]) == 1
    finally:
        runtime.store.close()


def test_tampered_voice_cues_fail_validation():
    cues = extract_voice_cues(tone(140), 16000)
    cues["f0_median_hz"] = 900.0
    with pytest.raises(ValueError, match="voice cue range"):
        validate_voice_cues(cues)


def test_revoked_consent_has_no_store_or_attention_side_effect(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=lambda source, receipt: False,
                finality="FINAL", token_budget=512,
            )
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_temporal_voice_evidence_gates_only_voice_salience_in_a4(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    state = TemporalVoiceEvidence()
    observed = []

    class CaptureAttention:
        def modulate(self, event_id, sal=None):
            observed.append(dict(sal or {}))
            return {"captured": True}

    monkeypatch.setattr(audio_voice_cues_module.attctl, "controller", lambda runtime: CaptureAttention())
    short_tone = tone(140, sample_rate=16000, seconds=0.04)
    try:
        first = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
            temporal_state=state,
        )
        second = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
            temporal_state=state,
        )
        assert first["a4"]["temporal_voice"]["voice_active"] is False
        assert first["a4"]["temporal_voice"]["voice_onset"] is False
        assert second["a4"]["temporal_voice"]["voice_active"] is True
        assert second["a4"]["temporal_voice"]["voice_onset"] is True
        assert observed[1]["novelty"] > observed[0]["novelty"]
        assert observed[1]["external_interrupt"] >= 0.5
        assert first["a4"]["learning_authority"] is False
        assert second["a4"]["action_authority"] is False
        assert first["c3_admission"].status == "ADMITTED"
        assert second["c3_admission"].status == "ADMITTED"
    finally:
        runtime.store.close()


def test_runtime_default_temporal_state_persists_across_audio_windows(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    observed = []

    class CaptureAttention:
        def modulate(self, event_id, sal=None):
            observed.append(dict(sal or {}))
            return {"captured": True}

    monkeypatch.setattr(
        audio_voice_cues_module.attctl, "controller",
        lambda runtime: CaptureAttention(),
    )
    short_tone = tone(140, sample_rate=16000, seconds=0.04)
    try:
        first = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
        )
        second = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
        )
        assert first["a4"]["temporal_voice"]["voice_active"] is False
        assert first["a4"]["temporal_voice"]["voice_onset"] is False
        assert second["a4"]["temporal_voice"]["voice_active"] is True
        assert second["a4"]["temporal_voice"]["voice_onset"] is True
        assert observed[1]["novelty"] > observed[0]["novelty"]
        assert observed[1]["external_interrupt"] >= 0.5
        assert len(runtime._raw_ear_temporal_registry) == 1
        assert reset_runtime_temporal_voice_states(runtime, source_id=SOURCE_ID) == 1
        assert len(runtime._raw_ear_temporal_registry) == 0
    finally:
        runtime.store.close()


def test_consent_revocation_clears_default_temporal_state_before_resume(tmp_path):
    runtime, event = make_runtime(tmp_path)
    short_tone = tone(140, sample_rate=16000, seconds=0.04)
    try:
        first = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
        )
        assert first["a4"]["temporal_voice"]["voice_active"] is False
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, short_tone, sample_rate=16000, start_ms=140,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=lambda source, receipt: False,
                finality="FINAL", token_budget=512,
            )
        resumed = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="FINAL", token_budget=512,
        )
        assert resumed["a4"]["temporal_voice"]["voice_active"] is False
        assert resumed["a4"]["temporal_voice"]["voice_onset"] is False
        assert len(runtime._raw_ear_temporal_registry) == 1
        assert packet_count(runtime.store, event["event_id"]) == 2
    finally:
        runtime.store.close()


def test_consent_revocation_resets_caller_supplied_temporal_state(tmp_path):
    runtime, event = make_runtime(tmp_path)
    state = TemporalVoiceEvidence()
    short_tone = tone(140, sample_rate=16000, seconds=0.04)
    try:
        first = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, temporal_state=state,
            finality="FINAL", token_budget=512,
        )
        assert first["a4"]["temporal_voice"]["voice_active"] is False
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, short_tone, sample_rate=16000, start_ms=140,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=lambda source, receipt: False,
                temporal_state=state, finality="FINAL", token_budget=512,
            )
        resumed = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, temporal_state=state,
            finality="FINAL", token_budget=512,
        )
        assert resumed["a4"]["temporal_voice"]["voice_active"] is False
        assert resumed["a4"]["temporal_voice"]["voice_onset"] is False
    finally:
        runtime.store.close()


def test_consent_revocation_between_pre_and_post_persist_leaves_no_packet(tmp_path):
    """Revocation at the post-write check must not leave a persisted audio packet.

    This is a privacy gate: packet commit and consent revocation need one ordering point.
    """
    runtime, event = make_runtime(tmp_path)
    calls = 0

    def revoke_after_pre_persist_checks(source_id, receipt):
        nonlocal calls
        calls += 1
        # The producer checks before packet construction and again after
        # validating the Store/event binding. Revoke at its post-write check.
        return calls <= 2

    try:
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=revoke_after_pre_persist_checks,
                finality="FINAL", token_budget=512,
            )
        assert calls == 3
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()
