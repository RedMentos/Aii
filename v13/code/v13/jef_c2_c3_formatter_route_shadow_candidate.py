"""Run117AW default-OFF source-bound JEF/C2 -> C3 formatter-route SHADOW.

A validated JEF typed action can be formatted, not independently reasoned by C3.
C2 native route proposals are strictly advisory and never override JEF or Runtime.
No model inference, output, TTY approval, tools, training or age promotion.
"""
from __future__ import annotations

from hashlib import sha256
from .common import dumps
from .c2_monotone_route_shadow import choose as c2_choose
from .jef_c3_typed_envelope_candidate import build_jef_c3_typed_envelope

SCHEMA = "v13.run117aw.jef_c2_c3_formatter_route_shadow.v1"
READY = "JEF_TYPED_C3_FORMATTER_ROUTE_SHADOW_NO_MODEL_CALL"
JEF_READY = "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL"
NEGATIVE = {
    "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
    "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
    "world_jepa_authority": "SHADOW", "jepa_weight": 0,
    "redmi_measured": False, "whole_system_complete": False,
}


def _receipt(status, **extra):
    return {
        "schema": SCHEMA, "status": status,
        "formatter_route": None, "route_applied": False,
        "c2_native_proof": False, "c3_native_proof": False,
        "native_model_called": False, "output_committed": False,
        "tool_dispatches": 0, "delivery_authority": 0,
        "learning_authority": 0, "real_tty_approved": False,
        "source_semantic_truth_authority": False,
        "independent_c3_reasoning_proven": False,
        "negative_gates": dict(NEGATIVE), **extra,
    }


def _epoch(store):
    if store.db.in_transaction:
        raise ValueError("ACTIVE_TRANSACTION_RED")
    return (store.db.total_changes,
            store.db.execute("PRAGMA data_version").fetchone()[0],
            store.generation_id)


def propose(runtime, event, memory_ids, *,
            operator_opt_in=False, callback_opt_in=False,
            approval_receipt=None, executive_admissible=True,
            native_control=None, calibration=None, scaffold_route="simple",
            effort_band="DIRECT_C_NATIVE", resource_wake_ceiling="none",
            cancelled=False):
    """Return a source-bound, zero-authority formatter route proposal.

    Optional C2 observations must already be measured and independently
    calibrated; this function never calls Needle or grants native authority.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _receipt("OFF")
    if approval_receipt is not None:
        return _receipt("REAL_TTY_APPROVAL_UNSUPPORTED")
    if type(cancelled) is not bool or cancelled:
        return _receipt("CANCELLED_OR_INVALID")
    if type(executive_admissible) is not bool or not executive_admissible:
        return _receipt("EXECUTIVE_VETO")
    if (type(scaffold_route) is not str or
            scaffold_route not in ("simple", "detail", "gist", "both") or
            type(effort_band) is not str or
            effort_band not in ("DIRECT_C_NATIVE", "C_NATIVE_ONE_BODY",
                                "FOCAL_TARGETED", "DEEP_FOCAL") or
            type(resource_wake_ceiling) is not str or
            resource_wake_ceiling not in ("none", "one", "both")):
        return _receipt("ROUTE_OR_RESOURCE_INPUT_RED")
    if (type(event) is not dict or
            type(event.get("event_id")) is not str or
            type(event.get("source_ref")) is not dict or
            type(memory_ids) not in (list, tuple) or len(memory_ids) != 2):
        return _receipt("SOURCE_INPUT_RED")
    try:
        store = runtime.store
        before = _epoch(store)
        first = build_jef_c3_typed_envelope(
            runtime.memory, runtime.session, event["event_id"],
            event["source_ref"], memory_ids, operator_opt_in=True)
        if (first.get("status") != JEF_READY or
                first.get("typed_jef_action") not in ("A", "B", "NONE") or
                first.get("source_rechecked") is not True or
                first.get("formatter_only") is not True or
                first.get("native_proof") is not False or
                first.get("model_called") is not False or
                first.get("delivery_authority") != 0 or
                first.get("learning_authority") != 0):
            return _receipt("JEF_SOURCE_ADMISSION_RED",
                            jef_status=first.get("status"))
        prompt = first.get("messages")
        prompt_sha = first.get("messages_sha256")
        if (type(prompt) is not list or len(prompt) != 2 or
                [m.get("role") for m in prompt] != ["system", "user"] or
                type(prompt_sha) is not str or len(prompt_sha) != 64 or
                sha256(dumps(prompt).encode("utf-8")).hexdigest() != prompt_sha):
            return _receipt("JEF_PROMPT_INTEGRITY_RED")
        c2 = {"status": "NOT_SUPPLIED", "changed": False,
              "native_validated": False, "authority": "SHADOW_ONLY"}
        if native_control is not None:
            try:
                if (type(native_control) is not dict or
                        len(dumps(native_control).encode("utf-8")) > 8192):
                    raise ValueError("CONTROL_INPUT_RED")
                raw = c2_choose(
                    scaffold_route, native_control,
                    effort_band=effort_band,
                    resource_wake_ceiling=resource_wake_ceiling,
                    executive_admissible=True, source_bound=True,
                    calibration=calibration)
                c2 = {"status": raw["reason"],
                      "changed": raw["changed"],
                      "native_validated": raw["native_validated"],
                      "authority": "SHADOW_ONLY",
                      "proposed_body_route": raw["selected_route"]}
            except (ValueError, TypeError, KeyError, OverflowError,
                    RecursionError, UnicodeError):
                c2 = {"status": "C2_INPUT_OR_CALIBRATION_RED",
                      "changed": False, "native_validated": False,
                      "authority": "SHADOW_ONLY"}
        second = build_jef_c3_typed_envelope(
            runtime.memory, runtime.session, event["event_id"],
            event["source_ref"], memory_ids, operator_opt_in=True)
        if (_epoch(store) != before or
                second.get("status") != JEF_READY or
                second.get("messages_sha256") != prompt_sha or
                second.get("source_ref_sha256") != first.get("source_ref_sha256") or
                second.get("typed_jef_action") != first["typed_jef_action"] or
                dumps(second) != dumps(first)):
            return _receipt("SOURCE_CHANGED_DURING_ROUTE")
        return _receipt(
            READY, formatter_route="JEF_TYPED_C3_FORMATTER_ONLY",
            route_applied=False, source_rechecked=True,
            typed_jef_action=first["typed_jef_action"],
            source_ref_sha256=first["source_ref_sha256"],
            current_source_sha256=first["current_source_sha256"],
            messages=prompt, messages_sha256=prompt_sha,
            c2_advisory=c2, c2_cannot_override_jef=True,
            model_hypothesis_not_fact=True,
        )
    except (AttributeError, ValueError, TypeError, KeyError, OverflowError,
            RecursionError, UnicodeError):
        return _receipt("SOURCE_OR_STORE_INTEGRITY_RED")
