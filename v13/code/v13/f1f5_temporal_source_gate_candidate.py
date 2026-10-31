"""Default-OFF temporal F1/F5 source gate for the Runtime C3 DRAFT bridge.

Only permits a correction that was recorded before the current USER query.
This is not a transactional C6 commit and not installed in live Runtime.
"""
from __future__ import annotations

import math
import time

from .f1f5_event_finalizer_candidate import _event_snapshot, _verified
from .f1f5_c5c6_atomic_draft_candidate import _locked_verified
from .runtime_c3_atomic_draft_candidate import stage_runtime_c3_draft


def _result(status, **extra):
    return {"schema": "v13.f1f5_temporal_source_gate.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False,
            "model_called": False, **extra}


def _ordered_source(runtime, session, current_event, generation, admitted):
    """Must be called with the Store transaction held; never write state."""
    store = runtime.store
    source = admitted["source"]
    mid = source["memory_id"]
    memory = runtime.memory.candidate(mid, session)
    if (memory["source_ref"] != source["source_ref"]
            or memory["value"] != source["value"]
            or memory["key_text"] != source["topic"]
            or memory["kind"] != "fact" or memory["scope"] != "session"
            or memory["session_id"] != session):
        return "MEMORY_LINEAGE_RED"
    correction_event = memory["event_id"]
    if correction_event == current_event:
        return "TEMPORAL_SOURCE_RED"
    rows = {}
    for event_id in (correction_event, current_event):
        event = store.one(
            "SELECT session_id,generation_id FROM events WHERE id=?", (event_id,))
        if (not event or event["session_id"] != session
                or event["generation_id"] != generation):
            return "EVENT_GENERATION_RED"
        messages = store.rows(
            "SELECT id,status FROM messages WHERE event_id=? AND session_id=? "
            "AND role='user'", (event_id, session))
        if len(messages) != 1 or messages[0]["status"] != "FINAL":
            return "USER_MESSAGE_LINEAGE_RED"
        rows[event_id] = messages[0]["id"]
    feedback = store.rows(
        "SELECT event_id,kind,value,permission FROM feedback WHERE source_id=?",
        (memory["source_id"],))
    if (len(feedback) != 1 or feedback[0]["event_id"] != correction_event
            or feedback[0]["kind"] != "fact"
            or feedback[0]["value"] != memory["value"]
            or feedback[0]["permission"] != "record"):
        return "FEEDBACK_LINEAGE_RED"
    if rows[correction_event] >= rows[current_event]:
        return "TEMPORAL_SOURCE_RED"
    return "SOURCE_ORDER_VERIFIED"


def stage_temporal_runtime_c3_draft(runtime, event_id, deadline, *,
                                    operator_opt_in=False,
                                    model_call_opt_in=False, max_tokens=96):
    if operator_opt_in is not True or model_call_opt_in is not True:
        return _result("OFF")
    if (type(event_id) is not str or not event_id
            or type(deadline) not in (int, float)
            or not math.isfinite(deadline)
            or time.monotonic() >= deadline
            or type(max_tokens) is not int or not 1 <= max_tokens <= 256):
        return _result("INVALID_OR_EXPIRED_INPUT")
    try:
        session = runtime.session
        initial = _event_snapshot(runtime.memory, event_id, session)
        first = _verified(runtime.memory, runtime.cfg, session, initial)
        if first is None:
            return _result("CLARIFY")
        with runtime.store.tx():
            if _event_snapshot(runtime.memory, event_id, session) != initial:
                return _result("SOURCE_CHANGED_BEFORE_C3")
            locked = _locked_verified(runtime.memory, runtime.cfg, session, initial)
            if locked != first:
                return _result("SOURCE_CHANGED_BEFORE_C3")
            ordered = _ordered_source(
                runtime, session, event_id, initial["generation"], locked)
            if ordered != "SOURCE_ORDER_VERIFIED":
                return _result(ordered)
    except Exception:
        return _result("EVENT_OR_SOURCE_RED")
    staged = stage_runtime_c3_draft(
        runtime, event_id, deadline, operator_opt_in=True,
        model_call_opt_in=True, max_tokens=max_tokens)
    if staged["status"] != "RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT":
        return dict(staged, temporal_source_verified=False)
    try:
        with runtime.store.tx():
            fresh = _event_snapshot(runtime.memory, event_id, session)
            locked = _locked_verified(runtime.memory, runtime.cfg, session, fresh)
            if (fresh != initial or locked != first
                    or _ordered_source(runtime, session, event_id,
                                       initial["generation"], locked)
                    != "SOURCE_ORDER_VERIFIED"):
                return _result("POST_STAGE_TEMPORAL_RED",
                               model_called=staged["model_called"],
                               draft_message_id=staged["draft_message_id"])
    except Exception:
        return _result("POST_STAGE_TEMPORAL_RED",
                       model_called=staged["model_called"],
                       draft_message_id=staged["draft_message_id"])
    return dict(staged, temporal_source_verified=True,
                temporal_gate="SOURCE_ORDER_BEFORE_AND_AFTER_SHADOW_ONLY")
