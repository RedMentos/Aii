"""Default-OFF cross-organ JEF/B1/B2/C3 -> C5/F3 DRAFT -> C6 SHADOW.

One trusted C3 callback is evaluated by Run84's post-generation guard.
Its verified typed action is reused in the existing JEF source-bound C5
transaction, WITHOUT another model invocation. The original C5 metadata
does not persist the dual-source/C3 digest; this bridge must not be used as
a durable C3 or body provenance credential, or as delivery authorization.
"""
from __future__ import annotations

from . import jef_b1b2_c3_dual_source_shadow as dual
from . import jef_b1b2_c3_postgen_shadow as postgen
from . import jef_c3_c5_c6_fallback_draft_candidate as draft

STATUS = "DUAL_SOURCE_C5_C6_DRAFT_PREFLIGHT_SHADOW"


def _result(status, **extra):
    return {
        "schema": "v13.jef_b1b2_c3_c5c6_draft_shadow.v1",
        "status": status,
        "delivery_authority": 0,
        "learning_authority": 0,
        "tool_dispatches": 0,
        "output_committed": False,
        "native_proof": False,
        "real_tty_approved": False,
        "dual_source_receipt_persisted": False,
        "c3_output_receipt_persisted": False,
        "c3_receiver_success": False,
        "whole_system_complete": False,
        "jepa_weight": 0,
        **extra,
    }


def _still_current(runtime, event, offers, ids, prompt_sha):
    """Read-only dual-source revalidation; never treat hypotheses as facts."""
    current = dual.build(runtime, event, offers, ids, operator_opt_in=True)
    return (current.get("status") == dual.STATUS
            and current.get("messages_sha256") == prompt_sha
            and current.get("human_source_lineage_verified") is True
            and current.get("formatter_only") is True)


def evaluate(runtime, event, offer_packet_ids, memory_ids, generator, *,
             operator_opt_in=False, callback_opt_in=False,
             approval_receipt=None):
    """Stage one C5 SHADOW DRAFT, then perform read-only C6 preflight.

    A successful return is not a C6 approval token. Callback side effects
    cannot be sandboxed or undone. A post-stage race may leave an orphan
    DRAFT, explicitly flagged for operator inspection.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED", callback_invoked=False)
    if not callable(generator):
        return _result("INVALID_GENERATOR", callback_invoked=False)
    if type(event) is not dict or type(memory_ids) not in (list, tuple):
        return _result("INVALID_INPUT", callback_invoked=False)
    try:
        event_id = event["event_id"]
        session = runtime.session
        store = runtime.store
        # Avoid a second model call when a DRAFT/action already exists.
        if draft._existing(store, session, event_id):
            return _result("EXISTING_DRAFT_OR_ACTION_RED",
                           callback_invoked=False)
    except Exception:
        return _result("PREFLIGHT_INTEGRITY_RED", callback_invoked=False)

    checked = postgen.evaluate(
        runtime, event, offer_packet_ids, memory_ids, generator,
        operator_opt_in=True, callback_opt_in=True)
    if checked.get("status") != postgen.STATUS:
        return _result("DUAL_SOURCE_C3_RED",
                       callback_invoked=checked.get("callback_invoked", False),
                       component_status=checked.get("status"))
    action = checked.get("parsed_action")
    prompt_sha = checked.get("messages_sha256")
    if (action not in ("A", "B", "NONE")
            or type(prompt_sha) is not str
            or type(checked.get("output_sha256")) is not str
            or checked.get("source_rechecked") is not True):
        return _result("POSTGEN_RECEIPT_RED", callback_invoked=True)
    try:
        if not _still_current(runtime, event, offer_packet_ids, memory_ids,
                              prompt_sha):
            return _result("SOURCE_CHANGED_BEFORE_DRAFT",
                           callback_invoked=True)
    except Exception:
        return _result("SOURCE_RECHECK_INTEGRITY_RED",
                       callback_invoked=True)

    # The existing stager independently rechecks JEF sources before, after,
    # and INSIDE its SQLite write transaction. This callback returns the
    # already verified action: never a second C3/model inference.
    staged = draft.stage(
        runtime.memory, session, event_id, event["source_ref"], memory_ids,
        lambda _messages: action, operator_opt_in=True, callback_opt_in=True)
    if staged.get("status") != draft.STAGED:
        return _result("C5_DRAFT_STAGE_RED", callback_invoked=True,
                       component_status=staged.get("status"),
                       shadow_draft_may_exist=staged.get(
                           "shadow_draft_may_exist", False))
    staged_action = staged.get("source_action")
    if (staged_action != action
            or staged.get("draft_origin") != "MODEL_EXACT_SHADOW"
            or staged.get("source_only_fallback") is not False):
        return _result("C5_DRAFT_BINDING_RED", callback_invoked=True,
                       shadow_draft_may_exist=True)
    try:
        if not _still_current(runtime, event, offer_packet_ids, memory_ids,
                              prompt_sha):
            return _result("SOURCE_CHANGED_AFTER_DRAFT",
                           callback_invoked=True,
                           shadow_draft_may_exist=True)
    except Exception:
        return _result("POSTSTAGE_SOURCE_INTEGRITY_RED",
                       callback_invoked=True, shadow_draft_may_exist=True)

    c6 = draft.preflight(
        runtime.memory, session, event_id, event["source_ref"], memory_ids,
        staged, operator_opt_in=True)
    if c6.get("status") != "NEEDS_REAL_TTY_APPROVAL":
        return _result("C6_DRAFT_PREFLIGHT_RED", callback_invoked=True,
                       component_status=c6.get("status"),
                       shadow_draft_may_exist=True)
    try:
        if not _still_current(runtime, event, offer_packet_ids, memory_ids,
                              prompt_sha):
            return _result("SOURCE_CHANGED_AFTER_C6_PREFLIGHT",
                           callback_invoked=True,
                           shadow_draft_may_exist=True)
    except Exception:
        return _result("POSTC6_SOURCE_INTEGRITY_RED",
                       callback_invoked=True, shadow_draft_may_exist=True)
    return _result(
        STATUS, callback_invoked=True, source_rechecked=True,
        formatter_match_shadow=True, c5_draft_staged=True,
        c6_preflight_only=True, shadow_draft_may_exist=True,
        c6_is_not_approval=True,
        typed_jef_action=action,
        dual_source_messages_sha256=prompt_sha,
        c3_output_sha256=checked["output_sha256"],
        jef_messages_sha256=checked["jef_messages_sha256"],
        b1b2_messages_sha256=checked["b1b2_messages_sha256"],
        draft_message_id=staged["draft_message_id"],
        c5_action_id=staged["c5_action_id"],
        c5_prompt_sha256=staged["prompt_sha256"])
