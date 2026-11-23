"""Measured-failure recovery for the *whole-turn* native compute envelope.

A short turn with repeated real C3 zero-token prefill failures reserves a
measured minimum for the outward C3 path. The remaining pre-answer window is
shared fairly by sequential B1/B2 passes; one body cannot consume the peer's
entire opportunity. A body is deferred to the existing post-commit path only
when its own remaining slice is below the minimum. Long/deep turns keep the
ordinary 45% observer window. Age and learning rights are unchanged.
"""

from __future__ import annotations

import json
import math


SCHEMA = "v13.native-turn-budget/1"
MAX_RECENT = 6
RECOVERY_MAX_DEADLINE_S = 50
NATIVE_FIRST_RESERVE_FRACTION = .87
DEFAULT_PREANSWER_FRACTION = .45
MIN_ROLE_SLICE_S = 1.0


def zero_token_prefill_failure(row):
    """Source-blind, strict evidence from a completed real assistant turn."""
    if not isinstance(row, dict) or row.get("status") != "DEADLINE":
        return False
    data = row.get("metadata")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (ValueError, TypeError):
            return False
    if not isinstance(data, dict):
        return False
    native = data.get("runner")
    return (isinstance(native, dict)
            and native.get("role") == "C3_LANGUAGE"
            and type(native.get("generated_tokens")) is int
            and native.get("generated_tokens") == 0
            and native.get("last_phase") in {"load", "template", "prefill"})


def recent_proof(store):
    """Only bounded device-local metadata. Never selects raw user/model text."""
    try:
        rows = store.rows(
            "SELECT status,metadata FROM messages "
            "WHERE role='assistant' AND status IN ('FINAL','DEADLINE','ERROR','CANCELLED') "
            "ORDER BY id DESC LIMIT ?",
            (MAX_RECENT,))
        return [{"status":r["status"], "metadata":r["metadata"]} for r in rows]
    except (OSError, ValueError, RuntimeError):
        return []


def plan(start, deadline, now, *, recent=(), background_enabled=True, direct=False, observer_deadline=None):
    for number in (start,deadline,now):
        if type(number) not in (int, float) or not math.isfinite(number):
            raise ValueError("invalid monotonic budget")
    if observer_deadline is not None and (
            type(observer_deadline) not in (int, float) or not math.isfinite(observer_deadline)):
        raise ValueError("invalid observer deadline")
    if deadline < start or now < start-1:
        raise ValueError("time plan clocks invalid")
    total = deadline-start
    ordinary_end = start+DEFAULT_PREANSWER_FRACTION*total
    bounded = list(recent)[:MAX_RECENT]
    failures = sum(zero_token_prefill_failure(row) for row in bounded)
    recent_good = 0
    for row in bounded:
        if not isinstance(row, dict):
            break
        status=row.get("status")
        data=row.get("metadata")
        if isinstance(data, str):
            try:
                data=json.loads(data)
            except (ValueError, TypeError):
                data=None
        native=data.get("runner") if isinstance(data, dict) else None
        if (status == "FINAL" and isinstance(native, dict)
                and native.get("role") == "C3_LANGUAGE"
                and type(native.get("generated_tokens")) is int
                and native["generated_tokens"] > 0):
            recent_good += 1
        else:
            break
        if recent_good == 2:
            break
    recover = (
        not direct and background_enabled is True
        and total <= RECOVERY_MAX_DEADLINE_S and total >= 5
        and failures >= 2 and recent_good < 2
    )
    if recover:
        reserve = min(total*NATIVE_FIRST_RESERVE_FRACTION,
                      max(26.0,total*.80))
        allotted = min(ordinary_end,deadline-reserve)
        reason="RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS"
    else:
        reserve=deadline-ordinary_end
        allotted=ordinary_end
        reason="NORMAL_COGNITIVE_PREANSWER"
    if observer_deadline is not None:
        allotted=min(allotted,observer_deadline)
    # Expired observer windows are honest (zero). The existing observer
    # scheduler and focal loop must not block C3 to make up missed time.
    remaining = max(0,allotted-now)
    return {
        "schema": SCHEMA,
        "recovery": recover,
        "reason": reason,
        "preanswer_end_monotonic": max(start, allotted),
        "preanswer_seconds_available": round(remaining,3),
        "c3_reserved_seconds": round(reserve,3),
        "recent_real_prefill_failures": failures,
        "recent_success_streak": recent_good,
        "postcommit_body_eligible": recover and remaining < MIN_ROLE_SLICE_S,
        "minimum_role_slice_s": MIN_ROLE_SLICE_S,
        "age_changed": False,
        "memory_or_native_weights_changed": False,
    }
