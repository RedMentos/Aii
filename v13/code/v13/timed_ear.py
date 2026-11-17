"""Consent-gated timed RAW EAR acoustic A5 contract. No microphone or ASR access."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class AcousticFrame:
    source_id: str
    start_ms: int
    end_ms: int
    rms: float
    pitch_hz: float | None = None
    speech_probability: float | None = None
    speaker_hint: str | None = None
    event_hint: str | None = None
    final: bool = False

def percept_packet(frame: AcousticFrame, *, consent: bool, source_kind: str,
                   teacher_text: str | None = None, teacher_provenance: str | None = None):
    """A5 acoustic metadata; teacher ASR separate, hints not identities."""
    if not consent:
        raise PermissionError("explicit audio consent required")
    if source_kind not in ("synthetic", "android_microphone", "authorized_audio_feed"):
        raise ValueError("invalid source kind")
    if not isinstance(frame.source_id, str) or not frame.source_id.strip() or len(frame.source_id) > 128:
        raise ValueError("invalid source id")
    if (type(frame.start_ms) is not int or type(frame.end_ms) is not int
            or frame.start_ms < 0 or frame.end_ms <= frame.start_ms):
        raise ValueError("invalid time interval")
    for value in (frame.rms, frame.pitch_hz, frame.speech_probability):
        if value is not None and (not isinstance(value, (float, int)) or not isfinite(value)):
            raise ValueError("invalid feature")
    if frame.rms < 0 or (frame.pitch_hz is not None and frame.pitch_hz <= 0):
        raise ValueError("invalid feature range")
    if frame.speech_probability is not None and not 0 <= frame.speech_probability <= 1:
        raise ValueError("invalid speech probability")
    if teacher_text is not None and (not teacher_provenance or not teacher_provenance.strip()):
        raise ValueError("teacher source required")
    if teacher_text is None and teacher_provenance is not None:
        raise ValueError("orphan teacher provenance")
    if teacher_text is not None and len(teacher_text) > 4096:
        raise ValueError("teacher text exceeds budget")
    return {
        "schema": "v13.a5.timed-acoustic/1", "modality": "audio",
        "source_ref": {"source_id": frame.source_id, "source_kind": source_kind,
                       "start_ms": frame.start_ms, "end_ms": frame.end_ms, "consent": True},
        "provenance": "final" if frame.final else "provisional",
        "acoustic": {"rms": float(frame.rms), "pitch_hz": frame.pitch_hz,
                     "speech_probability": frame.speech_probability,
                     "speaker_hint_unverified": frame.speaker_hint,
                     "event_hint_unverified": frame.event_hint},
        "teacher": None if teacher_text is None else
                   {"text": teacher_text, "provenance": teacher_provenance},
        "a3_projector": "UNAVAILABLE", "native_android_verified": False
    }
