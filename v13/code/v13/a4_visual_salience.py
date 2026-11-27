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


def apply_raw_eye_structure(a4_result, segment, score, components, *, segment_index=0):
    """Attach RAW-EYE structure to one source/index row and refresh A4 ranking.

    A5 may emit several hypotheses for one visual source. Source identity alone
    therefore does not identify a unique A4 row; the base visual segment is
    explicitly addressed by its stable segment index.
    """
    if not isinstance(a4_result, dict) or not isinstance(segment, dict):
        raise ValueError("A4 result and visual segment must be mappings")
    if type(segment_index) is not int or segment_index < 0:
        raise ValueError("RAW-EYE target segment index must be a non-negative integer")
    source_ref = segment.get("source_ref")
    if (
        segment.get("modality") != "visual"
        or not isinstance(source_ref, dict)
        # The provider-backed UI path keeps image provenance on SourceRef while
        # its A4 segment is explicitly marked visual and MediaProjection-bound.
        or source_ref.get("modality") not in {"visual", "image"}
        or segment.get("capture_method") != "MEDIA_PROJECTION"
        or segment.get("producer_component") not in {"A5_VISUAL", "A5_RAW_EYE_UI"}
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
    matches = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("index") == segment_index
        and row.get("source_ref") == source_ref
    ]
    if len(matches) != 1:
        raise ValueError("RAW-EYE source/index does not map to exactly one A4 row")
    row = matches[0]
    base_score = _unit(row.get("score"), "A4 base salience")
    contribution = RAW_EYE_STRUCTURE_GAIN * score
    row["base_score"] = round(base_score, 6)
    row["raw_eye_structure"] = round(score, 6)
    row["raw_eye_components"] = clean_components
    row["raw_eye_contribution"] = round(contribution, 6)
    row["score"] = round(min(1.0, base_score + contribution), 6)
    row["reason_detail"] = "raw_eye_structure" if score > 0.0 else row.get("reason")

    # The structural contribution changes A4 salience, so refresh the derived
    # normalized weights/suppression and re-look ranking instead of leaving
    # them tied to the pre-RAW-EYE scores.
    from .attention import A4 as ATTENTION_A4

    temperature = float(ATTENTION_A4["attention_temperature"])
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("A4 attention temperature must be finite and positive")
    if rows:
        scores = [_unit(item.get("score"), "A4 segment salience") for item in rows]
        maximum = max(scores)
        weights = [math.exp((value - maximum) / temperature) for value in scores]
        normalizer = sum(weights)
        if not math.isfinite(normalizer) or normalizer <= 0.0:
            raise ValueError("A4 attention normalization is invalid")
        for item, value, weight in zip(rows, scores, weights):
            if not isinstance(item, dict) or type(item.get("index")) is not int:
                raise ValueError("A4 segment row identity is invalid")
            item["weight"] = round(weight / normalizer, 6)
            item["suppression"] = round(
                ATTENTION_A4["suppression_max"] * (1.0 - value / maximum)
                if maximum > 0.0 else 0.0,
                6,
            )
        relook = sorted(
            (
                item for item in rows
                if item["score"] >= ATTENTION_A4["reentry_threshold"]
            ),
            key=lambda item: (-item["score"], item["index"]),
        )[:ATTENTION_A4["max_highres_regions"]]
        a4_result["highres"] = [item["index"] for item in relook]

    a4_result["raw_eye_signal"] = {
        "source_ref": source_ref,
        "score": round(score, 6),
        "gain": RAW_EYE_STRUCTURE_GAIN,
        "contribution": round(contribution, 6),
        "authority": "ATTENTION_ONLY",
        "learned": False,
    }
    return a4_result
