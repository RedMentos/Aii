"""Synthetic contract and stream-state tests for the optional Silero ONNX adapter."""
import hashlib
import struct

import numpy as np
import pytest

from v13.audio_silero_vad import SileroVADStream, validate_vad_evidence


class FakeSileroSession:
    def __init__(self, *, bad_state=False, bad_score=False):
        self.calls = []
        self.bad_state = bad_state
        self.bad_score = bad_score

    def run(self, output_names, inputs):
        self.calls.append(inputs)
        frame = inputs["input"][:, 64:]
        rms = float(np.sqrt(np.mean(frame * frame)))
        score = 0.9 if rms >= 0.08 else 0.1
        if self.bad_score:
            score = float("nan")
        state = inputs["state"] + 1.0
        if self.bad_state:
            state = np.zeros((1, 128), dtype=np.float32)
        return [np.asarray([[score]], dtype=np.float32), state]


def pcm_tone(samples=16000, amplitude=12000, frequency=140, sample_rate=16000):
    values = [
        int(amplitude * np.sin(2 * np.pi * frequency * i / sample_rate))
        for i in range(samples)
    ]
    return struct.pack("<" + "h" * len(values), *values)


def make_stream(session=None, **kwargs):
    return SileroVADStream(
        session or FakeSileroSession(),
        model_sha256="a" * 64,
        model_revision="fixture-silero-vad",
        **kwargs,
    )


def test_one_second_window_keeps_partial_frame_and_next_window_completes_it():
    session = FakeSileroSession()
    vad = make_stream(session)
    first = vad.push_pcm16(
        pcm_tone(), sample_rate=16000, stream_id="source-A", start_ms=100
    )
    assert first["state_reset_reason"] == "NEW_STREAM"
    assert first["frame_count"] == 31
    assert first["covered_ms"] == 992
    assert first["pending_samples"] == 128
    assert first["speech_fraction"] == 1.0
    assert first["mean_score"] == pytest.approx(0.9, abs=1e-6)
    assert first["first_frame_start_ms"] == 100
    assert first["last_frame_end_ms"] == 1092
    second = vad.push_pcm16(
        pcm_tone(samples=384), sample_rate=16000, stream_id="source-A", start_ms=1100
    )
    assert second["state_reset_reason"] is None
    assert second["frame_count"] == 1
    assert second["first_frame_start_ms"] == 1092
    assert second["last_frame_end_ms"] == 1124
    assert second["pending_samples"] == 0
    assert len(session.calls) == 32


def test_silence_and_speech_are_separate_model_scores():
    vad = make_stream()
    silence = bytes(512 * 2)
    speech = pcm_tone(samples=512)
    first = vad.push_pcm16(silence, sample_rate=16000, stream_id="s", start_ms=0)
    second = vad.push_pcm16(speech, sample_rate=16000, stream_id="s", start_ms=32)
    assert first["speech_fraction"] == 0.0
    assert first["speech_detected"] is False
    assert second["speech_fraction"] == 1.0
    assert second["speech_detected"] is True


def test_stream_change_resets_recurrent_state_and_partial_pcm():
    session = FakeSileroSession()
    vad = make_stream(session)
    vad.push_pcm16(pcm_tone(samples=128), sample_rate=16000, stream_id="s1", start_ms=0)
    assert vad.pending_samples == 128
    changed = vad.push_pcm16(
        pcm_tone(samples=512), sample_rate=16000, stream_id="s2", start_ms=500
    )
    assert changed["state_reset_reason"] == "STREAM_CHANGED"
    assert changed["frame_count"] == 1
    assert changed["first_frame_start_ms"] == 500
    assert vad.pending_samples == 0
    assert float(session.calls[-1]["state"].sum()) == 0.0


def test_time_discontinuity_resets_state_instead_of_bridging_missing_audio():
    session = FakeSileroSession()
    vad = make_stream(session)
    vad.push_pcm16(pcm_tone(512), sample_rate=16000, stream_id="s", start_ms=0)
    after_gap = vad.push_pcm16(
        pcm_tone(512), sample_rate=16000, stream_id="s", start_ms=500
    )
    assert after_gap["state_reset_reason"] == "TIME_DISCONTINUITY"
    assert float(session.calls[-1]["state"].sum()) == 0.0


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"sample_rate": 8000}, "16000 Hz"),
        ({"sample_rate": 16000, "stream_id": ""}, "stream_id"),
        ({"sample_rate": 16000, "start_ms": -1}, "start_ms"),
    ],
)
def test_invalid_stream_metadata_is_rejected(kwargs, message):
    vad = make_stream()
    args = {"sample_rate": 16000, "stream_id": "s", "start_ms": 0}
    args.update(kwargs)
    with pytest.raises(ValueError, match=message):
        vad.push_pcm16(pcm_tone(samples=512), **args)


def test_partial_pcm16_bytes_and_overlong_window_are_rejected():
    vad = make_stream()
    with pytest.raises(ValueError, match="complete PCM16"):
        vad.push_pcm16(b"\x00", sample_rate=16000, stream_id="s", start_ms=0)
    with pytest.raises(ValueError, match="one second"):
        vad.push_pcm16(
            bytes(16001 * 2), sample_rate=16000, stream_id="s", start_ms=0
        )


def test_bad_model_outputs_reset_stream_and_fail_closed():
    bad_score = make_stream(FakeSileroSession(bad_score=True))
    with pytest.raises(RuntimeError, match="invalid VAD score"):
        bad_score.push_pcm16(
            pcm_tone(samples=512), sample_rate=16000, stream_id="s", start_ms=0
        )
    assert bad_score.pending_samples == 0
    bad_state = make_stream(FakeSileroSession(bad_state=True))
    with pytest.raises(RuntimeError, match="invalid recurrent state"):
        bad_state.push_pcm16(
            pcm_tone(samples=512), sample_rate=16000, stream_id="s", start_ms=0
        )
    assert bad_state.pending_samples == 0


def test_evidence_validator_rejects_tampering():
    evidence = make_stream().push_pcm16(
        pcm_tone(samples=512), sample_rate=16000, stream_id="s", start_ms=0
    )
    malformed = dict(evidence, model_sha256="not-a-digest")
    with pytest.raises(ValueError, match="digest"):
        validate_vad_evidence(malformed)
    malformed = dict(evidence, covered_ms=31)
    with pytest.raises(ValueError, match="coverage"):
        validate_vad_evidence(malformed)


def test_from_onnx_checks_hash_before_optional_runtime_import(tmp_path):
    model = tmp_path / "silero_vad.onnx"
    model.write_bytes(b"fixture model bytes" * 100)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        SileroVADStream.from_onnx(
            model, expected_sha256="0" * 64, model_revision="fixture"
        )


def test_from_onnx_rejects_symlink(tmp_path):
    model = tmp_path / "silero_vad.onnx"
    model.write_bytes(b"fixture model bytes" * 100)
    link = tmp_path / "link.onnx"
    link.symlink_to(model)
    with pytest.raises(ValueError, match="symlink"):
        SileroVADStream.from_onnx(
            link, expected_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
            model_revision="fixture",
        )
