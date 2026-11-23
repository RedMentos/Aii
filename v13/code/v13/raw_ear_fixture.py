"""Deterministic tiny PCM-to-A5 adapter; does not record or transcribe audio."""
from math import isfinite, sqrt
from .timed_percept import TimedPercept

def synthetic_pcm_to_percept(samples, sample_rate, start_ms, source, consent_id, stage="provisional"):
    """Caller supplies permissioned data; synthetic test only, no Android capture."""
    if not consent_id:
        raise PermissionError("consent required")
    if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 192000:
        raise ValueError("invalid sample rate")
    if not samples or len(samples) > sample_rate * 10:
        raise ValueError("window must be nonempty and at most 10 seconds")
    if any(not isinstance(x, (int, float)) or not isfinite(x) or abs(x) > 1 for x in samples):
        raise ValueError("normalized finite PCM required")
    rms = sqrt(sum(x*x for x in samples)/len(samples))
    duration_ms = max(1, (len(samples)*1000 + sample_rate-1)//sample_rate)
    return TimedPercept(modality="audio", source=source, start_ms=start_ms,
                        end_ms=start_ms+duration_ms, consent_id=consent_id,
                        stage=stage, provenance="synthetic", rms=rms)
