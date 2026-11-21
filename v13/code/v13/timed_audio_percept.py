"""Bounded, consent-bound A-plane acoustic observation contract (no microphone access).

This module accepts *derived* features, not raw audio, transcripts or speaker identity.
An Android permission broker must enforce capture permission independently.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Optional


@dataclass(frozen=True)
class TimedAudioPercept:
    source_id: str
    start_ms: int
    end_ms: int
    consent_scope: str
    provenance: str  # raw_ear_derived | teacher_ear
    status: str  # provisional | final
    rms: float
    pitch_hz: Optional[float]
    speech_probability: float
    non_speech_probability: float
    prosody_change: float
    speaker_turn: bool
    teacher_text: Optional[str] = None

    def __post_init__(self):
        if not self.source_id or len(self.source_id) > 96 or any(c.isspace() for c in self.source_id):
            raise ValueError("invalid source_id")
        if self.start_ms < 0 or self.end_ms <= self.start_ms or self.end_ms - self.start_ms > 10000:
            raise ValueError("invalid audio interval")
        if self.consent_scope != "audio_observation_granted":
            raise PermissionError("audio observation consent absent")
        if self.provenance not in ("raw_ear_derived", "teacher_ear"):
            raise ValueError("unknown provenance")
        if self.status not in ("provisional", "final"):
            raise ValueError("unknown status")
        for name in ("rms", "speech_probability", "non_speech_probability", "prosody_change"):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError("invalid " + name)
        if self.pitch_hz is not None and (not isfinite(self.pitch_hz) or not 0 <= self.pitch_hz <= 4000):
            raise ValueError("invalid pitch")
        if self.teacher_text is not None:
            if self.provenance != "teacher_ear" or len(self.teacher_text) > 512:
                raise ValueError("untrusted teacher transcript")

    def bounded_context(self) -> dict:
        """Non-transcript, non-identity metadata for A5/JEF; no raw PCM."""
        return {
            "source_id": self.source_id,
            "interval_ms": [self.start_ms, self.end_ms],
            "modality": "audio",
            "provenance": self.provenance,
            "status": self.status,
            "speech_probability": round(self.speech_probability, 3),
            "non_speech_probability": round(self.non_speech_probability, 3),
            "prosody_change": round(self.prosody_change, 3),
            "speaker_turn": self.speaker_turn,
            "teacher_text_available": self.teacher_text is not None,
        }
