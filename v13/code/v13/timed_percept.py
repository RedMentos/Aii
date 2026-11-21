"""Consent-bound timed A-plane percept envelope. No microphone capture or ASR authority."""
from dataclasses import dataclass, asdict
from math import isfinite
from typing import Optional

@dataclass(frozen=True)
class TimedPercept:
    modality: str
    source: str
    start_ms: int
    end_ms: int
    consent_id: str
    stage: str = "provisional"
    provenance: str = "synthetic"
    rms: Optional[float] = None
    pitch_hz: Optional[float] = None
    speech_probability: Optional[float] = None
    non_speech: Optional[str] = None
    transcript: Optional[str] = None

    def __post_init__(self):
        if self.modality not in ("audio", "android_ui", "visual"):
            raise ValueError("unknown modality")
        if not self.source or not self.consent_id:
            raise ValueError("source and explicit consent required")
        if not (isinstance(self.start_ms, int) and isinstance(self.end_ms, int) and 0 <= self.start_ms <= self.end_ms):
            raise ValueError("invalid monotonic time window")
        if self.stage not in ("provisional", "final") or self.provenance not in ("synthetic", "permissioned_android", "teacher"):
            raise ValueError("invalid stage or provenance")
        if self.modality != "audio" and any(x is not None for x in (self.rms, self.pitch_hz, self.speech_probability, self.non_speech, self.transcript)):
            raise ValueError("audio attributes on non-audio event")
        for x in (self.rms, self.pitch_hz, self.speech_probability):
            if x is not None and (not isfinite(x) or x < 0):
                raise ValueError("invalid acoustic feature")
        if self.speech_probability is not None and self.speech_probability > 1:
            raise ValueError("probability out of range")
        if self.transcript is not None and self.provenance != "teacher":
            raise ValueError("transcript requires teacher provenance")

    def packet(self):
        return {"schema": "v13.a5.timed-percept/1", "authority": "observation_only", **asdict(self)}

def provisional_to_final(old: TimedPercept, new: TimedPercept):
    """Reject cross-source and cross-consent event substitution."""
    if old.stage != "provisional" or new.stage != "final":
        raise ValueError("invalid transition")
    if (old.modality, old.source, old.consent_id, old.start_ms) != (new.modality, new.source, new.consent_id, new.start_ms):
        raise ValueError("lineage mismatch")
    if new.end_ms < old.end_ms:
        raise ValueError("time regression")
    return new.packet()
