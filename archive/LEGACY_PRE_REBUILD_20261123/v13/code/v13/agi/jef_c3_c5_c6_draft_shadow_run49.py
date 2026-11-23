"""Run49: C5 TEXT_REPORT -> C6 DRAFT source-bound preflight, SHADOW only.

The check holds the real Store's SQLite write transaction while validating
source/event/session, C5 intent/corollary and an uncommitted C6 draft. It never
commits a message, executes a tool, calls a model, or grants delivery authority.
A future visible output needs a separately approved atomic commit integration.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from . import jef_c3_final_agreement_shadow_run48 as agreement

REVISION = "jef-c3-c5-c6-draft-shadow-run49-v1"


def _result(reason, *, draft_digest=None, agreement_digest=None, c5_digest=None):
    return {
        "revision": REVISION,
        "status": "SHADOW_NO_AUTHORITY",
        "result": reason,
        "draft_sha256": draft_digest,
        "matched_candidate_sha256": agreement_digest,
        "c5_binding_sha256": c5_digest,
        "delivery_authority": 0,
        "live_enabled": False,
        "user_approved": False,
        "model_called": False,
        "native_calls": 0,
        "store_writes": 0,
        "tool_dispatches": 0,
        "weight_updates": False,
        "age0": "RECORD_ONLY",
        "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0,
        "world_jepa_authority": "SHADOW",
        "redmi_measured": False,
        "whole_system_complete": False,
    }


def _json(raw):
    if type(raw) is not str or len(raw.encode("utf-8")) > 4096:
        raise ValueError("INVALID_JSON_BYTES")
    return json.loads(raw, object_pairs_hook=agreement._unique,
                      parse_constant=agreement._nonfinite)


def _draft(store, mid, event_id, session_id, c3_raw):
    row = store.one("SELECT id,session_id,event_id,role,text,status,metadata "
                    "FROM messages WHERE id=?", (mid,))
    if (not row or row["id"] != mid or row["session_id"] != session_id
            or row["event_id"] != event_id or row["role"] != "assistant"
            or row["status"] != "DRAFT" or row["text"] != c3_raw):
        return False
    meta = _json(row["metadata"])
    return (type(meta) is dict
            and not any(k in meta for k in ("delivery_authority", "output_authority",
                                            "user_approved", "tool_result")))


def _c5(store, action_id, event_id, session_id):
    action = store.one("SELECT id,event_id,kind,status,corollary_id,expected "
                       "FROM actions WHERE id=?", (action_id,))
    event = store.one("SELECT id,session_id,generation_id FROM events WHERE id=?",
                      (event_id,))
    if (not action or not event or action["event_id"] != event_id
            or event["session_id"] != session_id or action["kind"] != "TEXT_REPORT"
            or action["status"] != "DISPATCHED"):
        return None
    expected = _json(action["expected"])
    if expected != {"stream_owner": "C5_REPORT_BROKER", "type": "TEXT_REPORT"}:
        return None
    copy_row = store.one("SELECT id,kind,event_id,generation_id,payload "
                         "FROM packets WHERE id=?", (action["corollary_id"],))
    if (not copy_row or copy_row["kind"] != "CorollaryCopy"
            or copy_row["event_id"] != event_id
            or copy_row["generation_id"] != event["generation_id"]):
        return None
    copy = _json(copy_row["payload"])
    if (type(copy) is not dict or copy.get("packet_id") != copy_row["id"]
            or copy.get("event_id") != event_id
            or copy.get("brain_generation_id") != event["generation_id"]
            or copy.get("producer_component") != "F3_SELF"
            or copy.get("action_id") != action_id
            or copy.get("self_caused") is not True
            or copy.get("expected") != expected):
        return None
    intents = store.rows("SELECT id,kind,event_id,generation_id,payload "
                         "FROM packets WHERE kind='ActionIntent' AND event_id=?", (event_id,))
    matching = []
    for row in intents:
        intent = _json(row["payload"])
        if type(intent) is dict and intent.get("action_id") == action_id:
            matching.append((row, intent))
    if len(matching) != 1:
        return None
    row, intent = matching[0]
    if (row["event_id"] != event_id or row["generation_id"] != event["generation_id"]
            or intent.get("packet_id") != row["id"]
            or intent.get("event_id") != event_id
            or intent.get("brain_generation_id") != event["generation_id"]
            or intent.get("producer_component") != "C5_REPORT_BROKER"
            or intent.get("action_type") != "TEXT_REPORT"
            or intent.get("permission") != "local_text_only"):
        return None
    return hashlib.sha256(agreement._canonical({
        "action": action_id, "intent": row["id"], "copy": copy_row["id"],
        "event": event_id, "generation": event["generation_id"]})).hexdigest()


def check_draft(store, prior_ref, current_ref, current_event_id, session_id,
                c3_raw, draft_message_id, c5_action_id):
    """Read-only atomic SQLite preflight; a positive result never authorizes C6.

    This function cannot prevent source deletion *after* the transaction exits.
    It must not be used as a replacement for a future transactional C6 commit.
    """
    if (type(draft_message_id) is not int or draft_message_id <= 0
            or type(c5_action_id) is not str or not c5_action_id
            or type(current_event_id) is not str or not current_event_id
            or type(session_id) is not str or not session_id
            or type(c3_raw) is not str):
        return _result("INPUT_BINDING_RED")
    try:
        with store.tx():  # BEGIN IMMEDIATE serializes SQLite source revocations.
            if not _draft(store, draft_message_id, current_event_id, session_id, c3_raw):
                return _result("C6_DRAFT_RED")
            c5_digest = _c5(store, c5_action_id, current_event_id, session_id)
            if c5_digest is None:
                return _result("C5_INTENT_RED")
            matched = agreement.check(store, prior_ref, current_ref,
                                      current_event_id, session_id, c3_raw)
            if matched["result"] != "MATCHED_NO_AUTHORITY":
                return _result("FINAL_AGREEMENT_RED")
            if (not _draft(store, draft_message_id, current_event_id, session_id, c3_raw)
                    or _c5(store, c5_action_id, current_event_id, session_id) != c5_digest):
                return _result("BINDING_CHANGED_BEFORE_EXIT")
            return _result("DRAFT_BOUND_SHADOW_NO_COMMIT",
                           draft_digest=hashlib.sha256(c3_raw.encode("utf-8")).hexdigest(),
                           agreement_digest=matched["matched_candidate_sha256"],
                           c5_digest=c5_digest)
    except (ValueError, TypeError, KeyError, IndexError, OSError, UnicodeError,
            AttributeError, OverflowError, sqlite3.Error, RuntimeError):
        return _result("STORE_OR_BINDING_RED")
