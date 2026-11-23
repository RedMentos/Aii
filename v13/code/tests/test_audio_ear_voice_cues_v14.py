"""Synthetic RAW EAR voice-cue extraction and real A4/C3 adapter regressions."""
from concurrent.futures import ThreadPoolExecutor
import math
import random
import struct
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
import numpy as np

from v13 import audio_voice_cues as audio_voice_cues_module
from v13.audio_silero_vad import SileroVADStream
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


def _guard_for(check):
    """Non-racing fixture lease; concurrency tests use a shared provider below."""
    lock = threading.RLock()

    @contextmanager
    def lease(source_id, receipt):
        with lock:
            yield check(source_id, receipt)

    return lease


class _LinearizableConsentProvider:
    """Test provider whose check, lease and revoke share one lock."""

    def __init__(self):
        self._lock = threading.RLock()
        self._active = True

    def check(self, source_id, receipt):
        with self._lock:
            return self._active and source_id == SOURCE_ID and receipt == RECEIPT

    @contextmanager
    def lease(self, source_id, receipt):
        with self._lock:
            yield self._active and source_id == SOURCE_ID and receipt == RECEIPT

    def revoke(self):
        with self._lock:
            self._active = False


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



@pytest.mark.parametrize("sample_rate", (8000, 12000, 16000, 44100, 48000))
def test_numpy_pitch_backend_matches_python_for_synthetic_controls(sample_rate):
    fixtures = (
        tone(140, sample_rate=sample_rate),
        sweep_tone(sample_rate=sample_rate),
        amplitude_burst(sample_rate=sample_rate),
        white_noise(sample_rate=sample_rate),
        silence_padded_tone(sample_rate=sample_rate),
        tone(180, sample_rate=sample_rate, seconds=0.04),
    )
    for pcm in fixtures:
        assert extract_voice_cues(pcm, sample_rate, backend="numpy") == extract_voice_cues(
            pcm, sample_rate, backend="python"
        )


def test_numpy_backend_is_explicit_and_falls_back_without_changing_python(monkeypatch):
    pcm = tone(140)
    expected = extract_voice_cues(pcm, 16000, backend="python")
    monkeypatch.setattr(audio_voice_cues_module, "_load_numpy", lambda: None)
    with pytest.raises(RuntimeError, match="NumPy voice cue backend is unavailable"):
        extract_voice_cues(pcm, 16000, backend="numpy")
    assert extract_voice_cues(pcm, 16000, backend="python") == expected
    with pytest.raises(ValueError, match="voice cue backend"):
        extract_voice_cues(pcm, 16000, backend="fast")

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


@pytest.mark.parametrize("voice_backend", ("python", "numpy"))
def test_voice_cues_flow_to_real_a4_and_c3_without_raw_pcm_or_identity(tmp_path, voice_backend):
    runtime, event = make_runtime(tmp_path)
    pcm = tone(140)
    try:
        result = consume_pcm16_voice_window(
            runtime, pcm, sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
            voice_backend=voice_backend,
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
        assert "pitch" not in segment["unmeasured"]
        assert "prosody" not in segment["unmeasured"]
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
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
        )
        score = result["a4"]["prosody_change_score"]
        assert score > 0.6
        assert observed["novelty"] >= 0.9 * score
        assert observed["external_interrupt"] >= 0.25 * score
        assert result["a4"]["attention"] == {"captured": True}
        assert "prosody_change=" in result["c3_admission"].selected[0].summary
    finally:
        runtime.store.close()


def test_silent_audio_marks_pitch_and_prosody_unmeasured(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, bytes(2 * 16000), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok),
            finality="FINAL", token_budget=512,
        )
        segment = result["packet"]["segments"][0]
        cues = segment["acoustic"]["voice_cues"]
        assert cues["activity_hint"] == "SILENCE"
        assert cues["f0_median_hz"] is None
        assert "pitch" in segment["unmeasured"]
        assert "prosody" in segment["unmeasured"]
        assert "calibrated_speech_probability" in segment["unmeasured"]
        assert packet_count(runtime.store, event["event_id"]) == 1
    finally:
        runtime.store.close()


