"""Run13F explicit local Age0 TTY JEF ContextPlan source-link diagnostic.

Never called from the live answer route. No model, tool, learning, memory
admission or automatic C3 output. User must supply three persisted IDs.
"""
from __future__ import annotations

import re

from .common import dumps
from .agi.context_source_link_budget_run13e import propose_pointer

PACKET = re.compile(r"pkt_[a-f0-9]{28,32}\Z", re.ASCII)
EVENT = re.compile(r"evt_[a-f0-9]{28,32}\Z", re.ASCII)


def operator_command(r, args):
    if (len(args) != 3 or PACKET.fullmatch(args[0]) is None
            or any(EVENT.fullmatch(event) is None for event in args[1:])):
        raise ValueError(
            ":jeflink <ContextPlan-Packet-ID> <QueryEvent-ID> <SourceEvent-ID> (SHADOW only)")
    cfg = r.cfg
    if (cfg.get("system_stage") != 0
            or cfg.get("learning_mode") != "RECORD_ONLY"
            or cfg.get("latents_enabled") is not False
            or cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE0_RECORD_ONLY_REQUIRED")
    r.require_idle()
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
