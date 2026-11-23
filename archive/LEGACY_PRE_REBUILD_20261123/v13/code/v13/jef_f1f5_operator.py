"""Explicit local operator read-only JEF F1/F5 SHADOW diagnostic; no live answer."""
import json
import re

from .common import dumps
from . import jef_f1f5_source_admission as admission

EVENT = re.compile(r"evt_[a-f0-9]{28,32}\Z", re.ASCII)
MEMORY = re.compile(r"mem_[a-f0-9]{28,32}\Z", re.ASCII)


def operator_command(r, args):
    if (len(args) != 3 or EVENT.fullmatch(args[0]) is None
            or any(MEMORY.fullmatch(mid) is None for mid in args[1:])):
        raise ValueError(":jefsource <Event-ID> <PolicyMemory-ID> <SheetMemory-ID> (SHADOW only)")
    cfg = r.cfg
    if (cfg.get("system_stage") != 0
            or cfg.get("learning_mode") != "RECORD_ONLY"
            or cfg.get("latents_enabled") is not False
            or cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE0_RECORD_ONLY_REQUIRED")
    r.require_idle()
    event_id, policy_id, sheet_id = args
    row = r.store.one(
        "SELECT packet FROM events WHERE id=? AND session_id=?",
        (event_id, r.session))
    if row is None:
        raise ValueError("CURRENT_SESSION_EVENT_REQUIRED")
    try:
        envelope = json.loads(row["packet"])
        current_ref = envelope["source_ref"]
    except (ValueError, TypeError, KeyError):
        raise ValueError("AUTHORITATIVE_CURRENT_EVENT_REF_REQUIRED") from None
    result = admission.decide(r.memory, r.session, event_id,
                              current_ref, [policy_id, sheet_id])
    return dumps({
        **result, "operator_diagnostic": True,
        "no_live_answer": True, "age0_record_only": True,
        "model_called": False, "native_calls": 0,
        "weight_updates": False, "jepa_weight": 0,
        "ag6_approved": False, "whole_system_complete": False,
    })
