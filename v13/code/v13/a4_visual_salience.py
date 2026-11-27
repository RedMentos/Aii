"""A5 -> A4 visual-structure salience adapter.

This keeps the pinned core attention controller byte-stable while adding a
small, source-bound RAW-EYE structural cue to its returned A4 salience receipt.
The cue is handcrafted BOOT metadata, not semantic recognition, a probability,
a learned representation, truth, action authority or learning authority.
"""
from __future__ import annotations

import math


RAW_EYE_STRUCTURE_GAIN = 0.20
_COMPONENTS = (
    "global_contrast",
    "global_edge_energy",
    "cell_edge_energy",
    "spatial_color",
    "luminance_range",
)


def _unit(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be finite and within [0, 1]")
    return value


def apply_raw_eye_structure(a4_result, segment, score, components):
    """Attach a bounded visual structure contribution to the matching A4 row."""
    if not isinstance(a4_result, dict) or not isinstance(segment, dict):
        raise ValueError("A4 result and visual segment must be mappings")
    source_ref = segment.get("source_ref")
    if (
        segment.get("modality") != "visual"
        or not isinstance(source_ref, dict)
        or source_ref.get("modality") != "visual"
        or segment.get("capture_method") != "MEDIA_PROJECTION"
        or segment.get("producer_component") != "A5_VISUAL"
    ):
        raise ValueError("RAW-EYE salience lacks A5 MediaProjection provenance")
    score = _unit(score, "RAW-EYE structure score")
    if not isinstance(components, dict) or set(components) != set(_COMPONENTS):
        raise ValueError("RAW-EYE structure components are incomplete")
    clean_components = {
        key: round(_unit(components[key], f"RAW-EYE {key}"), 6)
        for key in _COMPONENTS
    }
    rows = a4_result.get("segments")
    if not isinstance(rows, list):
        raise ValueError("A4 result has no segment salience rows")
    matches = [row for row in rows if isinstance(row, dict) and row.get("source_ref") == source_ref]
    if len(matches) != 1:
        raise ValueError("RAW-EYE source does not map to exactly one A4 row")
    row = matches[0]
    base_score = _unit(row.get("score"), "A4 base salience")
    contribution = RAW_EYE_STRUCTURE_GAIN * score
    row["base_score"] = round(base_score, 6)
    row["raw_eye_structure"] = round(score, 6)
    row["raw_eye_components"] = clean_components
    row["raw_eye_contribution"] = round(contribution, 6)
    row["score"] = round(min(1.0, base_score + contribution), 6)
    row["reason_detail"] = "raw_eye_structure" if score > 0.0 else row.get("reason")
    a4_result["raw_eye_signal"] = {
        "source_ref": source_ref,
        "score": round(score, 6),
        "gain": RAW_EYE_STRUCTURE_GAIN,
        "contribution": round(contribution, 6),
        "authority": "ATTENTION_ONLY",
        "learned": False,
    }
    return a4_result
