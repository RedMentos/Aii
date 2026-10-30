"""Run31 isolated finite native token-confidence candidate, SHADOW only.

This is not wired into the frozen AG12 BodySolver or production runtime.
"""
from __future__ import annotations

import math

CONF_KEYS = ("field_min_prob", "field_mean_prob", "mean_prob")
REVISION = "run31-ag12-finite-token-confidence-shadow-v1"


def safe_confidence(metrics):
    """Return (probability, source); never turn malformed values into certainty.

    Only a truly absent token-confidence metric retains the historical .5
    fallback. A present invalid highest-priority field is a hard zero, not
    permission to select a lower-priority value. No model/Store side effects.
    """
    if metrics is None or metrics == {}:
        return 0.5, "none"
    if type(metrics) is not dict:
        return 0.0, "invalid:metrics"
    if "token_confidence" not in metrics:
        return 0.5, "none"
    tc = metrics["token_confidence"]
    if type(tc) is not dict:
        return 0.0, "invalid:token_confidence"
    for key in CONF_KEYS:
        if key not in tc:
            continue
        v = tc[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return 0.0, "invalid:" + key
        try:
            value = float(v)
        except (OverflowError, TypeError, ValueError):
            return 0.0, "invalid:" + key
        if not math.isfinite(value):
            return 0.0, "invalid:" + key
        return max(0.0, min(1.0, value)), key
    return 0.5, "none"
