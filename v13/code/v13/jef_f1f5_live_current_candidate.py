"""Default-OFF JEF live-current F1/F5 two-source decision SHADOW.

Historical :jefsource replay is intentionally unchanged. This opt-in read-only
candidate binds the latest authoritative USER event and original two HumanDecision
memories in one Store transaction. No model/output/action/learning authority.
"""
from __future__ import annotations

import json

from . import jef_f1f5_source_admission as admission


def _deny(reason):
    return {**admission._deny(reason),
            "live_current_status": reason,
            "live_current_verified": False,
            "delivery_authority": 0,
            "output_committed": False,
            "tool_dispatches": 0,
            "learning_authority": 0,
            "native_proof": False}


def _latest_authoritative_user(store, session):
    for row in store.rows(
            "SELECT id,packet FROM events WHERE session_id=? ORDER BY rowid DESC",
            (session,)):
        envelope = json.loads(row["packet"])
        if (envelope.get("authority") == "AUTHORITATIVE"
                and envelope.get("kind") == "USER_TEXT"):
            return row["id"]
    return None


def decide_current_turn(memory, session, event_id, current_ref, memory_ids, *,
                        operator_opt_in=False, approval_receipt=None):
    """One read-only transaction; never a token for later C3/egress delivery."""
    if operator_opt_in is not True:
        return _deny("OFF")
    if approval_receipt is not None:
        return _deny("REAL_TTY_APPROVAL_UNSUPPORTED")
    if (type(session) is not str or type(event_id) is not str
            or type(current_ref) is not dict
            or type(memory_ids) not in (list, tuple)):
        return _deny("INVALID_INPUT")
    try:
        store = memory.s
        with store.tx():
            if _latest_authoritative_user(store, session) != event_id:
                return _deny("STALE_USER_EVENT_RED")
            row = store.one(
                "SELECT packet FROM events WHERE id=? AND session_id=?",
                (event_id, session))
            if row is None:
                return _deny("CURRENT_EVENT_RED")
            envelope = json.loads(row["packet"])
            if (envelope.get("authority") != "AUTHORITATIVE"
                    or envelope.get("kind") != "USER_TEXT"
                    or envelope.get("event_id") != event_id
                    or envelope.get("source_ref") != current_ref):
                return _deny("CURRENT_SOURCE_REF_RED")
            decision = admission.decide(
                memory, session, event_id, current_ref, memory_ids)
            if (decision.get("admission_status")
                    != "F1F5_SESSION_VERIFIED_SHADOW"
                    or decision.get("human_source_lineage_verified") is not True
                    or decision.get("suggested_action") not in ("A", "B", "NONE")
                    or decision.get("authority") != 0
                    or decision.get("model_called") is not False
                    or decision.get("native_calls") != 0):
                return {**decision,
                        "live_current_status": "ADMISSION_RED",
                        "live_current_verified": False,
                        "delivery_authority": 0,
                        "output_committed": False,
                        "tool_dispatches": 0,
                        "learning_authority": 0,
                        "native_proof": False}
            if (_latest_authoritative_user(store, session) != event_id
                    or store.one(
                        "SELECT packet FROM events WHERE id=? AND session_id=?",
                        (event_id, session))["packet"] != row["packet"]):
                return _deny("CURRENT_CHANGED_DURING_READ")
            return {**decision,
                    "live_current_status": "JEF_LIVE_CURRENT_VERIFIED_SHADOW",
                    "live_current_verified": True,
                    "delivery_authority": 0,
                    "output_committed": False,
                    "tool_dispatches": 0,
                    "learning_authority": 0,
                    "native_proof": False}
    except Exception:
        return _deny("JEF_LIVE_CURRENT_INTEGRITY_RED")
