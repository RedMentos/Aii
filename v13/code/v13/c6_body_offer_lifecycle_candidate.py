"""Default-OFF B1/B2 OfferPacket lifecycle check around Run58 C6 SHADOW.

Run58's F1/F5/C5/C6 source rechecks do not revalidate the B1/B2 offer
envelope after the generator callback. This independent, non-authorizing
wrapper detects observable drift in both persisted offers, retained states,
model revisions, current USER source and the exact C3 input envelope.

NOT an atomic output commit, rollback, native proof, or Runtime integration.
"""
from __future__ import annotations

from .b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from .common import dumps
from .run58_crossorgan_c6_shadow_candidate import stage_crossorgan_c6_shadow


def _result(status, **extra):
    return {
        "schema": "v13.c6_body_offer_lifecycle_shadow.v1",
        "status": status,
        "delivery_authority": 0,
        "output_committed": False,
        "tool_dispatches": 0,
        "learning_authority": 0,
        "native_proof": False,
        **extra,
    }


def stage_offer_lifecycle_c6_shadow(runtime, event, offer_packet_ids, generate, *,
                                    operator_opt_in=False, callback_opt_in=False,
                                    approval_receipt=None):
    """Fail closed on changed B1/B2 evidence; never grant output authority.

    Only the source-exact C3 envelope can be used. Rebuilding it detects
    tampered OfferPackets, retained-state drift, revision changes, and newer
    authoritative USER events. The final read is NOT a substitute for a
    future writer's in-transaction source/TTY checks.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED", callback_invoked=False)
    if not callable(generate) or type(event) is not dict or type(offer_packet_ids) is not dict:
        return _result("INVALID_INPUT", callback_invoked=False)

    frozen_event = dict(event)
    frozen_ids = dict(offer_packet_ids)
    # A prior DRAFT/FINAL or TEXT_REPORT is not an invitation to call C3 again.
    # This is a cost/authority preflight, not a cross-process atomic reservation.
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
    first = build_c3_source_envelope(
        runtime, frozen_event, frozen_ids, operator_opt_in=True)
    if first.get("status") != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
        return _result("BODY_OFFER_BEFORE_CALLBACK_RED", callback_invoked=False,
                       envelope_status=first.get("status"))

    def unchanged():
        current = build_c3_source_envelope(
            runtime, frozen_event, frozen_ids, operator_opt_in=True)
        if current.get("status") != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
            return False, current.get("status")
        if (current.get("messages_sha256") != first["messages_sha256"]
                or current.get("source_ref") != first["source_ref"]
                or current.get("offer_packet_ids") != first["offer_packet_ids"]
                or dumps(current["messages"]) != dumps(first["messages"])):
            return False, "ENVELOPE_FINGERPRINT_CHANGED"
        return True, "UNCHANGED"

    violation = []
    callback_called = [False]

    def guarded_generate(body_messages, f1f5_messages):
        ok, reason = unchanged()
        if not ok or dumps(body_messages) != dumps(first["messages"]):
            violation.append(reason if not ok else "CALLBACK_BODY_ENVELOPE_MISMATCH")
            raise RuntimeError("BODY_OFFER_LIFECYCLE_RED_BEFORE_CALLBACK")
        callback_called[0] = True
        candidate = generate(body_messages, f1f5_messages)
        ok, reason = unchanged()
        if not ok:
            violation.append(reason)
            raise RuntimeError("BODY_OFFER_LIFECYCLE_RED_AFTER_CALLBACK")
        return candidate

    staged = stage_crossorgan_c6_shadow(
        runtime, frozen_event, frozen_ids, guarded_generate,
        operator_opt_in=True, callback_opt_in=True)
    ok, reason = unchanged()
    if violation or not ok:
        return _result(
            "BODY_OFFER_LIFECYCLE_RED",
            callback_invoked=callback_called[0],
            evidence_status=violation[0] if violation else reason,
            underlying_status=staged.get("status"),
            shadow_draft_may_exist="draft_message_id" in staged,
            preflight_only=True)
    if staged.get("status") == "CROSSORGAN_C6_PREFLIGHT_ONLY_NEEDS_REAL_TTY":
        return _result(
            "LIFECYCLE_C6_PREFLIGHT_ONLY_NEEDS_REAL_TTY",
            callback_invoked=callback_called[0],
            body_offer_lifecycle_rechecked=True,
            body_envelope_sha256=first["messages_sha256"],
            c6_status=staged.get("c6_status"),
            c6_fingerprint_sha256=staged.get("c6_fingerprint_sha256"),
            draft_message_id=staged.get("draft_message_id"),
            candidate_sha256=staged.get("candidate_sha256"),
            preflight_only=True)
    return _result(
        "UNDERLYING_C6_OR_DRAFT_RED",
        callback_invoked=callback_called[0],
        body_offer_lifecycle_rechecked=True,
        underlying_status=staged.get("status"),
        c6_status=staged.get("c6_status"),
        preflight_only=True)
