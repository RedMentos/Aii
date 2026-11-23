"""Bounded, consent-gated RAW EAR acoustic windows. No microphone or ASR access."""
import math

def acoustic_window(samples, sample_rate, source_ref, start_ms, *, consent=False, provisional=True):
    if consent is not True:
        raise PermissionError("explicit audio observation consent required")
    if not isinstance(source_ref, dict) or not source_ref.get("source_id"):
        raise ValueError("registered source_id required")
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 48000:
        raise ValueError("sample_rate 8000..48000 required")
    if not isinstance(start_ms, (int, float)) or not math.isfinite(start_ms) or start_ms < 0:
        raise ValueError("invalid start_ms")
    if not isinstance(samples, (list, tuple)) or not 0 < len(samples) <= 2 * sample_rate:
        raise ValueError("bounded nonempty PCM window required")
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) or abs(x) > 1 for x in samples):
        raise ValueError("finite normalized PCM required")
    n = len(samples)
    rms = math.sqrt(sum(float(x) ** 2 for x in samples) / n)
    crossings = sum((samples[i] < 0) != (samples[i-1] < 0) for i in range(1, n))
    return {
        "schema": "v13.a5.audio-acoustic/1", "modality": "audio_raw_ear",
        "source_ref": dict(source_ref), "start_ms": float(start_ms),
        "end_ms": float(start_ms) + 1000 * n / sample_rate,
        "sample_rate_hz": sample_rate, "samples": n,
        "features": {"rms": rms, "peak": float(max(abs(x) for x in samples)),
                     "zero_crossing_rate": crossings / max(1, n-1)},
        "provenance": {"origin": "PCM_ACOUSTIC_NOT_ASR",
                       "status": "PROVISIONAL" if provisional else "FINAL",
                       "speaker_identity": "UNKNOWN", "transcript": None},
        "learning_authority": "NONE" if provisional else "SOURCE_BOUND_REVIEW_REQUIRED",
    }

def canonical_packet(samples, sample_rate, source_ref, start_ms, *,
                     consent_receipt, event_id, generation_id, provisional=True):
    """Runtime-facing bridge to existing A5 contract; no ASR or OS permission grant."""
    from .audio_percept_contract import audio_percept_packet
    features = acoustic_window(samples, sample_rate, source_ref, start_ms,
                               consent=bool(consent_receipt), provisional=provisional)
    begin, end = round(features["start_ms"]), round(features["end_ms"])
    if end <= begin:
        raise ValueError("audio window too short for millisecond A5 schema")
    return audio_percept_packet(
        event_id=event_id, generation_id=generation_id,
        source_id=source_ref["source_id"], source_sha256=source_ref["sha256"],
        start_ms=begin, end_ms=end, rms=features["features"]["rms"],
        zcr=features["features"]["zero_crossing_rate"],
        finality="PROVISIONAL" if provisional else "FINAL",
        consent_receipt=consent_receipt)
