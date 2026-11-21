"""Synthetic RAW EAR voice-cue extraction and real A4/C3 adapter regressions."""
import math
import random
import struct
from types import SimpleNamespace

import pytest

from v13.audio_voice_cues import (
    consume_pcm16_voice_window,
    extract_voice_cues,
    validate_voice_cues,
)
from v13.store import Store


SOURCE_ID = "fixture:raw-ear-voice"
RECEIPT = "fixture:current-consent"


def tone(frequency=140, sample_rate=16000, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
               for i in range(count)]
    return struct.pack("<" + "h" * count, *samples)


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
        assert result["a4"]["voice_activity_hint"] == "VOICED"
        assert result["a4"]["learning_authority"] is False
        assert result["a4"]["action_authority"] is False
        assert result["c3_admission"].status == "ADMITTED"
        summary = result["c3_admission"].selected[0].summary
        assert "activity=VOICED" in summary and "f0_med_hz=" in summary
        assert segment["asr_transcript"] is None
        assert segment["learning_authority"] is False
        assert segment["action_authority"] is False
        assert "speaker_identity" in segment["unmeasured"]
        assert "speaker_id" not in cues and "speaker_identity" not in cues
        assert cues["method"] == "RAW_EAR_AUTOCORR_V1"
        assert packet_count(runtime.store, event["event_id"]) == 1
        assert attention_count(runtime.store, event["event_id"]) == 1
        digest = result["packet"]["source_ref"]["sha256"]
        assert not (tmp_path / "data" / "blobs" / digest).exists()
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
