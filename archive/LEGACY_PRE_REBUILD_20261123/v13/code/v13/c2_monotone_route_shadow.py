"""Run41 isolated C2/JEF monotone route advisory; never production authority.

The native observation parser is the frozen control-calibration worker. This
module does not call Needle, mutate Store, approve tools, or select live routes.
"""
from __future__ import annotations

import math

from .common import Cancelled
from .control_calibration_worker import observation
from .c2_route_admission_shadow import (
    CALIBRATION_SCOPE, MIN_ROUTE_SUPPORT, MIN_CONFIDENCE,
)

ROUTES = ("simple", "detail", "gist", "both")
BANDS = {"DIRECT_C_NATIVE": "none", "C_NATIVE_ONE_BODY": "one",
         "FOCAL_TARGETED": "both", "DEEP_FOCAL": "both"}
WAKE_LEVEL = {"none": 0, "one": 1, "both": 2}
ROUTE_LEVEL = {"simple": 0, "detail": 1, "gist": 1, "both": 2}
UPGRADES = {"simple": frozenset(("detail", "gist", "both")),
            "detail": frozenset(("both",)),
            "gist": frozenset(("both",)),
            "both": frozenset()}
NEGATIVE_GATES = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
                  "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
                  "jepa_weight": 0, "world_jepa_authority": "SHADOW"}


def choose(scaffold, control, *, effort_band, resource_wake_ceiling,
           executive_admissible, source_bound, calibration=None, cancelled=False):
    """Compute a *non-authoritative* monotone proposal under both ceilings.

    Caller must supply current executive/source decisions. A future live
    integration requires separate approval, source/age gates and native proof.
    """
    if (type(scaffold) is not str or scaffold not in ROUTES or
            type(effort_band) is not str or effort_band not in BANDS or
            type(resource_wake_ceiling) is not str or resource_wake_ceiling not in WAKE_LEVEL):
        raise ValueError("RUN41_ROUTE_OR_BUDGET_UNKNOWN")
    if any(type(x) is not bool for x in (executive_admissible, source_bound,
                                         cancelled)):
        raise ValueError("RUN41_UNTYPED_GUARD")
    if cancelled:
        raise Cancelled()
    base = {"schema": "v13.run41.c2_monotone_route_shadow.v1",
            "scaffold": scaffold, "selected_route": scaffold,
            "changed": False, "native_validated": False,
            "authority": "SHADOW_ONLY", "negative_gates": dict(NEGATIVE_GATES)}

    def deny(reason, native=False):
        return dict(base, reason=reason, native_validated=native)

    if not source_bound:
        return deny("SOURCE_UNBOUND")
    if not executive_admissible:
        return deny("EXECUTIVE_ABSTAIN")
    calls = control.get("function_calls") if type(control) is dict else None
    if (type(calls) is not list or len(calls) != 1 or
            type(calls[0]) is not dict or calls[0].get("name") != "select_processing"):
        return deny("NOT_ONE_NATIVE_SELECT_PROCESSING")
    try:
        obs = observation(control)
        if (obs["proposal_count"] != 1 or obs["ambiguous"] is not False or
                obs["route"] not in ROUTES):
            return deny("NATIVE_AMBIGUOUS")
    except (ValueError, TypeError, KeyError, OverflowError):
        return deny("NATIVE_VALIDATION_FAIL")
    native = obs["route"]
    # Existing frozen C2 route admission SHADOW is stricter than Runtime:
    # calibration must be approved and bound to this exact observation.
    if type(calibration) is not dict:
        return deny("NO_APPROVED_CALIBRATION", True)
    if (calibration.get("route") != obs["route"] or
            type(calibration.get("raw_confidence")) not in (int, float) or
            calibration["raw_confidence"] != obs["raw_confidence"] or
            calibration.get("proposal_count") != obs["proposal_count"] or
            calibration.get("ambiguous") is not False):
        return deny("CALIBRATION_SOURCE_MISMATCH", True)
    confidence = calibration.get("calibrated_confidence")
    count = calibration.get("route_observation_count")
    try:
        calibrated_finite = (type(confidence) in (int, float) and math.isfinite(confidence))
    except (OverflowError, ValueError, TypeError):
        calibrated_finite = False
    if (calibration.get("in_support") is not True or
            calibration.get("calibration_scope") != CALIBRATION_SCOPE or
            calibration.get("semantic_truth_authority") is not False or
            type(count) is not int or count < MIN_ROUTE_SUPPORT or
            not calibrated_finite or not 0 <= confidence <= 1):
        return deny("CALIBRATION_UNSUPPORTED", True)
    if confidence < MIN_CONFIDENCE:
        return deny("CALIBRATION_BELOW_THRESHOLD", True)
    if native == scaffold:
        return deny("SAME_ROUTE", True)
    if native not in UPGRADES[scaffold]:
        return deny("DEMOTION_OR_LATERAL_REFUSED", True)
    budget = min(WAKE_LEVEL[BANDS[effort_band]], WAKE_LEVEL[resource_wake_ceiling])
    if ROUTE_LEVEL[native] > budget:
        return deny("EFFORT_OR_RESOURCE_CEILING", True)
    return dict(base, selected_route=native, changed=True,
                native_validated=True, reason="MONOTONE_UPGRADE_SHADOW")