def test_single_voiced_frame_measures_pitch_but_not_prosody(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(140, sample_rate=16000, seconds=0.04),
            sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok),
            finality="FINAL", token_budget=512,
        )
        segment = result["packet"]["segments"][0]
        cues = segment["acoustic"]["voice_cues"]
        assert cues["f0_median_hz"] is not None
        assert "pitch" not in segment["unmeasured"]
        assert "prosody" in segment["unmeasured"]
    finally:
        runtime.store.close()


def test_provisional_voice_cues_remain_a4_only(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(140), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="PROVISIONAL", token_budget=512,
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
                consent_check=lambda source, receipt: False, consent_guard=_guard_for(lambda source, receipt: False),
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
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
            temporal_state=state,
        )
        second = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
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
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
        )
        second = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
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
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
        )
        assert first["a4"]["temporal_voice"]["voice_active"] is False
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, short_tone, sample_rate=16000, start_ms=140,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=lambda source, receipt: False, consent_guard=_guard_for(lambda source, receipt: False),
                finality="FINAL", token_budget=512,
            )
        resumed = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
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
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), temporal_state=state,
            finality="FINAL", token_budget=512,
        )
        assert first["a4"]["temporal_voice"]["voice_active"] is False
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, short_tone, sample_rate=16000, start_ms=140,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=lambda source, receipt: False, consent_guard=_guard_for(lambda source, receipt: False),
                temporal_state=state, finality="FINAL", token_budget=512,
            )
        resumed = consume_pcm16_voice_window(
            runtime, short_tone, sample_rate=16000, start_ms=140,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), temporal_state=state,
            finality="FINAL", token_budget=512,
        )
        assert resumed["a4"]["temporal_voice"]["voice_active"] is False
        assert resumed["a4"]["temporal_voice"]["voice_onset"] is False
    finally:
        runtime.store.close()


class _FakeSileroSession:
    def __init__(self):
        self.calls = []

    def run(self, output_names, inputs):
        self.calls.append(inputs)
        frame = inputs["input"][:, 64:]
        rms = float(np.sqrt(np.mean(frame * frame)))
        score = 0.9 if rms >= 0.08 else 0.1
        return [np.asarray([[score]], dtype=np.float32), inputs["state"] + 1.0]


def test_optional_silero_vad_is_source_bound_and_reaches_a4_c3(tmp_path):
    runtime, event = make_runtime(tmp_path)
    session = _FakeSileroSession()
    vad = SileroVADStream(
        session, model_sha256="b" * 64, model_revision="synthetic-fixture"
    )
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(140), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
            vad_stream=vad,
        )
        evidence = result["vad_evidence"]
        segment = result["packet"]["segments"][0]
        cues = segment["acoustic"]["voice_cues"]
        assert evidence["method"] == "SILERO_VAD_ONNX"
        assert evidence["model_sha256"] == "b" * 64
        assert evidence["frame_count"] == 31
        assert evidence["speech_fraction"] == 1.0
        assert evidence["pending_samples"] == 128
        assert cues["vad"] == evidence
        assert result["a4"]["vad_evidence"] == evidence
        assert "vad_speech_fraction=1.00" in result["c3_admission"].selected[0].summary
        assert result["a4"]["learning_authority"] is False
        assert result["a4"]["action_authority"] is False
        assert segment["asr_transcript"] is None
        assert "pcm16" not in segment
        assert packet_count(runtime.store, event["event_id"]) == 1
        assert attention_count(runtime.store, event["event_id"]) == 1
    finally:
        runtime.store.close()


