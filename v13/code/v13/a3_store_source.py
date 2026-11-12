"""Store-backed A3 perception entrypoint, without editing frozen Runtime.

This is an explicit opt-in SHADOW observation route. Source bytes come from the
actual V13 Store.read_source API, not caller-supplied feature vectors. It does
not approve learning, grant Android actions or promote canonical A5 packets.
"""
import hashlib
import json

from .a3_runtime_adapter import A3InferenceRuntime, FeatureObservation


def observe_stored_features(runtime, projector, source_ref, *, modality):
    """Read an immutable JSON feature fixture from V13's revocable source store.

    Runtime owns the Store; its read_source verifies blob hash and revocation.
    The caller cannot inject unverified feature values into this entrypoint.
    """
    if not hasattr(runtime, "store") or not callable(getattr(runtime.store, "read_source", None)):
        raise TypeError("real runtime Store.read_source required")
    if not isinstance(source_ref, dict) or set(source_ref) != {
            "source_id", "sha256", "char_start", "char_end", "modality"}:
        raise ValueError("complete source ref required")
    if source_ref["modality"] != "text" or modality not in (
            "synthetic_audio", "synthetic_visual", "synthetic_ui"):
        raise ValueError("unsupported source or feature modality")
    # Store.read_source independently verifies blob hash, deletion and range.
    # Full-span requirement prevents silent truncation / source aliasing.
    source_text = runtime.store.read_source(source_ref)
    if source_ref["char_start"] != 0 or source_ref["char_end"] != len(source_text):
        raise ValueError("feature fixture must cover entire source")
    data = json.loads(source_text)
    if not isinstance(data, dict) or set(data) != {"features", "final"}:
        raise ValueError("invalid fixture schema")
    if data["final"] is not True:
        raise PermissionError("provisional features cannot enter A3")
    if not isinstance(data["features"], list):
        raise ValueError("feature vector required")
    source_id = source_ref["source_id"]
    observation = FeatureObservation(
        source_id, modality, tuple(data["features"]), True, "")
    observation = FeatureObservation(
        source_id, modality, observation.feature_vector, True,
        hashlib.sha256(observation.canonical_bytes()).hexdigest())

    def verify(current):
        if current.source_id != source_id:
            return False
        # Recheck revocation at use, not only when fixture was read.
        try:
            return runtime.store.read_source(source_ref) == source_text
        except (ValueError, OSError, KeyError):
            return False

    result = A3InferenceRuntime(projector, verify).observe(observation)
    result["a5"]["store_source_sha256"] = source_ref["sha256"]
    result["a5"]["status"] = "SHADOW_STORE_BACKED"
    return result
