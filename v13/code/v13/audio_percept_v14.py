"""V14 A-plane timed RAW EAR metadata adapter; no microphone capture or ASR claim.

Only consented upstream audio feature frames enter here. Raw samples stay outside
the shared symbolic bus. Speaker identifiers are local opaque labels, not identity.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class AudioFrame:
    source_id: str
    start_ms: int
    end_ms: int
    rms: float
    pitch_hz: float | None = None
    voiced_probability: float | None = None
    speaker_label: str | None = None
    non_speech: str | None = None
    final: bool = False
    consent: bool = False

    def validate(self):
        if not self.consent:
            raise PermissionError("audio source consent required")
        if not self.source_id or len(self.source_id) > 96:
            raise ValueError("invalid source id")
        if type(self.start_ms) is not int or type(self.end_ms) is not int or not 0 <= self.start_ms < self.end_ms:
            raise ValueError("invalid audio interval")
        if self.end_ms - self.start_ms > 30_000:
            raise ValueError("audio frame exceeds bounded interval")
        for name, value, lo, hi in (
            ("rms", self.rms, 0, 1),
            ("pitch", self.pitch_hz, 0, 2000),
            ("voiced", self.voiced_probability, 0, 1),
        ):
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi):
                raise ValueError("invalid " + name)
        for value in (self.speaker_label, self.non_speech):
            if value is not None and (not isinstance(value, str) or len(value) > 48 or any(ord(c) < 32 for c in value)):
                raise ValueError("invalid feature label")

def publish_audio_frame(space, event, frame: AudioFrame):
    """A-plane -> Enlightened Space, control-only and no invented source refs.

    This publishes acoustic metadata, not verified transcript, speaker identity,
    learned embedding, or Android device success. Consumer can route via B/C.
    """
    frame.validate()
    summary = (f"audio interval {frame.start_ms}-{frame.end_ms}ms "
               f"rms={frame.rms:.3f} "
               f"pitch={frame.pitch_hz if frame.pitch_hz is not None else 'unknown'} "
               f"voiced={frame.voiced_probability if frame.voiced_probability is not None else 'unknown'} "
               f"speaker={frame.speaker_label or 'unknown'} "
               f"non_speech={frame.non_speech or 'none'} "
               f"provenance={'final' if frame.final else 'provisional'}")
    return space.publish(event, "A_PERCEPTION", "CONTROL",
                         summary=summary[:280], authority="CONTROL_ONLY")
