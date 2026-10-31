"""Default-OFF read-only C6 integrity replay with Store recovery quarantine.

Rechecks persisted single-call callback JSON and SHA, current human F1/F5,
dual B1/B2 offers, C5/F3 SHADOW_DRAFT and exactly one assistant DRAFT.
Store recovery INTERRUPTED is audited as QUARANTINED, never resumed as DRAFT.
Does NOT re-invoke a model, authorize output/TTY, or certify native evidence.
"""
from __future__ import annotations

import hashlib
import json
import re

from . import jef_b1b2_c3_c5c6_draft_shadow as bridge
from . import jef_b1b2_c3_postgen_shadow as postgen
from .c5_shadow_action_binding import _c5_shadow
from .jef_c3_c5_c6_fallback_draft_candidate import _draft
from .jef_c3_schema_draft_candidate import (
    decode_action, _unique, _reject_constant,
)

STATUS = "RESTART_C5_C6_DRAFT_INTEGRITY_SHADOW"
QUARANTINED = "RESTART_SHADOW_DRAFT_QUARANTINED"
META_KEYS = frozenset({
    "shadow", "origin", "source_action", "source_ref_sha256",
    "dual_source_messages_sha256", "jef_messages_sha256",
    "b1b2_messages_sha256", "callback_output_sha256",
    "callback_output_json", "candidate_sha256",
    "model_formatter_status", "body_hypotheses_are_facts",
})
HEX = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)


def _result(status, **extra):
    return {
        "schema": "v13.jef_b1b2_c3_c5c6_restart_shadow.v1",
        "status": status,
        "delivery_authority": 0,
        "learning_authority": 0,
        "tool_dispatches": 0,
        "output_committed": False,
        "callback_invoked": False,
        "native_proof": False,
        "c3_receiver_success": False,
        "real_tty_approved": False,
        "whole_system_complete": False,
        "jepa_weight": 0,
        **extra,
    }


def preflight(runtime, event, offer_packet_ids, memory_ids,
              draft_message_id, c5_action_id, *,
              operator_opt_in=False, approval_receipt=None):
    """No model call and no output commit; valid only for exact live Store."""
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if (type(event) is not dict or type(memory_ids) not in (tuple, list)
            or type(draft_message_id) is not int or draft_message_id <= 0
            or type(c5_action_id) is not str or not c5_action_id):
        return _result("INVALID_REFERENCE")
    try:
        store = runtime.store
        session = runtime.session
        event_id = event["event_id"]
        with store.tx():
            row = store.one(
                "SELECT session_id,event_id,role,text,status,metadata "
                "FROM messages WHERE id=?",
                (draft_message_id,))
            if row is None:
                return _result("DRAFT_MISSING")
            raw_meta = row["metadata"]
            if (type(raw_meta) is not str
                    or len(raw_meta.encode("utf-8")) > 8192):
                return _result("DRAFT_METADATA_SIZE_RED")
            meta = json.loads(
                raw_meta, object_pairs_hook=_unique,
                parse_constant=_reject_constant)
            if (type(meta) is not dict or set(meta) != META_KEYS
                    or meta["shadow"] is not True
                    or meta["origin"] != "DUAL_SOURCE_SCHEMA_EXACT_SHADOW"
                    or meta["body_hypotheses_are_facts"] is not False
                    or meta["model_formatter_status"] != postgen.STATUS
                    or meta["source_action"] not in ("A", "B", "NONE")
                    or type(meta["source_ref_sha256"]) is not list
                    or len(meta["source_ref_sha256"]) != 2
                    or any(type(h) is not str or HEX.fullmatch(h) is None
                           for h in meta["source_ref_sha256"])
                    or any(type(meta[key]) is not str
                           or HEX.fullmatch(meta[key]) is None
                           for key in (
                               "dual_source_messages_sha256",
                               "jef_messages_sha256",
                               "b1b2_messages_sha256",
                               "callback_output_sha256",
                               "candidate_sha256"))):
                return _result("DRAFT_METADATA_SHAPE_RED")
            raw = meta["callback_output_json"]
            if (decode_action(raw) != meta["source_action"]
                    or hashlib.sha256(raw.encode("utf-8")).hexdigest()
                    != meta["callback_output_sha256"]
                    or hashlib.sha256(
                        meta["source_action"].encode("utf-8")).hexdigest()
                    != meta["candidate_sha256"]):
                return _result("CALLBACK_OUTPUT_REPLAY_RED")
            if (not bridge._human(runtime, event, memory_ids,
                                  meta["source_action"],
                                  meta["source_ref_sha256"])
                    or not bridge._still_current(
                        runtime, event, offer_packet_ids, memory_ids, meta)):
                return _result("SOURCE_CHANGED_AFTER_RESTART")
            if (store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE event_id=? "
                    "AND session_id=? AND role='assistant'",
                    (event_id, session))["n"] != 1
                    or store.one(
                    "SELECT COUNT(*) AS n FROM actions WHERE event_id=? "
                    "AND kind='TEXT_REPORT'", (event_id,))["n"] != 1):
                return _result("DUPLICATE_DRAFT_OR_ACTION_RED")
            # Store recovery intentionally changes all DRAFT messages to
            # INTERRUPTED on reopen. Never resurrect that quarantined state.
            if row["status"] == "DRAFT":
                draft_ok = bool(_draft(
                    store, draft_message_id, event_id, session,
                    meta["source_action"]))
            elif row["status"] == "INTERRUPTED":
                draft_ok = (
                    row["session_id"] == session
                    and row["event_id"] == event_id
                    and row["role"] == "assistant"
                    and row["text"] == meta["source_action"])
            else:
                draft_ok = False
            c5_ok = _c5_shadow(store, c5_action_id,
                               event_id, session) is not None
            if not draft_ok or not c5_ok:
                action_row = store.one(
                    "SELECT status FROM actions WHERE id=?", (c5_action_id,))
                return _result(
                    "C5_F3_OR_DRAFT_BINDING_RED",
                    draft_binding_ok=draft_ok, c5_binding_ok=c5_ok,
                    action_status=(
                        action_row["status"] if action_row else "MISSING"))
        if row["status"] == "INTERRUPTED":
            return _result(
                QUARANTINED, source_rechecked=True,
                c6_preflight_only=False, resumable=False,
                recovery_interrupted=True, c6_is_not_approval=True,
                callback_json_digest_replayed=True,
                draft_message_id=draft_message_id,
                c5_action_id=c5_action_id)
        return _result(
            STATUS, source_rechecked=True, c6_preflight_only=True,
            resumable=False, c6_is_not_approval=True,
            callback_json_digest_replayed=True,
            dual_source_messages_sha256=meta[
                "dual_source_messages_sha256"],
            callback_output_sha256=meta["callback_output_sha256"],
            draft_message_id=draft_message_id,
            c5_action_id=c5_action_id)
    except Exception:
        return _result("RESTART_STORE_OR_BINDING_RED")
