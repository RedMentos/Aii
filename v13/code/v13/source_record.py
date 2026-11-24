"""Run95: explicit human-only Age0 source creation for narrow project budgets.

No model parses or authorizes this command. Source and HumanDecision are
persisted by the existing Store.event + Memory.feedback F1/F5 path.
Review-only candidate; does not change general Runtime._turn.
"""
import re

from .common import dumps

NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,39}\Z", re.ASCII)
AMOUNT = re.compile(r"(?:0|[1-9][0-9]{0,8})\Z", re.ASCII)


def operator_command(r, args):
    if (len(args) not in (3, 4) or args[0] != "budget"
            or (len(args) == 4 and args[3] != "--confirm")):
        raise ValueError(":source budget <ProjectName> <WholeEuroAmount> [--confirm]")
    name, amount = args[1], args[2]
    if (not NAME.fullmatch(name) or not AMOUNT.fullmatch(amount)):
        raise ValueError("Project name or whole Euro amount outside the bounded source grammar")
    key = f"Project {name} budget"
    value = f"{amount} Euro"
    if len(args) == 3:
        return dumps({"status": "CONFIRM_REQUIRED", "key": key, "value": value,
                      "scope": "session", "permission": "record", "writes": False,
                      "next": f":source budget {name} {amount} --confirm"})
    cfg = r.cfg
    if (cfg.get("system_stage") != 0 or cfg.get("learning_mode") != "RECORD_ONLY"
            or cfg.get("latents_enabled") is not False
            or cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE0_RECORD_ONLY_REQUIRED")
    r.require_idle()
    event = r.store.event(r.session, f":source budget {name} {amount} --confirm")
    memory_id = r.memory.feedback(event["event_id"], "fact", value,
                                  key=key, permission="record", scope="session")
    row = r.memory.candidate(memory_id, r.session)
    if (row["key_text"] != key or row["value"] != value
            or not r.memory._verified_rows([row])):
        return dumps({"status": "SOURCE_RECORD_UNVERIFIED",
                      "memory_id": memory_id, "native_calls": 0})
    return dumps({"status": "RECORDED_VERIFIED", "memory_id": memory_id,
                  "key": key, "value": value, "source_ref": row["source_ref"],
                  "scope": "session", "permission": "record",
                  "model_called": False, "native_calls": 0,
                  "age_promotion": False, "learning_weight_commit": False})
