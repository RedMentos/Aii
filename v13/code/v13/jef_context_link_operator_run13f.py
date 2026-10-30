"""Run13F/G explicit local Age0 TTY JEF ContextPlan source-link diagnostic.

Never called from the live answer route. No model, tool, learning, memory
admission or automatic C3 output. The 'last' form is bounded and unique-only.
"""
from __future__ import annotations

import json
import re

from .common import dumps
from .agi.context_source_link_budget_run13e import propose_pointer

PACKET = re.compile(r"pkt_[a-f0-9]{28,32}\Z", re.ASCII)
EVENT = re.compile(r"evt_[a-f0-9]{28,32}\Z", re.ASCII)
MAX_POINTERS = 32


def _deny(reason):
    return {
        "status": "SHADOW_NO_AUTHORITY", "reason": reason,
        "answer": None, "candidate": None, "authority": 0,
        "delivery_authority": 0, "source_link_authority": 0,
        "model_called": False, "native_calls": 0,
        "weight_updates": False, "learning_mode": "RECORD_ONLY",
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


def _latest_plan(store, session):
    return store.one(
        "SELECT p.id,p.event_id,p.payload FROM packets p "
        "JOIN events e ON e.id=p.event_id "
        "WHERE p.kind='ContextPlan' AND e.session_id=? "
        "ORDER BY p.created DESC,p.rowid DESC LIMIT 1",
        (session,))


def _last(r):
    try:
        row = _latest_plan(r.store, r.session)
        if row is None:
            return _deny("NO_CURRENT_SESSION_CONTEXT_PLAN")
        payload = row["payload"]
        plan = json.loads(payload)
        if (type(plan) is not dict or plan.get("packet_id") != row["id"]
                or plan.get("event_id") != row["event_id"]
                or plan.get("role") != "C3_LANGUAGE"
                or plan.get("mode") != "SHADOW"
                or plan.get("applied") is not False
                or type(plan.get("items")) is not list):
            return _deny("CONTEXT_PLAN_NOT_SHADOW_BOUND")
        pointers = [
            item.get("item_id") for item in plan["items"]
            if type(item) is dict
            and item.get("layer") == "SOURCE_LINKS"
            and item.get("form") == "POINTER"
        ]
        if (not pointers or len(pointers) > MAX_POINTERS
                or any(type(p) is not str or EVENT.fullmatch(p) is None
                       for p in pointers)
                or len(set(pointers)) != len(pointers)):
            return _deny("SOURCE_LINK_SET_EMPTY_AMBIGUOUS_OR_OVERSIZE")
        matches = []
        for source_event_id in pointers:
            result = propose_pointer(
                r.store, row["id"], row["event_id"], source_event_id)
            if result.get("answer") is not None:
                matches.append(result)
                if len(matches) > 1:
                    return _deny("MULTIPLE_VERIFIED_SOURCE_LINKS")
        fresh = _latest_plan(r.store, r.session)
        if (fresh is None or fresh["id"] != row["id"]
                or fresh["event_id"] != row["event_id"]
                or fresh["payload"] != payload):
            return _deny("LATEST_CONTEXT_PLAN_CHANGED")
        if len(matches) != 1:
            return _deny("NO_UNIQUE_VERIFIED_SOURCE_LINK")
        return matches[0]
    except (ValueError, KeyError, TypeError, OSError, AttributeError,
            UnicodeError, OverflowError):
        return _deny("CONTEXT_LINK_LAST_INTEGRITY_RED")


def operator_command(r, args):
    last = args == ["last"]
    if not last and (
            len(args) != 3 or PACKET.fullmatch(args[0]) is None
            or any(EVENT.fullmatch(event) is None for event in args[1:])):
        raise ValueError(
            ":jeflink <ContextPlan-Packet-ID> <QueryEvent-ID> <SourceEvent-ID> | :jeflink last (SHADOW only)")
    cfg = r.cfg
    if (cfg.get("system_stage") != 0
            or cfg.get("learning_mode") != "RECORD_ONLY"
            or cfg.get("latents_enabled") is not False
            or cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE0_RECORD_ONLY_REQUIRED")
    r.require_idle()
    if last:
        result = _last(r)
    else:
        plan_id, query_event_id, source_event_id = args
        row = r.store.one(
            "SELECT session_id FROM events WHERE id=?", (query_event_id,))
        if row is None or row["session_id"] != r.session:
            raise ValueError("CURRENT_SESSION_QUERY_EVENT_REQUIRED")
        result = propose_pointer(
            r.store, plan_id, query_event_id, source_event_id)
    return dumps({
        **result, "operator_diagnostic": True,
        "not_chat_turn": True, "no_autonomous_egress": True,
        "age0_record_only": True, "model_called": False,
        "native_calls": 0, "weight_updates": False,
        "jepa_weight": 0, "whole_system_complete": False,
    })
