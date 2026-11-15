"""V13 A-plane timed RAW EAR envelope; no capture, ASR, or model inference."""
from dataclasses import dataclass
from math import isfinite
from typing import Optional

@dataclass(frozen=True)
class TimedAudioPercept:
    source_id: str
    consent_scope: str
    start_ms: int
    end_ms: int
    rms: float
    voiced_fraction: float
    spectral_centroid_hz: float
    provenance: str = "synthetic"
    final: bool = False
    transcript: Optional[str] = None

    def __post_init__(self):
        if not self.source_id or not self.consent_scope:
            raise ValueError("source and consent required")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("invalid monotonic interval")
        if self.provenance not in ("synthetic", "consented_microphone", "consented_feed"):
            raise ValueError("unrecognized provenance")
        if not all(isfinite(x) for x in (self.rms, self.voiced_fraction, self.spectral_centroid_hz)):
            raise ValueError("nonfinite feature")
        if not (0 <= self.rms <= 1 and 0 <= self.voiced_fraction <= 1 and self.spectral_centroid_hz >= 0):
            raise ValueError("feature out of range")
        if self.transcript is not None and not self.final:
            raise ValueError("teacher transcript requires final provenance")

    def to_a5(self):
        """Source-linked A5 envelope; not a learned latent or ASR."""
        return {"modality": "audio_acoustic", "source_id": self.source_id,
                "consent_scope": self.consent_scope, "start_ms": self.start_ms,
                "end_ms": self.end_ms,
                "features": {"rms": self.rms, "voiced_fraction": self.voiced_fraction,
                             "spectral_centroid_hz": self.spectral_centroid_hz},
                "provenance": self.provenance, "final": self.final,
                "teacher_transcript": self.transcript, "gate": "SHADOW"}

def ordered_percepts(events):
    """Reject overlapping/out-of-order source segments, never silently reorder."""
    last = {}
    for event in events:
        if event.source_id in last and event.start_ms < last[event.source_id]:
            raise ValueError("overlapping/out-of-order audio")
        last[event.source_id] = event.end_ms
        yield event.to_a5()
