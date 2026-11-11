"""Age-0 RAW EAR timed acoustic percept contract (synthetic, no microphone authority).

Keeps acoustic evidence separate from optional ASR; downstream B/C may consume
only explicit, source-bound views. No audio capture, speaker identity inference,
or consent verification is provided here.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Optional
import hashlib
import json

MAX_FRAMES = 4096
MAX_DURATION_MS = 120_000
MAX_SOURCE_CHARS = 256

@dataclass(frozen=True)
class AcousticFrame:
    start_ms: int
    end_ms: int
    rms: float
    pitch_hz: Optional[float]
    voiced_probability: float
    non_speech_probability: float

@dataclass(frozen=True)
class RawEarPacket:
    source_ref: str
    source_sha256: str
    sample_rate_hz: int
    duration_ms: int
    frames: tuple[AcousticFrame, ...]
    provisional: bool
    asr_text: Optional[str] = None
    asr_teacher_id: Optional[str] = None

    def to_record(self) -> dict:
        return {
            "schema": "v13.raw_ear.v0",
            "source_ref": self.source_ref,
            "source_sha256": self.source_sha256,
            "sample_rate_hz": self.sample_rate_hz,
            "duration_ms": self.duration_ms,
            "frames": [vars(f) for f in self.frames],
            "provenance": "provisional" if self.provisional else "final",
            "asr": None if self.asr_text is None else {
                "text": self.asr_text, "teacher_id": self.asr_teacher_id},
            "modality": "audio_acoustic",
            "android_capture_verified": False,
        }

def build_raw_ear(source_ref: str, pcm16le: bytes, sample_rate_hz: int,
                  frames: tuple[AcousticFrame, ...], *,
                  provisional: bool = True,
                  asr_text: Optional[str] = None,
                  asr_teacher_id: Optional[str] = None) -> RawEarPacket:
    if not isinstance(source_ref, str) or not source_ref or len(source_ref) > MAX_SOURCE_CHARS:
        raise ValueError("bounded source_ref required")
    if not isinstance(pcm16le, bytes) or not pcm16le or len(pcm16le) % 2:
        raise ValueError("nonempty PCM16LE byte pairs required")
    if type(sample_rate_hz) is not int or sample_rate_hz not in (8000, 16000, 24000, 48000):
        raise ValueError("unsupported sample rate")
    samples = len(pcm16le) // 2
    duration_ms = samples * 1000 // sample_rate_hz
    if duration_ms < 1 or duration_ms > MAX_DURATION_MS:
        raise ValueError("audio duration outside bounds")
    if not isinstance(frames, tuple) or not (1 <= len(frames) <= MAX_FRAMES):
        raise ValueError("bounded acoustic frames required")
    previous = 0
    for f in frames:
        if not isinstance(f, AcousticFrame) or any(type(x) is not int for x in (f.start_ms, f.end_ms)):
            raise ValueError("invalid frame type")
        if f.start_ms < previous or f.end_ms <= f.start_ms or f.end_ms > duration_ms:
            raise ValueError("invalid or overlapping timestamps")
        previous = f.end_ms
        for v in (f.rms, f.voiced_probability, f.non_speech_probability):
            if not isinstance(v, (int, float)) or not isfinite(v) or not 0 <= v <= 1:
                raise ValueError("invalid acoustic probability or RMS")
        if f.pitch_hz is not None and (
            not isinstance(f.pitch_hz, (int, float)) or not isfinite(f.pitch_hz)
            or not 20 <= f.pitch_hz <= 2000):
            raise ValueError("invalid pitch")
    if (asr_text is None) != (asr_teacher_id is None):
        raise ValueError("ASR transcript must be teacher-bound")
    if asr_text is not None and (
        not isinstance(asr_text, str) or len(asr_text) > 8192 or
        not isinstance(asr_teacher_id, str) or not asr_teacher_id):
        raise ValueError("invalid ASR provenance")
    return RawEarPacket(source_ref, hashlib.sha256(pcm16le).hexdigest(),
                        sample_rate_hz, duration_ms, frames, provisional,
                        asr_text, asr_teacher_id)

def encode_record(packet: RawEarPacket) -> str:
    return json.dumps(packet.to_record(), sort_keys=True, separators=(",", ":"))
