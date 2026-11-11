"""Bounded, source-bound acoustic views for B1/B2 and JEF (SHADOW only).

These are numeric acoustic observations, not speech transcripts, speaker IDs,
intent labels, permission receipts, or model-produced semantic claims.
"""
from __future__ import annotations
from math import isfinite

def acoustic_views(percept: dict, *, max_detail: int = 64, gist_bins: int = 8) -> dict:
    if type(max_detail) is not int or not 1 <= max_detail <= 256:
        raise ValueError("invalid max_detail")
    if type(gist_bins) is not int or not 1 <= gist_bins <= 32:
        raise ValueError("invalid gist_bins")
    if not isinstance(percept, dict) or percept.get("modality") != "audio_acoustic":
        raise ValueError("audio A5 percept required")
    if percept.get("android_capture_verified") is not False or percept.get("action_authority") != 0:
        raise ValueError("unexpected native authority")
    raw = percept.get("raw_ear")
    if not isinstance(raw, dict) or raw.get("provenance") != "final" or raw.get("asr") is not None:
        raise ValueError("only final non-ASR acoustic evidence allowed")
    ref = percept.get("source_ref")
    frames = percept.get("segments")
    if not isinstance(ref, dict) or not isinstance(frames, list) or not 1 <= len(frames) <= 4096:
        raise ValueError("bounded source and frames required")
    # A5 segments are a derived projection of RAW EAR frames. Reject divergence
    # before any B/C consumer sees the view (no semantic or training authority).
    raw_frames = raw.get("frames")
    if not isinstance(raw_frames, list) or len(raw_frames) != len(frames):
        raise ValueError("RAW EAR / A5 frame count mismatch")
    for segment, original in zip(frames, raw_frames):
        if not isinstance(segment, dict) or not isinstance(original, dict):
            raise ValueError("invalid acoustic frame")
        for field in ("start_ms", "end_ms", "rms", "pitch_hz",
                      "voiced_probability", "non_speech_probability"):
            if type(segment.get(field)) is not type(original.get(field)) or segment.get(field) != original.get(field):
                raise ValueError("RAW EAR / A5 acoustic value mismatch")
    if raw.get("android_capture_verified") is not False:
        raise ValueError("RAW EAR native authority is unverified")
    duration = raw.get("duration_ms")
    if type(duration) is not int or not 1 <= duration <= 120000:
        raise ValueError("invalid duration")
    previous = 0
    for f in frames:
        if not isinstance(f, dict) or f.get("source_ref") != ref:
            raise ValueError("source mismatch")
        a,b,r = f.get("start_ms"), f.get("end_ms"), f.get("rms")
        if type(a) is not int or type(b) is not int or a < previous or b <= a or b > duration:
            raise ValueError("invalid timeline")
        if type(r) not in (int,float) or not isfinite(r) or not 0 <= r <= 1:
            raise ValueError("invalid RMS")
        # Numeric features must remain valid after serialization or mutation.
        # Unknown pitch is None; unknown probabilities remain explicit, never inferred.
        pitch = f.get("pitch_hz")
        if pitch is not None and (type(pitch) not in (int, float) or
                                  not isfinite(pitch) or not 20 <= pitch <= 2000):
            raise ValueError("invalid pitch")
        for field in ("voiced_probability", "non_speech_probability"):
            value = f.get(field)
            if type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1:
                raise ValueError("invalid acoustic probability")
        previous = b
    # B1 retains exact sampled frame measurements, without inventing missing frames.
    step = max(1, (len(frames) + max_detail - 1) // max_detail)
    detail = [{"start_ms": f["start_ms"], "end_ms": f["end_ms"],
               "rms": f["rms"], "pitch_hz": f["pitch_hz"],
               "voiced_probability": f["voiced_probability"],
               "non_speech_probability": f["non_speech_probability"]}
              for f in frames[::step]][:max_detail]
    # B2 is a time-weighted RMS energy envelope, not semantic compression.
    buckets = []
    for i in range(gist_bins):
        lo,hi = duration*i//gist_bins, duration*(i+1)//gist_bins
        energy = coverage = 0.0
        for f in frames:
            overlap = max(0,min(hi,f["end_ms"])-max(lo,f["start_ms"]))
            energy += overlap * f["rms"]**2
            coverage += overlap
        buckets.append({"start_ms":lo,"end_ms":hi,
                        "rms":(energy/coverage)**0.5 if coverage else None,
                        "covered_ms":int(coverage)})
    return {"source_ref":ref,"modality":"audio_acoustic","authority":"SHADOW",
            "b1_detail":detail,"b2_gist":buckets,
            "jef_control":{"duration_ms":duration,"frame_count":len(frames),
                           "provisional":False,"asr_available":False,
                           "semantic_truth_authority":False,
                           "android_capture_verified":False,
                           "action_authority":0,"training_authority":0}}
