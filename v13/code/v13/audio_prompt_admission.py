"""Source-bound, byte-budgeted A5 audio admission for C3 SHADOW prompts.

Offline stdlib only. UTF-8 bytes are a conservative proxy, not tokenizer
counts or native prefill guarantees. No source reader or OS consent is granted.
"""
import json
import math

def admit_audio_shadow(observation, *, max_utf8_bytes=256):
    if type(max_utf8_bytes) is not int or not 0 <= max_utf8_bytes <= 4096:
        raise ValueError("invalid byte budget")
    if not isinstance(observation, dict) or observation.get("kind") != "A5_AUDIO_OBSERVATION":
        raise ValueError("not an A5 audio observation")
    if observation.get("authority") != "SHADOW_ONLY" or any(
        observation.get(k) is not False for k in
        ("action_authority", "learning_authority", "semantic_truth_authority")
    ):
        raise PermissionError("non-shadow observation")
    ref = observation.get("source_ref")
    if not isinstance(ref, dict) or not isinstance(ref.get("source_id"), str) or not ref["source_id"]:
        raise ValueError("missing source lineage")
    sha = ref.get("sha256")
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid source digest")
    if observation.get("finality") not in ("FINAL", "PROVISIONAL"):
        raise ValueError("invalid finality")
    windows = observation.get("windows")
    if not isinstance(windows, list) or not 1 <= len(windows) <= 64:
        raise ValueError("invalid acoustic window count")
    previous_end = None
    any_provisional = False
    for w in windows:
        if not isinstance(w, dict) or any(type(w.get(k)) is not int for k in ("start_ms", "end_ms")):
            raise ValueError("invalid window")
        if not 0 <= w["start_ms"] < w["end_ms"] or w["end_ms"] - w["start_ms"] > 1000:
            raise ValueError("invalid time range")
        if w.get("finality") not in ("FINAL", "PROVISIONAL"):
            raise ValueError("invalid window finality")
        if previous_end is not None and w["start_ms"] < previous_end:
            raise ValueError("overlapping or unordered audio windows")
        previous_end = w["end_ms"]
        any_provisional |= w["finality"] == "PROVISIONAL"
        for k in ("rms", "zcr"):
            v = w.get(k)
            if type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError("invalid acoustic feature")
    if any_provisional and observation["finality"] == "FINAL":
        raise ValueError("provisional audio cannot claim finality")
    base = {"kind": "A5_AUDIO_SHADOW", "source_sha256": sha,
            "finality": observation["finality"], "meaning": "uninterpreted_acoustics"}
    full = dict(base, windows=[
        {"start_ms": w["start_ms"], "end_ms": w["end_ms"],
         "rms": round(w["rms"], 4), "zcr": round(w["zcr"], 4),
         "finality": w["finality"]} for w in windows], omitted_windows=0)
    summary = dict(base, omitted_windows=len(windows),
                   interval_ms=[min(w["start_ms"] for w in windows),
                                max(w["end_ms"] for w in windows)])
    for candidate, level in ((full, "FULL"), (summary, "SUMMARY")):
        value = json.dumps(candidate, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        size = len(value.encode("utf-8"))
        if size <= max_utf8_bytes:
            return {"status": level, "prompt_text": value, "utf8_bytes": size,
                    "omitted_windows": candidate["omitted_windows"], "authority": "SHADOW_ONLY"}
    return {"status": "OMITTED_BUDGET", "prompt_text": "", "utf8_bytes": 0,
            "omitted_windows": len(windows), "authority": "SHADOW_ONLY"}
