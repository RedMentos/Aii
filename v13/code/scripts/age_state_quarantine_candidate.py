"""Run132 read-only persisted Age-state integrity diagnostic.

This candidate is NOT wired into production AgeControl or operator commands.
It must never repair stored state, grant rights or claim runtime containment.
"""
from __future__ import annotations

import math

from v13 import age


class AgeStateIntegrityError(ValueError):
    """Stored Age state is not safe to use for stage/budget calculations."""


def _require(condition, reason):
    if not condition:
        raise AgeStateIntegrityError(reason)


def _stage(value):
    return type(value) is int and 0 <= value <= 5


def _unit(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def _nonnegative_int(value):
    return type(value) is int and value >= 0


def _ids(value, max_count, reason):
    _require(type(value) is list and len(value) <= max_count, reason)
    _require(all(type(item) is str and bool(item) for item in value), reason)
    _require(len(value) == len(set(value)), reason)


def _subject(name, sub):
    _require(type(sub) is dict, "AGE_SUBJECT_SHAPE:" + name)
    _require(_stage(sub.get("stage")), "AGE_STAGE_CORRUPT:" + name)
    _require(_nonnegative_int(sub.get("evidence_count")), "AGE_COUNT_CORRUPT:" + name)
    _require(type(sub.get("fail_streak")) is int
             and 0 <= sub["fail_streak"] <= age.DEMOTE_AFTER,
             "AGE_FAIL_STREAK_CORRUPT:" + name)
    _ids(sub.get("pass_streak"), age.PROMOTE_AFTER, "AGE_PASS_STREAK_CORRUPT:" + name)
    last = sub.get("last_evidence")
    _require(last is None or (type(last) is str and bool(last)),
             "AGE_LAST_EVIDENCE_CORRUPT:" + name)
    maturity = sub.get("maturity")
    _require(type(maturity) is dict, "AGE_MATURITY_SHAPE:" + name)
    for metric in ("trust", "retention", "calibration", "stability", "competence"):
        _require(_unit(maturity.get(metric)), "AGE_MATURITY_CORRUPT:" + name + ":" + metric)
    noise = sub.get("noise")
    if noise is not None:
        _require(type(noise) is dict and _unit(noise.get("mad"))
                 and _nonnegative_int(noise.get("n")),
                 "AGE_NOISE_CORRUPT:" + name)
    hold = sub.get("plasticity_hold")
    if hold is not None:
        _require(type(hold) is dict and _stage(hold.get("stage"))
                 and _nonnegative_int(hold.get("until")),
                 "AGE_PLASTICITY_HOLD_CORRUPT:" + name)


def verify_state(state):
    """Validate a persisted snapshot without mutating it; return same object."""
    _require(type(state) is dict and state.get("revision") == age.REVISION,
             "AGE_STATE_REVISION_CORRUPT")
    for flag in ("frozen", "structural_locked"):
        _require(type(state.get(flag)) is bool, "AGE_FLAG_CORRUPT:" + flag)
    _subject("system", state.get("system"))
    capabilities = state.get("capabilities")
    _require(type(capabilities) is dict
             and all(c in capabilities for c in age.CAPABILITIES),
             "AGE_CAPABILITY_SET_CORRUPT")
    for name, sub in capabilities.items():
        _require(type(name) is str and bool(name), "AGE_CAPABILITY_NAME_CORRUPT")
        _subject(name, sub)
    _ids(state.get("seen_evidence"), 512, "AGE_SEEN_EVIDENCE_CORRUPT")
    history = state.get("history")
    proposals = state.get("proposals")
    _require(type(history) is list and len(history) <= age.HISTORY
             and all(type(item) is dict for item in history),
             "AGE_HISTORY_CORRUPT")
    _require(type(proposals) is list and len(proposals) <= 16
             and all(type(item) is dict for item in proposals),
             "AGE_PROPOSALS_CORRUPT")
    return state


def snapshot(controller):
    """Diagnostic only: corrupt state produces no stage/rights/budget assertion."""
    if not isinstance(controller, age.AgeControl):
        raise ValueError("AGE_CONTROLLER_INVALID")
    state, version = controller.state()
    try:
        verify_state(state)
    except AgeStateIntegrityError as exc:
        return {
            "status": "QUARANTINED_DIAGNOSTIC_ONLY",
            "reason": str(exc),
            "state_version": version,
            "granted_rights": [],
            "budgets": None,
            "effective_stage": None,
            "runtime_enforced": False,
            "read_only": True,
        }
    return {
        "status": "VALID_DIAGNOSTIC_ONLY",
        "state_version": version,
        "stored_stage": state["system"]["stage"],
        "effective_stage": controller.system_stage(state),
        "build_ceiling": controller.build_ceiling,
        "runtime_enforced": False,
        "read_only": True,
    }


def guarded_view(controller):
    """Raise on corruption before using the existing, unchanged view method."""
    if not isinstance(controller, age.AgeControl):
        raise ValueError("AGE_CONTROLLER_INVALID")
    state, _ = controller.state()
    verify_state(state)
    return controller.view()
