"""Consent-bound, timestamped RAW EAR packet contract. No microphone capture or ASR."""
from dataclasses import dataclass, asdict
from math import isfinite
from typing import Optional
import json

@dataclass(frozen=True)
class AudioPercept:
    source_id: str
    start_ms: int
    end_ms: int
    sample_rate_hz: int
    channel_count: int
    consent_scope: str
    provenance: str
    phase: str
    rms: float
    peak: float
    zero_crossing_rate: float
    speech_probability: Optional[float] = None
    speaker_local_label: Optional[str] = None
    teacher_transcript: Optional[str] = None
    teacher_revision: Optional[str] = None

    def validate(self):
        if not self.source_id or not self.consent_scope or self.consent_scope == "none":
            raise ValueError("source and explicit consent scope required")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("invalid time window")
        if self.sample_rate_hz not in (8000, 16000, 24000, 44100, 48000) or self.channel_count not in (1, 2):
            raise ValueError("unsupported PCM metadata")
        if self.phase not in ("provisional", "final"):
            raise ValueError("invalid phase")
        if self.provenance not in ("synthetic", "consented_android", "consented_import"):
            raise ValueError("untrusted provenance")
        if any(not isfinite(x) or x < 0 or x > 1 for x in (self.rms, self.peak, self.zero_crossing_rate)):
            raise ValueError("invalid acoustic feature")
        if self.rms > self.peak:
            raise ValueError("RMS cannot exceed peak")
        if self.speech_probability is not None and (not isfinite(self.speech_probability) or not 0 <= self.speech_probability <= 1):
            raise ValueError("invalid speech probability")
        if self.teacher_transcript is not None and not self.teacher_revision:
            raise ValueError("teacher revision required")
        return self

    def to_json(self):
        self.validate()
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

def synthetic_pcm_packet(samples, *, source_id, start_ms, sample_rate_hz=16000,
                         consent_scope="synthetic_test", phase="final"):
    """Pure-Python deterministic fixture; NOT an Android microphone implementation."""
    if not samples or len(samples) > sample_rate_hz * 10:
        raise ValueError("1..10 seconds maximum samples")
    if any(not isinstance(x, (int, float)) or not isfinite(x) or abs(x) > 1 for x in samples):
        raise ValueError("normalized finite PCM samples required")
    n = len(samples)
    rms = (sum(x*x for x in samples)/n)**0.5
    peak = max(abs(x) for x in samples)
    crossings = sum((a < 0) != (b < 0) for a,b in zip(samples,samples[1:])) / max(1,n-1)
    return AudioPercept(source_id, start_ms, start_ms + max(1, round(n*1000/sample_rate_hz)),
                       sample_rate_hz, 1, consent_scope, "synthetic", phase,
                       rms, peak, crossings).validate()
