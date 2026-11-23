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
RECOVERY_FOCAL_RESERVE_S = 1.0


def register_store_telemetry():
    """Extend the mutable Store telemetry allowlist without editing shared Store code."""
    from . import store

    store.TELEMETRY_FIELDS.update({
        "preanswer_seconds_available",
        "c3_reserved_seconds",
        "recent_real_prefill_failures",
        "minimum_role_slice_s",
    })
    store.TELEMETRY_ENUMS.update({
        "PREANSWER_BUDGETED",
        "POSTCOMMIT_ELIGIBLE",
        "native_turn_budget_plan",
        "native_turn_budget_unavailable",
        "native_body_budgeted_for_c3",
        "native_body_deferred_for_c3",
    })


# Runtime imports this module before emitting budget telemetry. Keeping the
# registration here avoids changing Store's shared source/pin contract.
register_store_telemetry()


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
    # The total pre-answer envelope includes both initial body work and C4.
    # During C3 recovery, reserve its final second for focal selection/re-entry;
    # B1/B2 receive only the earlier body window. Normal turns keep the old
    # shared observer/focal envelope unchanged.
    preanswer_end=max(start,allotted)
    focal_reserve=(min(RECOVERY_FOCAL_RESERVE_S,max(0.,preanswer_end-start))
                   if recover else 0.)
    body_end=max(start,preanswer_end-focal_reserve)
    # Per-role callers may further cap the body window. Do not subtract the
    # focal reserve twice when Cognition checks an already allocated role slice.
    effective_body_end=body_end if observer_deadline is None else min(body_end,observer_deadline)
    remaining=max(0.,effective_body_end-now)
    return {
        "schema": SCHEMA,
        "recovery": recover,
        "reason": reason,
        "preanswer_end_monotonic": preanswer_end,
        "body_preanswer_end_monotonic": body_end,
        "focal_reserved_seconds": round(focal_reserve,3),
        "preanswer_seconds_available": round(remaining,3),
        "c3_reserved_seconds": round(reserve,3),
        "recent_real_prefill_failures": failures,
        "recent_success_streak": recent_good,
        "postcommit_body_eligible": recover and remaining < MIN_ROLE_SLICE_S,
        "minimum_role_slice_s": MIN_ROLE_SLICE_S,
        "age_changed": False,
        "memory_or_native_weights_changed": False,
    }
