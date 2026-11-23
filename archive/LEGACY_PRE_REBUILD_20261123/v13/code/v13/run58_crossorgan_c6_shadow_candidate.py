"""Default-OFF B1/B2 -> C3 -> temporal F1/F5 -> C5/C6 DRAFT SHADOW.

A caller-supplied generator is a software test seam, not native proof. No
Runtime installation, FINAL, output commit, TTY approval or tool dispatch.
"""
from __future__ import annotations

from .b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from .f1f5_event_finalizer_candidate import _event_snapshot
from .f1f5_temporal_atomic_draft_candidate import (
    stage_temporal_atomic_draft, check_temporal_staged_draft)
from .c6_positive_assertion_candidate import preflight_positive_budget_assertion
from .runtime_c3_atomic_draft_candidate import _idle


def _result(status, **extra):
    return {"schema": "v13.run58_crossorgan_c6_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def stage_crossorgan_c6_shadow(runtime, event, offer_packet_ids, generate, *,
                               operator_opt_in=False, callback_opt_in=False,
                               approval_receipt=None):
    """Stage one temporal DRAFT using source-verified body and F1/F5 inputs.

    The two input message groups remain separate: the current USER source
    and body quote evidence, and independently admitted F1/F5 correction.
    Neither body hypotheses nor a C6 fingerprint is an approval credential.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED", callback_invoked=False)
    if not callable(generate) or type(event) is not dict:
        return _result("INVALID_INPUT", callback_invoked=False)
    if not _idle(runtime):
        return _result("RUNTIME_NOT_IDLE", callback_invoked=False)
    envelope = build_c3_source_envelope(
        runtime, event, offer_packet_ids, operator_opt_in=True)
    if envelope["status"] != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
        return _result("BODY_SOURCE_ENVELOPE_RED",
                       envelope_status=envelope["status"],
                       callback_invoked=False)
    try:
        initial = _event_snapshot(
            runtime.memory, event["event_id"], runtime.session)
        if initial["ref"] != envelope["source_ref"]:
            return _result("SOURCE_CHANGED_BEFORE_DRAFT", callback_invoked=False)
    except Exception:
        return _result("EVENT_OR_SOURCE_RED", callback_invoked=False)

    def fused_generate(verified_f1f5_messages):
        if _event_snapshot(runtime.memory, event["event_id"],
                           runtime.session) != initial:
            raise RuntimeError("RUN58_SOURCE_CHANGED_BEFORE_GENERATION")
        if (type(verified_f1f5_messages) is not list
                or len(verified_f1f5_messages) != 2
                or [x.get("role") for x in verified_f1f5_messages]
                != ["system", "user"]):
            raise RuntimeError("RUN58_F1F5_RENDER_RED")
        return generate(envelope["messages"], verified_f1f5_messages)

    staged = stage_temporal_atomic_draft(
        runtime.cfg, runtime.memory, runtime.session,
        event["event_id"], fused_generate, operator_opt_in=True)
    if staged.get("status") != "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT":
        return _result("TEMPORAL_DRAFT_RED",
                       draft_status=staged.get("status"),
                       callback_invoked=staged.get("callback_invoked", False))
    checked = check_temporal_staged_draft(
        runtime.cfg, runtime.memory, runtime.session,
        event["event_id"], staged)
    if checked["status"] != "TEMPORAL_ATOMIC_DRAFT_BOUND_SHADOW_NO_COMMIT":
        return _result("POST_STAGE_BINDING_RED",
                       draft_message_id=staged["draft_message_id"],
                       draft_status=checked["status"],
                       callback_invoked=True)
    c6 = preflight_positive_budget_assertion(
        runtime.cfg, runtime.memory, runtime.session,
        event["event_id"], staged, operator_opt_in=True)
    status = ("CROSSORGAN_C6_PREFLIGHT_ONLY_NEEDS_REAL_TTY"
              if c6["status"] == "NEEDS_REAL_TTY_APPROVAL"
              else "CROSSORGAN_C6_GROUNDING_RED")
    return _result(status,
                   callback_invoked=True,
                   body_envelope_sha256=envelope["messages_sha256"],
                   c6_status=c6["status"],
                   c6_fingerprint_sha256=c6.get("fingerprint_sha256"),
                   draft_message_id=staged["draft_message_id"],
                   c5_action_id=staged["c5_action_id"],
                   candidate_sha256=staged["candidate_sha256"],
                   preflight_only=True)
