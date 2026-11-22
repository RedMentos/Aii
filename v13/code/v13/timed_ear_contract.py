"""Bounded A-plane RAW EAR metadata contract; no microphone acquisition or model inference.

This adapter accepts only locally consented, derived acoustic observations.
No audio bytes, transcript or speaker identity are persisted by this module.
Synthetic tests are not Android microphone or A3 projector evidence.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Optional, Tuple


@dataclass(frozen=True)
class AcousticFrame:
    start_ms: int
    end_ms: int
    rms: float
    pitch_hz: Optional[float]
    speech_probability: float
    non_speech: Tuple[str, ...] = ()
    provisional: bool = True

    def __post_init__(self):
        if not (isinstance(self.start_ms, int) and isinstance(self.end_ms, int)
                and 0 <= self.start_ms < self.end_ms):
            raise ValueError("invalid monotonic audio frame interval")
        for name, value in (("rms", self.rms), ("speech_probability", self.speech_probability)):
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("invalid " + name)
        if self.pitch_hz is not None and (not isfinite(self.pitch_hz) or self.pitch_hz <= 0):
            raise ValueError("invalid pitch")
        if len(self.non_speech) > 8 or any(not isinstance(x, str) or len(x) > 32 for x in self.non_speech):
            raise ValueError("invalid non-speech label")


@dataclass(frozen=True)
class TimedEarPacket:
    source: str
    consent_scope: str
    frames: Tuple[AcousticFrame, ...]
    provenance: str = "synthetic"
    transcript: Optional[str] = None
    teacher_revision: Optional[str] = None

    def __post_init__(self):
        if self.source not in ("synthetic", "authorized_microphone", "authorized_feed"):
            raise ValueError("untrusted source")
        if self.consent_scope not in ("synthetic_test", "audio_observation"):
            raise PermissionError("audio consent missing")
        if self.source != "synthetic" and self.consent_scope != "audio_observation":
            raise PermissionError("live audio requires observation consent")
        if self.source == "synthetic" and self.consent_scope != "synthetic_test":
            raise PermissionError("synthetic provenance mismatch")
        if not 1 <= len(self.frames) <= 128:
            raise ValueError("bounded frame count required")
        if any(a.end_ms > b.start_ms for a, b in zip(self.frames, self.frames[1:])):
            raise ValueError("overlapping or unordered frames")
        if self.transcript is not None and (not self.teacher_revision or len(self.transcript) > 4096):
            raise ValueError("ASR requires bounded teacher provenance")
        if not self.provenance or len(self.provenance) > 128:
            raise ValueError("invalid provenance")

    def percept_packet(self):
        """A5-compatible derived envelope; no raw audio, identities or action authority."""
        return {
            "schema": "v13.a5.timed-ear/1",
            "modality": "audio",
            "source": self.source,
            "consent_scope": self.consent_scope,
            "provenance": self.provenance,
            "provisional": any(f.provisional for f in self.frames),
            "start_ms": self.frames[0].start_ms,
            "end_ms": self.frames[-1].end_ms,
            "acoustics": [
                {"start_ms": f.start_ms, "end_ms": f.end_ms,
                 "rms": f.rms, "pitch_hz": f.pitch_hz,
                 "speech_probability": f.speech_probability,
                 "non_speech": list(f.non_speech), "provisional": f.provisional}
                for f in self.frames
            ],
            "teacher_asr": {"text": self.transcript, "revision": self.teacher_revision}
            if self.transcript is not None else None,
            "a3_projector": "UNAVAILABLE",
            "android_capture": "UNVERIFIED",
            "action_authority": False,
        }
