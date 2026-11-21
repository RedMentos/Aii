"""Bounded recovery for the whole-turn native compute envelope.

Two recent real C3 zero-token prefill deadlines are a risk signal, not a
blanket veto on both pre-answer bodies. The Runtime already owns the actual
pre-answer observer window (start + 45% of the turn deadline); its scheduler
stops body work at that boundary and leaves the remaining 55% for C3.

Recovery therefore defers a body only after that real observer window has
expired (or has less than the scheduler's one-second start allowance). It
never extends the turn deadline, changes Age, or mutates model weights.
"""

from __future__ import annotations

import json
import math


SCHEMA = "v13.native-turn-budget/2"
MAX_RECENT = 6
RECOVERY_MAX_DEADLINE_S = 50
DEFAULT_PREANSWER_FRACTION = .45
MIN_BODY_START_WINDOW_S = 1.0


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
        return [{"status": r["status"], "metadata": r["metadata"]} for r in rows]
    except (OSError, ValueError, RuntimeError):
        return []


def plan(start, deadline, now, *, recent=(), background_enabled=True, direct=False):
    for number in (start, deadline, now):
        if type(number) not in (int, float) or not math.isfinite(number):
            raise ValueError("invalid monotonic budget")
    if deadline < start or now < start - 1:
        raise ValueError("time plan clocks invalid")
    total = deadline - start
    preanswer_end = start + DEFAULT_PREANSWER_FRACTION * total
    bounded = list(recent)[:MAX_RECENT]
    failures = sum(zero_token_prefill_failure(row) for row in bounded)
    recent_good = 0
    for row in bounded:
        if not isinstance(row, dict):
            break
        status = row.get("status")
        if status == "FINAL":
            recent_good += 1
        else:
            break
        if recent_good == 2:
            break
    recovery_detected = (
        not direct and background_enabled is True
        and total <= RECOVERY_MAX_DEADLINE_S and total >= 5
        and failures >= 2 and recent_good < 2
    )
    # This is the same absolute boundary used by Runtime.observer_end and
    # observer_schedule.run. Do not invent a second, earlier C3 reserve.
    reserve = max(0.0, deadline - preanswer_end)
    remaining = max(0.0, preanswer_end - now)
    preanswer_eligible = remaining >= MIN_BODY_START_WINDOW_S
    # Cognition.offer historically reads `recovery` as the defer decision.
    # Keep that interface, but distinguish the detected risk from whether the
    # actual pre-answer window is still available.
    defer_preanswer = recovery_detected and not preanswer_eligible
    reason = ("RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS" if recovery_detected
              else "NORMAL_COGNITIVE_PREANSWER")
    return {
        "schema": SCHEMA,
        "recovery": defer_preanswer,
        "recovery_detected": recovery_detected,
        "preanswer_eligible": preanswer_eligible,
        "reason": reason,
        "preanswer_end_monotonic": max(start, preanswer_end),
        "preanswer_seconds_available": round(remaining, 3),
        "c3_reserved_seconds": round(reserve, 3),
        "recent_real_prefill_failures": failures,
        "recent_success_streak": recent_good,
        "postcommit_body_eligible": recovery_detected,
        "age_changed": False,
        "memory_or_native_weights_changed": False,
    }
