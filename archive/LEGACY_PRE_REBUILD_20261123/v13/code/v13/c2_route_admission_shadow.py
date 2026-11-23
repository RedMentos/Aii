"""Source-bound C2 route admission SHADOW candidate, not wired into Runtime.

An uncalibrated Needle tool call has no route authority. This pure function
evaluates whether an already approved calibration *would* admit a validated
proposal. It never changes routing, weights, Age or permissions.
"""
import math

from .control_calibration_worker import observation

REVISION = "c2-route-admission-shadow-v1"
ROUTES = ("simple", "detail", "gist", "both")
CALIBRATION_SCOPE = "HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY"
MIN_CONFIDENCE = .6
MIN_ROUTE_SUPPORT = 3


def evaluate(scaffold_route, native_control, calibration):
    """Return an evidence-bound, non-authoritative decision; never apply it."""
    if type(scaffold_route) is not str or scaffold_route not in ROUTES:
        raise ValueError("Expected existing scaffold route")
    result = {
        "revision": REVISION, "scaffold_route": scaffold_route,
        "native_route": None, "candidate_route": None,
        "would_admit": False, "reason": "INVALID_NATIVE_CONTROL",
        "calibrated_confidence": None,
        "authority": "SHADOW_ONLY_NO_RUNTIME_ROUTE",
        "applied": False, "age_authority": 0,
        "model_called": False, "weight_updates": False,
    }
    try:
        observed = observation(native_control)
        calls = native_control.get("function_calls")
        # Do not inherit Runtime's recursive route scan: a foreign or earlier
        # nested route can disagree with the validated select_processing call.
        if (type(calls) is not list or len(calls) != 1
                or type(calls[0]) is not dict
                or calls[0].get("name") != "select_processing"
                or observed["proposal_count"] != 1 or observed["ambiguous"]):
            return result
    except (ValueError, TypeError, KeyError, OverflowError):
        return result
    result["native_route"] = observed["route"]
    if type(calibration) is not dict:
        result["reason"] = "NO_APPROVED_CALIBRATION"
        return result
    if (calibration.get("route") != observed["route"]
            or type(calibration.get("raw_confidence")) not in (int, float)
            or calibration["raw_confidence"] != observed["raw_confidence"]
            or calibration.get("proposal_count") != observed["proposal_count"]
            or calibration.get("ambiguous") is not False):
        result["reason"] = "CALIBRATION_SOURCE_MISMATCH"
        return result
    confidence = calibration.get("calibrated_confidence")
    count = calibration.get("route_observation_count")
    if (calibration.get("in_support") is not True
            or calibration.get("calibration_scope") != CALIBRATION_SCOPE
            or calibration.get("semantic_truth_authority") is not False
            or type(count) is not int or count < MIN_ROUTE_SUPPORT
            or type(confidence) not in (int, float)
            or not math.isfinite(confidence) or not 0. <= confidence <= 1.):
        result["reason"] = "UNSUPPORTED_CALIBRATION"
        return result
    result["calibrated_confidence"] = float(confidence)
    if confidence < MIN_CONFIDENCE:
        result["reason"] = "BELOW_CALIBRATED_THRESHOLD"
    elif scaffold_route != "simple":
        result["reason"] = "SCAFFOLD_NOT_SIMPLE"
    else:
        result.update(would_admit=True, candidate_route=observed["route"],
                      reason="ELIGIBLE_SHADOW_ONLY")
    return result
