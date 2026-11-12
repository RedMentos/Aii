"""Strict observation-only A5 candidate for source-bound timed RAW EAR.

Not the canonical A5 PerceptPacket. Explicitly preserves non-ASR acoustics,
source lineage and missing measurements. No Android permissions or action rights.
"""
import math

def from_timed_a3(result):
    """Convert existing observe_timed_audio output to an immutable-by-convention
    plain-data handoff; reject missing provenance and fabricated measurements."""
    if not isinstance(result, dict) or not isinstance(result.get("a5"), dict):
        raise ValueError("A3/A5 shadow observation required")
    a = result["a5"]
    required = ("source_id", "source_sha256", "store_source_sha256",
                "a3_embedding", "a4_salience", "acoustic", "start_ms",
                "end_ms", "sample_rate_hz", "status", "authority")
    if any(k not in a for k in required):
        raise ValueError("incomplete A3 audio provenance")
    if a["status"] != "SHADOW_TIMED_AUDIO" or a["authority"] != "observation_only":
        raise PermissionError("only shadow observation may be adapted")
    if a.get("android_action_allowed") is not False or a.get("provisional") is not False:
        raise PermissionError("no action or provisional promotion")
    for k in ("source_sha256", "store_source_sha256"):
        if not isinstance(a[k], str) or len(a[k]) != 64 or any(c not in "0123456789abcdef" for c in a[k]):
            raise ValueError("invalid source digest")
    if not isinstance(a["source_id"], str) or not a["source_id"]:
        raise ValueError("missing source ID")
    emb = a["a3_embedding"]
    if not isinstance(emb, (list, tuple)) or not emb or len(emb) > 4096 or any(
        type(x) not in (int, float) or not math.isfinite(x) for x in emb
    ):
        raise ValueError("invalid embedding")
    sal = a["a4_salience"]
    if not isinstance(sal, dict) or sal.get("authority") != "observation_only" or sal.get("learned") is not False:
        raise ValueError("unverified salience")
    score = sal.get("score")
    if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("invalid salience")
    start, end, rate = (a[k] for k in ("start_ms", "end_ms", "sample_rate_hz"))
    if any(type(x) is not int for x in (start, end, rate)) or not (0 <= start < end <= 86400000 and 8000 <= rate <= 192000):
        raise ValueError("invalid timing")
    acoustic = a["acoustic"]
    if not isinstance(acoustic, dict) or "rms" not in acoustic:
        raise ValueError("missing acoustic evidence")
    if a.get("transcript") is not None:
        raise ValueError("this RAW EAR route cannot assert ASR")
    return {
        "schema": "v13.a5.audio.observation_candidate.v1",
        "canonical_a5": False,
        "status": "SHADOW",
        "modality": "synthetic_audio",
        "source": {"id": a["source_id"], "feature_sha256": a["source_sha256"],
                   "store_sha256": a["store_source_sha256"], "final": True},
        "time": {"start_ms": start, "end_ms": end, "sample_rate_hz": rate},
        "a3": {"embedding": list(emb), "training_steps": a.get("a3_training_steps")},
        "a4": {"score": float(score), "method": sal.get("method"),
               "unmeasured": list(sal.get("unmeasured", ()))},
        "raw_ear": {"rms": acoustic["rms"], "pitch_hz": acoustic.get("pitch_hz"),
                    "speech_probability": acoustic.get("speech_probability"),
                    "unmeasured": list(sal.get("unmeasured", ()))},
        "transcript": None,
        "authority": "observation_only",
        "android_action_allowed": False,
        "runtime_consumer": "NOT_CONNECTED",
    }
