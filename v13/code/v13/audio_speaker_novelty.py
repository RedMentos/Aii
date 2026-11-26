"""Low-gain A4 novelty from uncalibrated, source-bound speaker similarity.

This is a salience hint, not a speaker-change decision, identity label,
probability, interrupt, learning signal, or action authority. It accepts only
FINAL voiced evidence emitted by the bounded speaker-evidence registry.
"""
from __future__ import annotations

import math

BOOT_MAX_SPEAKER_SIMILARITY_NOVELTY = 0.05
_METHOD = "COSINE_LOOKBACK_DIAGNOSTIC_V1"
_UNCALIBRATED = {"CALLER_ASSERTED_UNVERIFIED", "NOT_CONFIGURED"}


def speaker_similarity_novelty(evidence, *, activity_hint: str, finality: str) -> float:
    """Map measured embedding discontinuity to a capped A4-only novelty hint."""
    if activity_hint != "VOICED" or finality != "FINAL":
        return 0.0
    if (type(evidence) is not dict or evidence.get("method") != _METHOD
            or evidence.get("status") != "MEASURED"
            or evidence.get("threshold_status") not in _UNCALIBRATED):
        return 0.0
    frames = evidence.get("frame_evidence")
    if type(frames) is not list:
        return 0.0
    scores = []
    for frame in frames:
        if type(frame) is not dict or frame.get("status") != "MEASURED":
            continue
        value = frame.get("change_score")
        if (type(value) not in (int, float) or not math.isfinite(float(value))
                or not 0.0 <= float(value) <= 1.0):
            continue
        scores.append(float(value))
    if not scores:
        return 0.0
    return round(BOOT_MAX_SPEAKER_SIMILARITY_NOVELTY * max(scores), 6)
