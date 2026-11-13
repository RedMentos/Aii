"""Bounded G13 idle laboratory: real B1↔B2↔C3 thoughts and C2 warm checks.

Never creates a synthetic user event, a trusted T8 training label, a tool
invocation, or a promoted Age/weight update. Each job runs on the existing V13
coordinator, yields to user input, reuses RunnerPool warm residency, and
records only small private technical status plus provisional inner speech.
"""
from __future__ import annotations

import time
from .common import safe_text, Cancelled

KEY = "G13_NATIVE_LAB_CYCLE_V1"
SCHEMA = "v13.native-lab-cycle/1"
ROLES = ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE", "C2_CONTROL")
MAX_HISTORY = 6
MAX_TEXT = 320
MAX_RUNS_HOUR = 18
MIN_IDLE_S = 10.
DEFAULT_INTERVAL_S = 90.
ROLE_SYSTEM = {
    "B1_DETAIL": "You are V13 B1_DETAIL, the detailed reasoning hemisphere. "
                 "Respond to the preceding inner thought with a specific uncertainty "
                 "and one question for B2. This is provisional internal reasoning, "
                 "not a user instruction, fact, tool command or verified result.",
    "B2_GIST": "You are V13 B2_GIST, the broad-context reasoning hemisphere. "
               "Answer B1's question, connect the general picture and ask C3 for "
               "a clear distinction between an observation and hypothesis. "
               "This internal exchange cannot authorize tools or changes.",
    "C3_LANGUAGE": "You are V13 C3_LANGUAGE. Condense the ongoing B1/B2 discussion "
                   "in ordinary language, acknowledge uncertainty and pose one "
                   "useful question back to B1. Never claim it is a user request."
}


def initial():
    # User explicitly asked for active, reversible tests while V13 is on.
    # This affects only synthetic local probes; trained weights remain frozen.
    return dict(schema=SCHEMA, enabled=True, interval_s=DEFAULT_INTERVAL_S,
                next_role=ROLES[0], last_started=0., recent_started=[],
                history=[], completed=0, last_result={"status": "NEVER"})


def load(store):
    value, version = store.state(KEY, None)
    if value is None:
        return initial(), version
    if (type(value) is not dict or value.get("schema") != SCHEMA
            or type(value.get("enabled")) is not bool
            or value.get("next_role") not in ROLES
            or type(value.get("interval_s")) not in (int, float)
            or not 30. <= value["interval_s"] <= 1800.
            or type(value.get("last_started")) not in (int, float)
            or type(value.get("recent_started")) is not list
            or type(value.get("history")) is not list
            or type(value.get("completed")) is not int
            or type(value.get("last_result")) is not dict):
        raise ValueError("Invalid native lab state")
    return value, version


def status(runtime):
    obj, _ = load(runtime.store)
    now = time.time()
    recent = [x for x in obj["recent_started"] if type(x) in (int, float)
              and now - 3600. < x <= now]
    return {"schema": SCHEMA, "enabled": obj["enabled"],
            "interval_s": obj["interval_s"], "next_role": obj["next_role"],
            "completed": obj["completed"], "last_result": dict(obj["last_result"]),
            "recent_attempts": len(recent), "limit_per_hour": MAX_RUNS_HOUR,
            "last_thoughts": list(obj["history"][-MAX_HISTORY:]),
            "resident_roles": sorted(runtime.pool.resident_roles())
                              if hasattr(runtime.pool, "resident_roles") else [],
            "official_age_unchanged": True, "learning_authority": "NONE",
            "tool_authority": "NONE", "training_data_source": "SYNTHETIC_UNTRUSTED"}


def configure(runtime, *, enabled=None, interval=None, reset=False):
    with runtime.store.mutex:
        obj, ver = load(runtime.store)
        if enabled is not None:
            if type(enabled) is not bool:
                raise ValueError("Lab on|off")
            obj["enabled"] = enabled
        if interval is not None:
            if type(interval) is not int or not 30 <= interval <= 1800:
                raise ValueError("Interval 30..1800 seconds")
            obj["interval_s"] = float(interval)
        if reset:
            obj["history"] = []
            obj["last_result"] = {"status": "RESET"}
        runtime.store.set_state(KEY, obj, expected=ver)
    if enabled is False and getattr(runtime.sleep, "lab_active", False):
        runtime.cancel_event.set()
    runtime.wake.set()
    return status(runtime)


def maybe_schedule(sleep, resource):
    r = sleep.r
    if r.stop.is_set() or r.paused or not r.idle():
        return None
    if resource != "NORMAL" or sleep.idle_seconds() < MIN_IDLE_S:
        return None
    obj, _ = load(r.store)
    if not obj["enabled"]:
        return None
    now = sleep.clock()
    if now < obj["last_started"] or now - obj["last_started"] < obj["interval_s"]:
        return None
    recent = [x for x in obj["recent_started"] if type(x) in (int, float)
              and now - 3600. < x <= now]
    if len(recent) >= MAX_RUNS_HOUR:
        return None
    return sleep.scheduler.post("IDLE", origin="SYSTEM", action="lab_check",
                                dedup="v13-native-lab-check", ttl=600.)


