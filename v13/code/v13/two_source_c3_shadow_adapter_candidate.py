"""Default-OFF exact USER two-source -> Context OS C3 plan, SHADOW only.

Source transport is not B1/B2 model quotation, JEF learning, native C3 or
approved output. ContextPlan is an internal SHADOW record, not delivery.
"""
from __future__ import annotations

from . import context_os as ctxos
from .two_source_pointer_shadow_candidate import bind_two_source


def _deny(status, *, orphaned_shadow_plan_packet_id=None):
    result = {"schema": "v13.two_source_c3_shadow_adapter.v1",
              "status": status, "applied": False,
              "source_transport_only": True,
              "body_model_quote_verified": False,
              "native_c3_calls": 0, "native_body_calls": 0,
              "output_committed": False, "tool_dispatches": 0,
              "delivery_authority": 0, "learning_authority": 0,
              "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
              "b3": "NO_PROMOTION", "jepa_weight": 0,
              "whole_system_complete": False}
    if orphaned_shadow_plan_packet_id is not None:
        result["orphaned_shadow_plan_packet_id"] = orphaned_shadow_plan_packet_id
    return result


def plan_c3_two_source(runtime, prior_event, current_event, *, operator_opt_in=False):
    if operator_opt_in is not True:
        return _deny("OFF")
    context = ctxos.controller(runtime)
    try:
        if context._load()[0]["mode"] != "SHADOW":
            return _deny("CONTEXT_OS_NOT_SHADOW_RED")
        bound = bind_two_source(runtime, prior_event, current_event, operator_opt_in=True)
        if bound["status"] != "SHADOW_TWO_SOURCE_POINTER_VERIFIED":
            return _deny("SOURCE_POINTER_REFUSED_RED")
        sources = bound["sources"]
        payload = {"source_transport_only": True,
                   "body_model_quote_verified": False,
                   "prior": {"source_ref": sources[0]["source_ref"],
                             "text": sources[0]["text"]},
                   "current": {"source_ref": sources[1]["source_ref"],
                               "text": sources[1]["text"]}}
        plan = context.plan(
            current_event["event_id"], "C3_LANGUAGE",
            "Only the following source-bound USER records are factual inputs. "
            "No body-model quote or semantic correctness is proven.",
            [("SOURCE_LINKS", "\nExact USER source pointers (not B1/B2 quotes):\n", payload)],
            [], sources[1]["text"],
            provenance=[sources[0]["source_ref"], sources[1]["source_ref"]])
        pid = plan["packet_id"]
        if (plan["applied"] is not False or plan["plan"]["mode"] != "SHADOW"
                or plan["plan"].get("provenance") !=
                [sources[0]["source_ref"], sources[1]["source_ref"]]):
            return _deny("CONTEXT_PLAN_AUTHORITY_RED", orphaned_shadow_plan_packet_id=pid)
        combined = "\n".join(m["content"] for m in plan["messages"])
        if not all(s["text"] in combined for s in sources):
            return _deny("CONTEXT_PLAN_SOURCE_LOST_RED", orphaned_shadow_plan_packet_id=pid)
        after = bind_two_source(runtime, prior_event, current_event, operator_opt_in=True)
        if after != bound:
            return _deny("POST_PLAN_STALE_SOURCE_RED", orphaned_shadow_plan_packet_id=pid)
        result = _deny("SHADOW_C3_SOURCE_PLAN_VERIFIED")
        result.update(context_plan_packet_id=pid, source_refs=[s["source_ref"] for s in sources],
                      messages=plan["messages"], applied=False)
        return result
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return _deny("CONTEXT_PLAN_REFUSED_RED")
