"""Bounded C3 optional pre-decode work admission.

This protects the actual native first-token window when optional output-head
inference would consume the remainder. It does not shorten the body/peer loop,
alter permission gates, or assert a Redmi latency improvement.
"""
from __future__ import annotations

import math


def admit_output_adapter(remaining_seconds, adapter_budget_seconds, *, native_reserve_seconds=8.0):
    """Allow optional adapter inference only when a native reserve survives.

    The reserve is an initial conservative software policy, NOT a measured
    guarantee of C3 prefill or completion on any device.
    """
    values = (remaining_seconds, adapter_budget_seconds, native_reserve_seconds)
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in values):
        return False
    remaining, adapter, reserve = values
    if remaining <= 0 or adapter < 0 or reserve <= 0:
        return False
    return remaining > adapter + reserve
