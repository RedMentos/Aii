"""Pure synthetic RAW EAR feature adapter to A5 Percept.

No microphone permission, ASR transcript, speaker identity or native proof.
"""
from dataclasses import dataclass
from math import isfinite
from .percept_admission import Percept


@dataclass(frozen=True)
class AcousticFrame:
    source_id: str
    start_ms: int
    end_ms: int
    rms: float
    pitch_hz: float | None
    speech_probability: float
    non_speech: str
    consent: bool
    final: bool


def acoustic_to_percept(frame: AcousticFrame) -> Percept:
    if not frame.source_id or frame.start_ms < 0 or frame.end_ms < frame.start_ms:
        raise ValueError("invalid source/timing")
    if not isfinite(frame.rms) or not 0 <= frame.rms <= 1:
        raise ValueError("invalid rms")
    if frame.pitch_hz is not None and (not isfinite(frame.pitch_hz) or frame.pitch_hz < 0):
        raise ValueError("invalid pitch")
    if not isfinite(frame.speech_probability) or not 0 <= frame.speech_probability <= 1:
        raise ValueError("invalid probability")
    if frame.non_speech not in ("none", "laughter", "breath", "music", "noise", "unknown"):
        raise ValueError("invalid non-speech tag")
    summary = (f"acoustic:rms={frame.rms:.3f};pitch_hz="
               f"{frame.pitch_hz if frame.pitch_hz is not None else 'unknown'};"
               f"speech_probability={frame.speech_probability:.3f};"
               f"non_speech={frame.non_speech};source=synthetic_feature")
    return Percept(frame.source_id, "audio", frame.start_ms, frame.end_ms,
                   summary, frame.consent, frame.final)
