"""Run13E: persisted Context OS SOURCE_LINKS -> JEF exact source SHADOW.

Only an explicit operator call with a real ContextPlan packet and event IDs.
Not wired into Runtime, memory recall, C3 output, tools or active authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3

from v13.agi.budget_answer_shadow_run13b import propose_text

REVISION = "run13e-context-source-link-budget-shadow-v1"
HEX = re.compile(r"[0-9a-f]{64}", re.ASCII)


def _deny(reason):
    return {
        "revision": REVISION, "status": "SHADOW_NO_AUTHORITY",
        "reason": reason, "answer": None, "candidate": None,
        "authority": 0, "delivery_authority": 0,
        "model_called": False, "native_calls": 0,
        "weight_updates": False, "learning_mode": "RECORD_ONLY",
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


def _event(store, event_id):
    row = store.one(
        "SELECT e.id AS event_id,e.session_id AS session,e.created AS created,"
        "s.id AS source_id,s.hash AS sha,s.chars AS chars,"
        "s.deleted AS deleted,s.kind AS kind "
        "FROM events e JOIN sources s ON s.id=e.source_id WHERE e.id=?",
        (event_id,))
    if (row is None or row["deleted"] != 0 or row["kind"] != "USER"
            or type(row["source_id"]) is not str
            or type(row["sha"]) is not str or HEX.fullmatch(row["sha"]) is None
            or type(row["chars"]) is not int
            or not 0 < row["chars"] <= 1024):
        raise ValueError("EVENT_SOURCE_INVALID")
    ref = {
        "source_id": row["source_id"], "sha256": row["sha"],
        "char_start": 0, "char_end": row["chars"], "modality": "text",
    }
    return ref, row["session"], row["created"]


def _witness(store, plan_id, query_event_id, source_event_id):
    for value in (plan_id, query_event_id, source_event_id):
        if type(value) is not str or not 1 <= len(value) <= 128:
            raise ValueError("EVENT_ID_SHAPE_RED")
    if query_event_id == source_event_id:
        raise ValueError("EVENT_ALIAS_RED")
    packet = store.one(
        "SELECT event_id,payload FROM packets WHERE id=? AND kind='ContextPlan'",
        (plan_id,))
    if packet is None or packet["event_id"] != query_event_id:
        raise ValueError("CONTEXT_PLAN_MISSING_OR_FOREIGN")
    plan = json.loads(packet["payload"])
    if (type(plan) is not dict
            or plan.get("packet_id") != plan_id
            or plan.get("event_id") != query_event_id
            or plan.get("role") != "C3_LANGUAGE"
            or plan.get("mode") != "SHADOW"
            or plan.get("applied") is not False
            or type(plan.get("items")) is not list):
        raise ValueError("CONTEXT_PLAN_NOT_SHADOW_BOUND")
    pointers = [
        item for item in plan["items"]
        if type(item) is dict and item.get("item_id") == source_event_id
        and item.get("layer") == "SOURCE_LINKS"
        and item.get("form") == "POINTER"
    ]
    if (len(pointers) != 1
            or sum(type(item) is dict and
                   item.get("item_id") == source_event_id
                   for item in plan["items"]) != 1):
        raise ValueError("SOURCE_LINK_NOT_UNIQUE")
    qref, qsession, qcreated = _event(store, query_event_id)
    sref, ssession, screated = _event(store, source_event_id)
    if (type(qsession) is not str or not qsession
            or qsession != ssession or screated > qcreated):
        raise ValueError("EVENT_SESSION_OR_ORDER_RED")
    return {
        "query_ref": qref, "source_ref": sref, "session": qsession,
        "plan_sha256": hashlib.sha256(
            packet["payload"].encode("utf-8")).hexdigest(),
    }


def propose_pointer(store, plan_id, query_event_id, source_event_id):
    """Revalidate persisted plan and both event/source rows before returning."""
    try:
        first = _witness(store, plan_id, query_event_id, source_event_id)
        answer = propose_text(store, first["query_ref"], first["source_ref"])
        if answer.get("answer") is None:
            return _deny(answer.get("reason", "SOURCE_ANSWER_ABSTAIN"))
        if _witness(store, plan_id, query_event_id, source_event_id) != first:
            return _deny("SOURCE_LINK_CHANGED_BEFORE_RENDER")
        return {
            **answer, "revision": REVISION,
            "context_plan_packet_id": plan_id,
            "query_event_id": query_event_id,
            "source_event_id": source_event_id,
            "source_link_used": True,
            "source_link_authority": 0,
            "delivery_authority": 0,
        }
    except (ValueError, KeyError, TypeError, OSError, AttributeError,
            UnicodeError, OverflowError, json.JSONDecodeError, sqlite3.Error):
        return _deny("CONTEXT_SOURCE_LINK_INTEGRITY_RED")