def test_consent_revocation_resets_optional_silero_stream_before_resume(tmp_path):
    runtime, event = make_runtime(tmp_path)
    vad = SileroVADStream(
        _FakeSileroSession(), model_sha256="c" * 64, model_revision="synthetic-fixture"
    )
    try:
        vad.push_pcm16(
            tone(140, seconds=0.04), sample_rate=16000,
            stream_id=SOURCE_ID + ":" + event["brain_generation_id"], start_ms=100,
        )
        assert vad.pending_samples > 0
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, tone(140, seconds=0.04), sample_rate=16000, start_ms=140,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=lambda source, receipt: False, consent_guard=_guard_for(lambda source, receipt: False),
                finality="FINAL", token_budget=512, vad_stream=vad,
            )
        assert vad.pending_samples == 0
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_optional_silero_rejects_non_16khz_before_packet_or_attention(tmp_path):
    runtime, event = make_runtime(tmp_path)
    vad = SileroVADStream(
        _FakeSileroSession(), model_sha256="d" * 64, model_revision="synthetic-fixture"
    )
    try:
        with pytest.raises(ValueError, match="16000 Hz"):
            consume_pcm16_voice_window(
                runtime, tone(140, sample_rate=8000), sample_rate=8000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=_guard_for(consent_ok), finality="FINAL", token_budget=512,
                vad_stream=vad,
            )
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()



def test_audio_packet_fails_closed_without_linearizable_consent_lease(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    vad = SileroVADStream(
        _FakeSileroSession(), model_sha256="e" * 64, model_revision="synthetic-fixture"
    )
    vad.push_pcm16(
        tone(140, seconds=0.04), sample_rate=16000,
        stream_id=SOURCE_ID + ":" + event["brain_generation_id"], start_ms=60,
    )
    assert vad.pending_samples > 0
    state = TemporalVoiceEvidence()
    state.update(
        source_id=SOURCE_ID, generation_id=event["brain_generation_id"],
        start_ms=0, end_ms=100,
        cues={"activity_hint": "VOICED", "activity_score": 0.9},
    )
    monkeypatch.setattr(
        audio_voice_cues_module, "admit",
        lambda *args, **kwargs: pytest.fail("C3 admission must not run without a lease"),
    )
    try:
        with pytest.raises(PermissionError, match="linearizable audio consent lease"):
            consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=consent_ok, finality="FINAL", token_budget=512,
                vad_stream=vad, temporal_state=state,
            )
        assert vad.pending_samples == 0
        # The same window can be accepted after reset; stale temporal state is gone.
        resumed = state.update(
            source_id=SOURCE_ID, generation_id=event["brain_generation_id"],
            start_ms=0, end_ms=100,
            cues={"activity_hint": "VOICED", "activity_score": 0.9},
        )
        assert resumed["voice_active"] is True
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
        assert getattr(runtime, "_raw_ear_temporal_registry", None) is None
    finally:
        runtime.store.close()


def test_provider_revocation_winning_before_lease_has_no_audio_side_effects(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    provider = _LinearizableConsentProvider()
    provider.revoke()
    monkeypatch.setattr(
        audio_voice_cues_module, "admit",
        lambda *args, **kwargs: pytest.fail("C3 admission must not run after revocation"),
    )
    try:
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=provider.check, consent_guard=provider.lease, finality="FINAL", token_budget=512,
            )
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
        assert getattr(runtime, "_raw_ear_temporal_registry", None) is None
    finally:
        runtime.store.close()



def test_linearizable_lease_blocks_revocation_before_sqlite_commit(tmp_path):
    runtime, event = make_runtime(tmp_path)
    provider = _LinearizableConsentProvider()
    at_commit = threading.Event()
    allow_commit = threading.Event()
    revoke_started = threading.Event()
    revoke_finished = threading.Event()
    original_tx = runtime.store.tx
    blocked_once = False

    @contextmanager
    def block_before_first_commit():
        nonlocal blocked_once
        with original_tx() as connection:
            yield connection
            if not blocked_once:
                blocked_once = True
                at_commit.set()
                if not allow_commit.wait(5):
                    raise TimeoutError("test did not release blocked SQLite commit")

    runtime.store.tx = block_before_first_commit

    def revoke():
        revoke_started.set()
        provider.revoke()
        revoke_finished.set()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            consumer = pool.submit(
                consume_pcm16_voice_window,
                runtime, tone(140),
                sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=provider.check, consent_guard=provider.lease,
                finality="FINAL", token_budget=512,
            )
            assert at_commit.wait(5)
            revoker = pool.submit(revoke)
            assert revoke_started.wait(5)
            # The provider lease remains held through the Store transaction and COMMIT.
            assert not revoke_finished.wait(0.05)
            allow_commit.set()
            result = consumer.result(timeout=5)
            revoker.result(timeout=5)

        assert revoke_finished.is_set()
        assert provider.check(SOURCE_ID, RECEIPT) is False
        assert result["c3_admission"].status == "ADMITTED"
        assert packet_count(runtime.store, event["event_id"]) == 1
        assert attention_count(runtime.store, event["event_id"]) == 1
    finally:
        allow_commit.set()
        runtime.store.close()

