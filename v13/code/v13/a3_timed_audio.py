"""Source-bound, timestamped RAW EAR -> A3 SHADOW observation.

Only synthetic, previously authorized Store sources. No microphone, ASR, speaker
identity, Android permission, action authority or canonical A5 promotion.
"""
import hashlib
import json
import math
from .a3_runtime_adapter import A3InferenceRuntime, FeatureObservation

def observe_timed_audio(runtime, projector, source_ref):
    if not callable(getattr(getattr(runtime, "store", None), "read_source", None)):
        raise TypeError("Runtime.store.read_source required")
    if not isinstance(source_ref, dict) or set(source_ref) != {
        "source_id", "sha256", "char_start", "char_end", "modality"
    } or source_ref["modality"] != "text":
        raise ValueError("complete Store source reference required")
    raw = runtime.store.read_source(source_ref)
    if source_ref["char_start"] != 0 or source_ref["char_end"] != len(raw):
        raise ValueError("full-span source required")
    data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    if not isinstance(data, dict) or set(data) != {
        "features", "final", "start_ms", "end_ms", "sample_rate_hz", "acoustic"
    }:
        raise ValueError("invalid timed audio schema")
    if data["final"] is not True:
        raise PermissionError("provisional audio is not final A3 evidence")
    start, end, rate = (data[k] for k in ("start_ms", "end_ms", "sample_rate_hz"))
    if any(type(v) is not int for v in (start, end, rate)) or not (
        0 <= start < end <= 86400000 and end-start <= 60000 and 8000 <= rate <= 192000
    ):
        raise ValueError("invalid audio timing or sample rate")
    acoustic = data["acoustic"]
    if not isinstance(acoustic, dict) or set(acoustic) != {
        "rms", "pitch_hz", "speech_probability"
    }:
        raise ValueError("invalid acoustic feature schema")
    rms, pitch, speech = (acoustic[k] for k in ("rms", "pitch_hz", "speech_probability"))
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (rms, pitch, speech)):
        raise ValueError("nonfinite acoustic measurement")
    if not (0 <= rms <= 1 and 0 <= pitch <= 4000 and 0 <= speech <= 1):
        raise ValueError("acoustic measurement out of bounds")
    if not isinstance(data["features"], list):
        raise ValueError("numeric features required")
    # Source hash and revocation are checked by Store.read_source; this digest
    # additionally binds the derived observation to its exact feature values.
    obs = FeatureObservation(source_ref["source_id"], "synthetic_audio",
                             tuple(data["features"]), True, "")
    obs = FeatureObservation(obs.source_id, obs.modality, obs.feature_vector,
                             True, hashlib.sha256(obs.canonical_bytes()).hexdigest())
    def verify(current):
        if current.source_id != source_ref["source_id"]:
            return False
        try:
            return runtime.store.read_source(source_ref) == raw
        except (ValueError, KeyError, OSError, PermissionError):
            return False
    result = A3InferenceRuntime(projector, verify).observe(obs)
    result["a5"].update({
        "status": "SHADOW_TIMED_AUDIO", "store_source_sha256": source_ref["sha256"],
        "start_ms": start, "end_ms": end, "sample_rate_hz": rate,
        "acoustic": dict(acoustic), "transcript": None
    })
    return result
