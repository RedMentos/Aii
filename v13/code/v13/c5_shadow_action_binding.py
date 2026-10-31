"""Strict read-only C5/F3 binding verifier for isolated SHADOW_DRAFT actions.

Derived from the repository's frozen Run49 _c5 verifier (same field/packet
checks, only action status is SHADOW_DRAFT rather than DISPATCHED).
Run49 remains unchanged. This is NOT a delivery or approval credential.
"""
from __future__ import annotations

import hashlib
from .agi.jef_c3_c5_c6_draft_shadow_run49 import _json
from .agi import jef_c3_final_agreement_shadow_run48 as agreement


def _c5_shadow(store, action_id, event_id, session_id):
    action = store.one("SELECT id,event_id,kind,status,corollary_id,expected "
                       "FROM actions WHERE id=?", (action_id,))
    event = store.one("SELECT id,session_id,generation_id FROM events WHERE id=?",
                      (event_id,))
    if (not action or not event or action["event_id"] != event_id
            or event["session_id"] != session_id or action["kind"] != "TEXT_REPORT"
            or action["status"] != "SHADOW_DRAFT"):
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