def test_linearizable_lease_serializes_revocation_through_a4_and_c3(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    provider = _LinearizableConsentProvider()
    entered_attention = threading.Event()
    allow_attention = threading.Event()
    revoke_started = threading.Event()
    revoke_finished = threading.Event()
    real_attention = audio_voice_cues_module.attctl.controller(runtime)

    class BlockingAttention:
        def modulate(self, event_id, *, sal):
            entered_attention.set()
            if not allow_attention.wait(5):
                raise TimeoutError("test did not release blocked attention")
            return real_attention.modulate(event_id, sal=sal)

    blocking_attention = BlockingAttention()
    monkeypatch.setattr(
        audio_voice_cues_module.attctl, "controller",
        lambda _runtime: blocking_attention,
    )

    def revoke():
        revoke_started.set()
        provider.revoke()
        revoke_finished.set()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            consumer = pool.submit(
                consume_pcm16_voice_window,
                runtime, tone(140),
                sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=provider.check, consent_guard=provider.lease,
                finality="FINAL", token_budget=512,
            )
            assert entered_attention.wait(5)
            revoker = pool.submit(revoke)
            assert revoke_started.wait(5)
            # Revocation cannot linearize while the producer owns the lease.
            assert not revoke_finished.wait(0.05)
            allow_attention.set()
            result = consumer.result(timeout=5)
            revoker.result(timeout=5)

        assert revoke_finished.is_set()
        assert provider.check(SOURCE_ID, RECEIPT) is False
        assert result["c3_admission"].status == "ADMITTED"
        assert packet_count(runtime.store, event["event_id"]) == 1
        assert attention_count(runtime.store, event["event_id"]) == 1
    finally:
        allow_attention.set()
        runtime.store.close()

def test_store_commit_failure_rolls_back_audio_packet_before_attention(tmp_path, monkeypatch):
    """A Store failure rolls back the packet while the real consent lease is held."""
    runtime, event = make_runtime(tmp_path)
    provider = _LinearizableConsentProvider()
    original_tx = runtime.store.tx

    @contextmanager
    def fail_before_commit():
        with original_tx() as connection:
            yield connection
            raise OSError("synthetic Store commit failure")

    runtime.store.tx = fail_before_commit
    monkeypatch.setattr(
        audio_voice_cues_module, "admit",
        lambda *args, **kwargs: pytest.fail("C3 admission must not run after Store failure"),
    )
    try:
        with pytest.raises(OSError, match="synthetic Store commit failure"):
            consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=provider.check, consent_guard=provider.lease,
                finality="FINAL", token_budget=512,
            )
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_consent_revocation_after_preflight_before_lease_cannot_process_pcm(tmp_path, monkeypatch):
    """A revoke completed in the preflight/lease gap must prevent all PCM work."""
    runtime, event = make_runtime(tmp_path)
    provider = _LinearizableConsentProvider()
    processed = []
    revoked = False
    original_require = audio_voice_cues_module._require_current_consent_and_reset
    original_observe = audio_voice_cues_module.observe_pcm16
    original_extract = audio_voice_cues_module.extract_voice_cues

    def revoke_after_preflight(
        runtime_arg, source_id, generation_id, consent_check, receipt,
        temporal_state=None, vad_stream=None,
    ):
        nonlocal revoked
        result = original_require(
            runtime_arg, source_id, generation_id, consent_check, receipt,
            temporal_state, vad_stream,
        )
        if not revoked:
            # The initial metadata-only check has returned and no processing
            # lease has yet been acquired. Complete revocation at this exact
            # linearization point, without scheduler sleeps or timing guesses.
            provider.revoke()
            revoked = True
        return result

    def observe(*args, **kwargs):
        processed.append("observe_pcm16")
        return original_observe(*args, **kwargs)

    def extract(*args, **kwargs):
        processed.append("extract_voice_cues")
        return original_extract(*args, **kwargs)

    monkeypatch.setattr(
        audio_voice_cues_module,
        "_require_current_consent_and_reset",
        revoke_after_preflight,
    )
    monkeypatch.setattr(audio_voice_cues_module, "observe_pcm16", observe)
    monkeypatch.setattr(audio_voice_cues_module, "extract_voice_cues", extract)

    try:
        with pytest.raises(PermissionError):
            consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=provider.check, consent_guard=provider.lease,
                finality="FINAL", token_budget=512,
            )

        assert revoked is True
        assert provider.check(SOURCE_ID, RECEIPT) is False
        assert processed == [], "RAW EAR processed PCM after revocation had completed"
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


