"""Run61: default-OFF cross-organ B1/B2 + F1/F5 + C6 v2 DRAFT SHADOW.

Real Store source/OfferPacket/retained-state lifecycle; generator is a
synthetic software seam, not native proof. No TTY approval, output, tools,
learning, or production Runtime installation.
"""
from __future__ import annotations

from .b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from .c6_budget_lexical_v2_candidate import preflight_budget_lexical_v2
from .common import dumps
from .f1f5_event_finalizer_candidate import _event_snapshot
from .f1f5_temporal_atomic_draft_candidate import (
    stage_temporal_atomic_draft, check_temporal_staged_draft)
from .runtime_c3_atomic_draft_candidate import _idle


def _result(status, **extra):
    return {"schema": "v13.run61_crossorgan_c6_v2_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def stage_run61_crossorgan_c6_v2_shadow(runtime, event, offer_packet_ids, generate, *,
                                       operator_opt_in=False, callback_opt_in=False,
                                       approval_receipt=None):
    """Only a DRAFT and read-only C6 preflight; no output authority.

    A future atomic writer must repeat source, OfferPacket, DRAFT and TTY
    consent checks in its own transaction. This wrapper does not reserve an
    event across concurrent generators and cannot roll back a staged DRAFT.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED", callback_invoked=False)
    if (not callable(generate) or type(event) is not dict
            or type(offer_packet_ids) is not dict
            or type(event.get("event_id")) is not str):
        return _result("INVALID_INPUT", callback_invoked=False)
    if not _idle(runtime):
        return _result("RUNTIME_NOT_IDLE", callback_invoked=False)

    frozen_event = dict(event)
    frozen_ids = dict(offer_packet_ids)
    try:
        with runtime.store.tx():
            existing_message = runtime.store.one(
                "SELECT id FROM messages WHERE event_id=? AND session_id=? "
                "AND role='assistant' LIMIT 1",
                (frozen_event["event_id"], runtime.session))
            existing_action = runtime.store.one(
                "SELECT id FROM actions WHERE event_id=? AND kind='TEXT_REPORT' LIMIT 1",
                (frozen_event["event_id"],))
            if existing_message is not None or existing_action is not None:
                return _result("EXISTING_OUTPUT_OR_ACTION_RED", callback_invoked=False)
    except Exception:
        return _result("OUTPUT_PREFLIGHT_INTEGRITY_RED", callback_invoked=False)

    envelope = build_c3_source_envelope(
        runtime, frozen_event, frozen_ids, operator_opt_in=True)
    if envelope.get("status") != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
        return _result("BODY_SOURCE_ENVELOPE_RED", callback_invoked=False,
                       envelope_status=envelope.get("status"))
    try:
        initial = _event_snapshot(
            runtime.memory, frozen_event["event_id"], runtime.session)
        if initial["ref"] != envelope["source_ref"]:
            return _result("SOURCE_CHANGED_BEFORE_DRAFT", callback_invoked=False)
    except Exception:
        return _result("EVENT_OR_SOURCE_RED", callback_invoked=False)

    def unchanged():
        current = build_c3_source_envelope(
            runtime, frozen_event, frozen_ids, operator_opt_in=True)
        if current.get("status") != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
            return False, current.get("status")
        if (current.get("messages_sha256") != envelope["messages_sha256"]
                or current.get("source_ref") != envelope["source_ref"]
                or current.get("offer_packet_ids") != envelope["offer_packet_ids"]
                or dumps(current["messages"]) != dumps(envelope["messages"])
                or _event_snapshot(runtime.memory, frozen_event["event_id"],
                                   runtime.session) != initial):
            return False, "SOURCE_OR_ENVELOPE_CHANGED"
        return True, "UNCHANGED"

    called = [False]
    violation = []

    def fused_generate(f1f5_messages):
        ok, reason = unchanged()
        if not ok:
            violation.append(reason)
            raise RuntimeError("RUN61_BODY_OR_SOURCE_CHANGED_BEFORE_CALLBACK")
        if (type(f1f5_messages) is not list
                or len(f1f5_messages) != 2
                or [x.get("role") for x in f1f5_messages] != ["system", "user"]):
            raise RuntimeError("RUN61_F1F5_RENDER_RED")
        called[0] = True
        candidate = generate(envelope["messages"], f1f5_messages)
        ok, reason = unchanged()
        if not ok:
            violation.append(reason)
            raise RuntimeError("RUN61_BODY_OR_SOURCE_CHANGED_AFTER_CALLBACK")
        return candidate

    staged = stage_temporal_atomic_draft(
        runtime.cfg, runtime.memory, runtime.session,
        frozen_event["event_id"], fused_generate, operator_opt_in=True)
    if staged.get("status") != "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT":
        return _result("RUN61_TEMPORAL_DRAFT_RED",
                       callback_invoked=called[0],
                       lifecycle_reason=violation[0] if violation else None,
                       draft_status=staged.get("status"))
    checked = check_temporal_staged_draft(
        runtime.cfg, runtime.memory, runtime.session,
        frozen_event["event_id"], staged)
    if checked.get("status") != "TEMPORAL_ATOMIC_DRAFT_BOUND_SHADOW_NO_COMMIT":
        return _result("RUN61_POST_STAGE_BINDING_RED",
                       callback_invoked=called[0],
                       draft_message_id=staged["draft_message_id"],
                       draft_status=checked.get("status"),
                       shadow_draft_may_exist=True)
    ok, reason = unchanged()
    if not ok:
        return _result("RUN61_BODY_OFFER_LIFECYCLE_RED",
                       callback_invoked=called[0],
                       lifecycle_reason=reason,
                       shadow_draft_may_exist=True)

    c6 = preflight_budget_lexical_v2(
        runtime.cfg, runtime.memory, runtime.session,
        frozen_event["event_id"], staged, operator_opt_in=True)
    ok, reason = unchanged()
    if not ok:
        return _result("RUN61_BODY_OFFER_LIFECYCLE_RED",
                       callback_invoked=called[0],
                       lifecycle_reason=reason,
                       shadow_draft_may_exist=True)
    accepted = c6.get("status") == "NEEDS_REAL_TTY_APPROVAL"
    return _result(
        "RUN61_C6_V2_PREFLIGHT_ONLY_NEEDS_REAL_TTY"
        if accepted else "RUN61_C6_V2_GROUNDING_RED",
        callback_invoked=called[0],
        c6_status=c6.get("status"),
        c6_fingerprint_sha256=c6.get("fingerprint_sha256") if accepted else None,
        body_envelope_sha256=envelope["messages_sha256"],
        draft_message_id=staged["draft_message_id"],
        c5_action_id=staged["c5_action_id"],
        candidate_sha256=staged["candidate_sha256"],
        preflight_only=True)