def run(runtime):
    """One organ per G13 wake; native models remain loaded when resources allow."""
    r = runtime
    if r.stop.is_set() or r.paused or r.cancel_event.is_set():
        return {"status": "CANCELLED"}
    if r.sleep.resource_state() != "NORMAL":
        return {"status": "SKIPPED_RESOURCE"}
    with r.store.mutex:
        obj, ver = load(r.store)
        if not obj["enabled"]:
            return {"status": "OFF"}
        role = obj["next_role"]
        history = list(obj["history"][-MAX_HISTORY:])
        now = r.sleep.clock()
        obj["last_started"] = now
        obj["recent_started"] = [x for x in obj["recent_started"]
                                 if type(x) in (int, float) and now - 3600 < x <= now][-MAX_RUNS_HOUR+1:] + [now]
        obj["next_role"] = ROLES[(ROLES.index(role) + 1) % len(ROLES)]
        r.store.set_state(KEY, obj, expected=ver)
    last = history[-1]["text"] if history else ""
    start = time.monotonic()
    deadline = start + min(45., max(15., float(r.cfg.get("observer_seconds", 35.))))
    result_text = ""
    state = "ERROR"
    runner = None
    r.sleep.lab_active = True
    try:
        if role == "C2_CONTROL":
            r.needle.load(r.cancel_event, deadline)
            state = "LOADED"  # C2 is control, not a fake language speaker.
        else:
            runner = r.pool.get(role)
            messages = [
                {"role": "system", "content": ROLE_SYSTEM[role]},
                {"role": "user", "content":
                 "Unverified previous thought: " +
                 (last[:MAX_TEXT] or "What measurement could falsify V13's claim to be learning?")}]
            parts = []
            for token in runner.generate(messages, r.cancel_event, deadline,
                                         max_tokens=32):
                if r.stop.is_set() or r.cancel_event.is_set():
                    state = "CANCELLED"
                    break
                parts.append(safe_text(token))
                if sum(map(len, parts)) >= MAX_TEXT:
                    break
            result_text = "".join(parts)[:MAX_TEXT].strip()
            if state != "CANCELLED":
                state = "FINAL" if result_text else "EMPTY"
    except Cancelled:
        state = "CANCELLED"
    except Exception as exc:
        state = "CANCELLED" if r.cancel_event.is_set() else type(exc).__name__
    finally:
        r.sleep.lab_active = False
        elapsed = max(0., time.monotonic() - start)
        metrics = dict(getattr(runner, "last_metrics", {}) or {}) if runner else {}
        last_result = {"role": role, "status": state, "duration_s": round(elapsed, 3),
                       "generated_characters": len(result_text),
                       "native_tokens": metrics.get("generated_tokens", 0)}
        with r.store.mutex:
            obj, ver = load(r.store)
            if not obj["enabled"]:
                state = "DISABLED"
                last_result["status"] = state
                result_text = ""
            obj["last_result"] = last_result
            if state == "FINAL":
                obj["history"] = (obj["history"] + [{"role": role, "text": result_text}])[-MAX_HISTORY:]
                obj["completed"] += 1
            r.store.set_state(KEY, obj, expected=ver)
        try:
            r.store.log("native_lab", None, {k: last_result[k] for k in
                        ("role", "status", "duration_s", "generated_characters", "native_tokens")})
        except Exception:
            pass
    if state == "FINAL":
        r.notice("Interner Modelltest " + role + " · vorläufige Hypothese: " + result_text)
    return {"status": state, "role": role, "duration_s": round(elapsed, 3)}


def operator_command(runtime, args):
    if args == ["summary"]:
        result = status(runtime)
        result.pop("last_thoughts", None)  # safe for private technical relay
        return result
    if not args or args == ["status"]:
        return status(runtime)
    if args == ["on"] or args == ["off"]:
        return configure(runtime, enabled=(args == ["on"]))
    if args == ["reset"]:
        return configure(runtime, reset=True)
    if len(args) == 2 and args[0] == "every":
        return configure(runtime, interval=int(args[1]))
    if args == ["now"]:
        event_id = runtime.sleep.scheduler.post("TIMER", origin="USER",
                     action="lab_check", dedup="v13-native-lab-check")
        runtime.sleep.tick(force=True)
        return {"queued": bool(event_id), "event_id": event_id,
                "status": operator_command(runtime, ["summary"])}
    raise ValueError(":scheduler lab [status|summary|on|off|reset|now|every 30..1800]")