class _NonReentrantConsentProvider:
    """Models a normal threading.Lock-backed provider (not an RLock)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._owner = None
        self._active = True

    @contextmanager
    def _locked(self):
        ident = threading.get_ident()
        if self._owner == ident:
            raise RuntimeError("provider lock must not be reacquired under its lease")
        self._lock.acquire()
        self._owner = ident
        try:
            yield
        finally:
            self._owner = None
            self._lock.release()

    def check(self, source_id, receipt):
        with self._locked():
            return self._active and source_id == SOURCE_ID and receipt == RECEIPT

    @contextmanager
    def lease(self, source_id, receipt):
        with self._locked():
            yield self._active and source_id == SOURCE_ID and receipt == RECEIPT

    def revoke(self):
        with self._locked():
            self._active = False


def test_consent_lease_does_not_reacquire_a_non_reentrant_provider_lock(tmp_path):
    """The guard's yielded authorization must suffice while its provider lock is held."""
    runtime, event = make_runtime(tmp_path)
    provider = _NonReentrantConsentProvider()
    try:
        result = consume_pcm16_voice_window(
            runtime, tone(140), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=provider.check, consent_guard=provider.lease,
            finality="FINAL", token_budget=512,
        )
        assert result["c3_admission"] is not None
        assert packet_count(runtime.store, event["event_id"]) == 1
        assert attention_count(runtime.store, event["event_id"]) == 1
        provider.revoke()
        assert provider.check(SOURCE_ID, RECEIPT) is False
    finally:
        runtime.store.close()


# Shared Runtime/C3 lease API: caller can hold one non-reentrant provider lock
# beyond PerceptPacket/A4/C3 admission and through the complete C3 generation.
from v13.audio_voice_cues import AudioConsentLease, audio_consent_lease


def test_outer_audio_lease_reuses_non_reentrant_provider_lock(tmp_path):
    runtime, event = make_runtime(tmp_path)
    provider = _NonReentrantConsentProvider()
    lease = None
    try:
        with audio_consent_lease(
            runtime, SOURCE_ID, event["brain_generation_id"], RECEIPT,
            provider.check, provider.lease,
        ) as lease:
            assert isinstance(lease, AudioConsentLease)
            assert lease.active is True
            assert lease.matches(
                runtime, SOURCE_ID, event["brain_generation_id"], RECEIPT
            )
            result = consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=100,
                event_id=event["event_id"],
                generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=None, consent_guard=None,
                consent_lease=lease, finality="FINAL", token_budget=512,
            )
            assert result["c3_admission"] is not None
            assert packet_count(runtime.store, event["event_id"]) == 1
            assert attention_count(runtime.store, event["event_id"]) == 1

        assert lease.active is False
        with pytest.raises(PermissionError, match="lease"):
            consume_pcm16_voice_window(
                runtime, tone(140), sample_rate=16000, start_ms=400,
                event_id=event["event_id"],
                generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=None, consent_guard=None,
                consent_lease=lease, finality="FINAL", token_budget=512,
            )
        assert packet_count(runtime.store, event["event_id"]) == 1
    finally:
        runtime.store.close()


