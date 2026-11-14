"""Measured-failure recovery for the *whole-turn* native compute envelope.

Why this exists: on a real 30 s Redmi turn, observers held the pipeline until
~15 s; then C3 alone needed 10.8 s for native load and still got 0 generated
tokens before the deadline. Reducing C3's prompt to 161 tokens did not help.
A pre-answer B1/B2 pass that repeatedly yields zero usable offers must not
consume the last time reserved for the only external C3 output.

This is *not* permanently removing either hemisphere. It temporarily moves
their work to the already existing, bounded post-commit observer path when
the owner uses background observers, the deadline is short, and at least two
recent real C3 turns failed before generating any token. Long/deep turns
retain the original 45% pre-answer observation window. Age remains unchanged.
"""

from __future__ import annotations

import json
import math


SCHEMA = "v13.native-turn-budget/1"
MAX_RECENT = 6
RECOVERY_MAX_DEADLINE_S = 50
NATIVE_FIRST_RESERVE_FRACTION = .87
DEFAULT_PREANSWER_FRACTION = .45


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


def plan(start, deadline, now, *, recent=(), background_enabled=True, direct=False):
    for number in (start,deadline,now):
        if type(number) not in (int, float) or not math.isfinite(number):
            raise ValueError("invalid monotonic budget")
    if deadline < start or now < start-1:
        raise ValueError("time plan clocks invalid")
    total = deadline-start
    ordinary_end = start+DEFAULT_PREANSWER_FRACTION*total
    bounded = list(recent)[:MAX_RECENT]
    # A completed successful C3 turn closes the old failure epoch.  A stale
    # pair of timeouts must not keep suppressing synchronous B1/B2 forever
    # merely because fewer than two subsequent FINAL turns fit in the window.
    # Only failures newer than the most recent successful C3 output count.
    failures = 0
    for row in bounded:
        if not isinstance(row, dict):
            break
        if row.get("status") == "FINAL":
            break
        if zero_token_prefill_failure(row):
            failures += 1
    recent_good = 0
    for row in bounded:
        if not isinstance(row, dict):
            break
        status=row.get("status")
        if status == "FINAL":
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
        "postcommit_body_eligible": recover,
        "age_changed": False,
        "memory_or_native_weights_changed": False,
    }
