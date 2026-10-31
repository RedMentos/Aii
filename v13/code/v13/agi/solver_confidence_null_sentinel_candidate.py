"""Run37 isolated AG12 confidence semantics: native None is an absent span.

No production runtime imports this candidate. Frozen original and Run31
software/native evidence are unchanged.
"""
from __future__ import annotations

import math

from .solver_confidence_finite_candidate import CONF_KEYS

REVISION = "run37-ag12-native-null-sentinel-shadow-v1"


def safe_confidence_null_aware(metrics):
    """Finite confidence with native missing-span None distinguished from invalid.

    A present None field is a native no-span sentinel, so seek the next
    available confidence key. A present malformed non-None priority field is
    fail-closed zero; never let a lower-priority field mask NaN/Inf.
    """
    if metrics is None:
        return 0.5, "none"
    if type(metrics) is not dict:
        return 0.0, "invalid:metrics"
    if "token_confidence" not in metrics:
        return 0.5, "none"
    tc = metrics["token_confidence"]
    if tc is None:
        return 0.5, "none"
    if type(tc) is not dict:
        return 0.0, "invalid:token_confidence"
    for key in CONF_KEYS:
        if key not in tc or tc[key] is None:
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