def test_outer_audio_lease_rejects_wrong_source_and_boolean_bypass(tmp_path):
    runtime, event = make_runtime(tmp_path)
    provider = _NonReentrantConsentProvider()
    try:
        with audio_consent_lease(
            runtime, SOURCE_ID, event["brain_generation_id"], RECEIPT,
            provider.check, provider.lease,
        ) as lease:
            for source_id, forged in (("other-source", lease), (SOURCE_ID, True)):
                with pytest.raises(PermissionError, match="lease"):
                    consume_pcm16_voice_window(
                        runtime, tone(140), sample_rate=16000, start_ms=100,
                        event_id=event["event_id"],
                        generation_id=event["brain_generation_id"],
                        source_id=source_id, consent_receipt=RECEIPT,
                        consent_check=None, consent_guard=None,
                        consent_lease=forged, finality="FINAL", token_budget=512,
                    )
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


@pytest.mark.parametrize("mismatch", ["source", "receipt"])
def test_outer_audio_lease_rejects_runtime_binding_mismatch(tmp_path, monkeypatch, mismatch):
    runtime, event = make_runtime(tmp_path)
    provider = _NonReentrantConsentProvider()
    original = audio_voice_cues_module._validate_runtime_binding

    def mismatched_binding(runtime_arg, event_id, packet):
        source_id, receipt, rms, zcr, segment = original(runtime_arg, event_id, packet)
        if mismatch == "source":
            source_id = "different-source"
        else:
            receipt = "different-receipt"
        return source_id, receipt, rms, zcr, segment

    try:
        with audio_consent_lease(
            runtime, SOURCE_ID, event["brain_generation_id"], RECEIPT,
            provider.check, provider.lease,
        ) as lease:
            monkeypatch.setattr(
                audio_voice_cues_module, "_validate_runtime_binding",
                mismatched_binding,
            )
            with pytest.raises(PermissionError, match="active consent lease"):
                consume_pcm16_voice_window(
                    runtime, tone(140), sample_rate=16000, start_ms=100,
                    event_id=event["event_id"],
                    generation_id=event["brain_generation_id"],
                    source_id=SOURCE_ID, consent_receipt=RECEIPT,
                    consent_check=None, consent_guard=None,
                    consent_lease=lease, finality="FINAL", token_budget=512,
                )
        assert packet_count(runtime.store, event["event_id"]) == 0
        assert attention_count(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_outer_audio_lease_serializes_revoke_until_scope_exit(tmp_path):
    runtime, event = make_runtime(tmp_path)
    provider = _NonReentrantConsentProvider()
    revoke_started = threading.Event()
    revoke_finished = threading.Event()
    revoker = None

    def revoke():
        revoke_started.set()
        provider.revoke()
        revoke_finished.set()

    try:
        with audio_consent_lease(
            runtime, SOURCE_ID, event["brain_generation_id"], RECEIPT,
            provider.check, provider.lease,
        ) as lease:
            assert lease.active is True
            revoker = threading.Thread(target=revoke, daemon=True)
            revoker.start()
            assert revoke_started.wait(2)
            assert not revoke_finished.wait(0.1), (
                "provider revocation completed while Runtime still held the audio lease"
            )
        assert revoke_finished.wait(2)
        assert provider.check(SOURCE_ID, RECEIPT) is False
    finally:
        if revoker is not None:
            revoker.join(timeout=2)
        runtime.store.close()


def test_outer_audio_lease_is_thread_bound_and_nonserializable(tmp_path):
    import pickle

    runtime, event = make_runtime(tmp_path)
    provider = _NonReentrantConsentProvider()
    other_thread_result = []
    try:
        with audio_consent_lease(
            runtime, SOURCE_ID, event["brain_generation_id"], RECEIPT,
            provider.check, provider.lease,
        ) as lease:
            worker = threading.Thread(
                target=lambda: other_thread_result.append(
                    lease.matches(runtime, SOURCE_ID, event["brain_generation_id"], RECEIPT)
                )
            )
            worker.start()
            worker.join(timeout=2)
            assert other_thread_result == [False]
            with pytest.raises(TypeError, match="ephemeral"):
                pickle.dumps(lease)
            assert RECEIPT not in repr(lease)
    finally:
        runtime.store.close()
