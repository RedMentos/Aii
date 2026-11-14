"""Consent-gated, source-bound timed RAW EAR packet contract (synthetic stage).

No microphone access, ASR, speaker identification, or native Android claims.
Pure standard-library adapter for A5 consumers; retains non-verbal acoustics.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from math import isfinite
from typing import Optional


@dataclass(frozen=True)
class EarFrame:
    source_id: str
    start_ms: int
    end_ms: int
    rms: float
    pitch_hz: Optional[float] = None
    voiced_probability: Optional[float] = None
    non_speech_label: Optional[str] = None
    speaker_hint: Optional[str] = None
    transcript: Optional[str] = None
    teacher_revision: Optional[str] = None
    final: bool = False


def to_percept_packet(frame: EarFrame, *, consent: bool, source_authorized: bool) -> dict:
    """Produce a JSON-compatible A5 proposal; never grants model/action authority."""
    if not consent or not source_authorized:
        raise PermissionError("RAW_EAR_CONSENT_REQUIRED")
    if not frame.source_id or len(frame.source_id) > 128:
        raise ValueError("invalid source id")
    if not (isinstance(frame.start_ms, int) and isinstance(frame.end_ms, int)
            and 0 <= frame.start_ms < frame.end_ms):
        raise ValueError("invalid monotonic interval")
    if frame.end_ms - frame.start_ms > 30_000:
        raise ValueError("audio frame exceeds bounded duration")
    for name, value in (("rms", frame.rms), ("pitch_hz", frame.pitch_hz),
                        ("voiced_probability", frame.voiced_probability)):
        if value is not None and (not isinstance(value, (int, float)) or not isfinite(value)):
            raise ValueError("nonfinite " + name)
    if not 0 <= frame.rms <= 1:
        raise ValueError("rms outside normalized range")
    if frame.pitch_hz is not None and not 0 <= frame.pitch_hz <= 5000:
        raise ValueError("pitch outside bounded range")
    if frame.voiced_probability is not None and not 0 <= frame.voiced_probability <= 1:
        raise ValueError("invalid voiced probability")
    if frame.transcript is not None and not frame.teacher_revision:
        raise ValueError("teacher transcript requires provenance")
    if frame.teacher_revision and not frame.transcript:
        raise ValueError("teacher provenance without transcript")
    if frame.transcript is not None and len(frame.transcript) > 4096:
        raise ValueError("unbounded transcript")
    for value in (frame.non_speech_label, frame.speaker_hint, frame.teacher_revision):
        if value is not None and len(value) > 128:
            raise ValueError("unbounded annotation")
    return {
        "schema": "v13.a5.raw-ear/1",
        "source": {"id": frame.source_id, "modality": "audio", "authorized": True},
        "interval_ms": [frame.start_ms, frame.end_ms],
        "status": "FINAL" if frame.final else "PROVISIONAL",
        "acoustics": {"rms": frame.rms, "pitch_hz": frame.pitch_hz,
                      "voiced_probability": frame.voiced_probability,
                      "non_speech": frame.non_speech_label,
                      "speaker_hint_unverified": frame.speaker_hint},
        "teacher": ({"text": frame.transcript, "revision": frame.teacher_revision}
                    if frame.transcript is not None else None),
        "gate": "SYNTHETIC_CONTRACT_ONLY",
        "action_authority": False,
        "learning_authority": False,
    }
