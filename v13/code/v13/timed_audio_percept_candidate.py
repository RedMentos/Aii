"""Consent-bound dependency-free A-plane timed acoustic packet prototype.

No microphone access, ASR inference, identity classification or model training.
"""
from dataclasses import dataclass, asdict
from math import isfinite, sqrt
from typing import Optional

@dataclass(frozen=True)
class AudioPercept:
    schema: str
    source: str
    consent_scope: str
    start_ms: int
    end_ms: int
    sample_rate_hz: int
    sample_count: int
    rms: float
    peak: float
    zero_crossing_rate: float
    speech_text: Optional[str]
    transcript_provenance: str
    status: str
    speaker_id: Optional[str] = None

    def to_packet(self):
        return asdict(self)

def acoustic_packet(samples, sample_rate_hz, start_ms, *, source, consent_scope,
                    speech_text=None, transcript_provenance='none', final=False):
    """Compute bounded low-level features; speech and non-speech are not conflated."""
    if not consent_scope or not source:
        raise PermissionError('explicit source and consent scope required')
    if not isinstance(sample_rate_hz, int) or not 8000 <= sample_rate_hz <= 192000:
        raise ValueError('invalid sample rate')
    if not isinstance(start_ms, int) or start_ms < 0:
        raise ValueError('invalid start time')
    if not 1 <= len(samples) <= sample_rate_hz * 10:
        raise ValueError('audio fixture must be 1 sample to 10 seconds')
    if any(not isfinite(x) or abs(x) > 1 for x in samples):
        raise ValueError('nonfinite or out-of-range PCM')
    if speech_text is not None and transcript_provenance not in ('teacher_asr', 'human'):
        raise ValueError('text requires provenance')
    if speech_text is None and transcript_provenance != 'none':
        raise ValueError('provenance without text')
    n = len(samples)
    return AudioPercept('v13.a5.audio.timed/1', source, consent_scope, start_ms,
        start_ms + (n * 1000 + sample_rate_hz - 1) // sample_rate_hz,
        sample_rate_hz, n, sqrt(sum(x*x for x in samples)/n),
        max(abs(x) for x in samples),
        sum((a < 0) != (b < 0) for a,b in zip(samples, samples[1:])) / max(1,n-1),
        speech_text, transcript_provenance, 'final' if final else 'provisional')
