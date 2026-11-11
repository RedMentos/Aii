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
        previous = b
    # B1 retains exact sampled frame measurements, without inventing missing frames.
    step = max(1, (len(frames) + max_detail - 1) // max_detail)
    detail = [{"start_ms": f["start_ms"], "end_ms": f["end_ms"], "rms": f["rms"]}
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
