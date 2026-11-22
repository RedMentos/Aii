"""Default-OFF read-only USER SourceRef transport for B1/B2 -> JEF/C3.

A source pointer is NOT a verified quote produced by a body model. This
candidate transports exact USER text separately from fallible B1/B2 offers;
it cannot replace evidence that a native body quoted the source correctly.
No live Runtime wiring, model inference, egress, actions, or learning.
"""
from __future__ import annotations

from .b1b2_causal_context_candidate import _bound_user_event, _project_scope
from .jef_f1f5_live_current_candidate import _latest_authoritative_user


def _base(status):
    return {
        "schema": "v13.two_source_pointer_shadow.v1",
        "status": status,
        "source_transport_only": True,
        "body_model_quote_verified": False,
        "body_model_called": False,
        "native_calls": 0,
        "jef_model_called": False,
        "output_committed": False,
        "tool_dispatches": 0,
        "learning_authority": 0,
        "delivery_authority": 0,
        "source_semantic_truth_authority": False,
        "age0": "RECORD_ONLY",
        "step2_exit": "EVIDENCE_NOT_PASSING",
        "b3": "NO_PROMOTION",
        "jepa_weight": 0,
        "whole_system_complete": False,
    }


def bind_two_source(runtime, prior_event, current_event, *, operator_opt_in=False):
    """Bind exactly two same-project USER events with latest-turn veto.

    This returns a SHADOW source bundle for a future *separately approved*
    Context OS adapter, not a replacement for Cognition.analyst_context.
    """
    if operator_opt_in is not True:
        return _base("OFF")
    if type(prior_event) is not dict or type(current_event) is not dict:
        return _base("INVALID_INPUT_RED")
    store = runtime.store
    try:
        with store.mutex:
            before = store.db.total_changes
            prior = _bound_user_event(store, prior_event["event_id"], runtime.session)
            current = _bound_user_event(store, current_event["event_id"], runtime.session)
            if (prior_event.get("source_ref") != prior["source_ref"]
                    or current_event.get("source_ref") != current["source_ref"]
                    or prior_event.get("brain_generation_id") != prior["generation"]
                    or current_event.get("brain_generation_id") != current["generation"]
                    or prior["generation"] != current["generation"]
                    or current["generation"] != store.generation_id):
                raise ValueError("SOURCE_BINDING_RED")
            if prior["message_id"] >= current["message_id"]:
                raise ValueError("SOURCE_ORDER_RED")
            scope = _project_scope(prior["text"])
            if not scope or _project_scope(current["text"]) != scope:
                raise ValueError("SOURCE_PROJECT_SCOPE_RED")
            if _latest_authoritative_user(store, runtime.session) != current_event["event_id"]:
                raise ValueError("LATEST_USER_STALE_RED")
            if (_bound_user_event(store, prior_event["event_id"], runtime.session) != prior
                    or _bound_user_event(store, current_event["event_id"], runtime.session) != current
                    or _latest_authoritative_user(store, runtime.session) != current_event["event_id"]
                    or store.db.total_changes != before):
                raise ValueError("SOURCE_CHANGED_DURING_READ_RED")
            result = _base("SHADOW_TWO_SOURCE_POINTER_VERIFIED")
            result["project_scope"] = next(iter(scope))
            result["sources"] = [
                {"lane": "B2_PRIOR_USER_SOURCE", "source_ref": dict(prior["source_ref"]),
                 "text": prior["text"], "origin": "STORE_EXACT_USER_NOT_MODEL_QUOTE"},
                {"lane": "B1_CURRENT_USER_SOURCE", "source_ref": dict(current["source_ref"]),
                 "text": current["text"], "origin": "STORE_EXACT_USER_NOT_MODEL_QUOTE"},
            ]
            return result
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return _base("SOURCE_POINTER_REFUSED_RED")
