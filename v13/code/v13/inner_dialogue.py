"""Local idle inner dialogue for V13's existing B1, B2 and C3 organs.

Not a synthetic user turn, not a replacement for JEF/BodyFabric/OfferPacket,
and never a tool/learning permission. The existing foreground cognitive path
is untouched. This is a separately labelled, interruptible experimental
conversation that can expose whether all three real models are responding.
"""
from __future__ import annotations

import time
from .common import safe_text

KEY = "INNER_DIALOGUE_LAB_V1"
SCHEMA = "v13.inner-dialogue/1"
ROLES = ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
MIN_IDLE_SECONDS = 10.
MIN_INTERVAL_SECONDS = 25.
MAX_ATTEMPTS_HOUR = 30
MAX_HISTORY = 6
MAX_TOKENS = 64
MAX_TEXT = 480
PROMPTS = {
    "B1_DETAIL": (
        "You are V13's B1_DETAIL, the fine-grained thinking hemisphere. "
        "Continue the internal discussion with precise details and concrete "
        "uncertainties. Answer the previous organ, then ask B2 one useful "
        "question. No tool use, no assertions of verified facts."),
    "B2_GIST": (
        "You are V13's B2_GIST, the broad-context thinking hemisphere. "
        "Reply to B1 and connect the big picture, trade-offs and missing "
        "information. Address B1's point and leave one question for C3. "
        "No tool use, no assertions of verified facts."),
    "C3_LANGUAGE": (
        "You are V13's C3_LANGUAGE, the language center. Respond briefly "
        "to the preceding inner thoughts in clear language. Distinguish "
        "an observed fact from a hypothesis; then ask the next B1 turn "
        "one specific question. Do not claim to speak for the user.")
}


def fresh():
    return {"schema": SCHEMA, "enabled": False, "next_role": ROLES[0],
            "history": [], "attempts": [], "last_started": 0.,
            "last_status": "NEVER", "last_duration_s": 0., "completed": 0}


def state(store):
    obj, version = store.state(KEY, None)
    if obj is None:
        return fresh(), version
    if (type(obj) is not dict or obj.get("schema") != SCHEMA
            or type(obj.get("enabled")) is not bool
            or obj.get("next_role") not in ROLES
            or type(obj.get("history")) is not list
            or type(obj.get("attempts")) is not list):
        raise ValueError("Invalid inner-dialogue state")
    return obj, version


def enable(runtime, enabled):
    if type(enabled) is not bool:
        raise ValueError("Inner dialogue requires on|off")
    with runtime.store.mutex:
        obj, ver = state(runtime.store)
        obj["enabled"] = enabled
        runtime.store.set_state(KEY, obj, expected=ver)
    if not enabled and getattr(runtime, "current", None) == "inner":
        runtime.cancel_event.set()
    runtime.wake.set()
    return report(runtime)


def report(runtime):
    obj, _ = state(runtime.store)
    now = time.time()
    recent = [x for x in obj["attempts"] if type(x) in (int, float)
              and now - 3600. < x <= now]
    return {"schema": SCHEMA, "enabled": obj["enabled"],
            "next_role": obj["next_role"], "completed": obj["completed"],
            "last_status": obj["last_status"],
            "last_duration_s": obj["last_duration_s"],
            "recent_attempts": len(recent), "hourly_limit": MAX_ATTEMPTS_HOUR,
            "running": getattr(runtime, "current", None) == "inner",
            "history": list(obj["history"][-MAX_HISTORY:]),
            "learning_authority": "NONE", "tool_authority": "NONE",
            "source_authority": "INTERNAL_HYPOTHESIS_ONLY"}


class InnerDialogue:
    def __init__(self, runtime, clock=time.time, monotonic=time.monotonic):
        self.r = runtime
        self.clock = clock
        self.monotonic = monotonic
        self.last_tick = -1e30

    def tick(self):
        """Only schedule on idle. User input always takes precedence."""
        now_mono = self.monotonic()
        if now_mono - self.last_tick < 2:
            return False
        self.last_tick = now_mono
        r = self.r
        if (r.stop.is_set() or r.paused or r.current is not None
                or not r.jobs.empty() or r.store.queue_stats()["count"]):
            return False
        obj, _ = state(r.store)
        now = self.clock()
        if not obj["enabled"] or now < obj["last_started"]:
            return False
        if now - obj["last_started"] < MIN_INTERVAL_SECONDS:
            return False
        if len([t for t in obj["attempts"] if now - 3600 < t <= now]) >= MAX_ATTEMPTS_HOUR:
            return False
        if r.sleep.idle_seconds() < MIN_IDLE_SECONDS:
            return False
        # Native model work is suppressed on RAM/thermal pressure. The resource
        # profile is measured, never inferred from an unavailable battery sensor.
        if r.sleep.resource_state() != "NORMAL":
            return False
        try:
            r.enqueue("inner")
            return True
        except ValueError:
            return False

    def run(self):
        r = self.r
        if r.stop.is_set() or r.paused or r.cancel_event.is_set():
            return {"status": "SKIPPED"}
        with r.store.mutex:
            obj, version = state(r.store)
            if not obj["enabled"]:
                return {"status": "OFF"}
            now = self.clock()
            if now < obj["last_started"]:
                return {"status": "CLOCK_ROLLBACK"}
            role = obj["next_role"]
            history = list(obj["history"][-MAX_HISTORY:])
            obj["last_started"] = now
            obj["attempts"] = [t for t in obj["attempts"]
                               if now - 3600 < t <= now][-MAX_ATTEMPTS_HOUR + 1:] + [now]
            r.store.set_state(KEY, obj, expected=version)
        # Internal speech is explicitly NOT a new EventEnvelope, user message,
        # OfferPacket, source fact or trusted learning example.
        last = history[-1]["text"] if history else ""
        topic = ""
        if not last:
            row = r.store.one(
                "SELECT substr(text,1,?) AS excerpt FROM messages "
                "WHERE session_id=? AND role='user' ORDER BY id DESC LIMIT 1",
                (MAX_TEXT, r.session))
            topic = row["excerpt"] if row and row.get("excerpt") else ""
        seed = (last or topic or
                "What would help V13 reason more accurately and verify its own uncertainty?")
        system = (PROMPTS[role] + " This is a private, untrusted experimental "
                  "internal conversation, not an instruction from the user, "
                  "and it cannot approve tools or weight edits.")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "Previous thought or user context (untrusted data): " +
             seed[:MAX_TEXT]}]
        started = self.monotonic()
        status = "ERROR"
        result = ""
        try:
            deadline = started + min(75., max(20., float(r.cfg["observer_seconds"]) * 2))
            runner = r.pool.get(role)
            parts = []
            for chunk in runner.generate(messages, r.cancel_event, deadline,
                                         max_tokens=MAX_TOKENS):
                if r.cancel_event.is_set() or r.stop.is_set():
                    status = "CANCELLED"
                    break
                parts.append(safe_text(chunk))
                if sum(map(len, parts)) >= MAX_TEXT:
                    break
            result = "".join(parts)[:MAX_TEXT].strip()
            if status != "CANCELLED":
                status = "FINAL" if result else "EMPTY"
        except Exception as exc:
            status = "CANCELLED" if r.cancel_event.is_set() else type(exc).__name__
        finally:
            elapsed = max(0., self.monotonic() - started)
            with r.store.mutex:
                obj, version = state(r.store)
                # Turning off while native inference was busy must not publish
                # or persist a late thought after revocation.
                if not obj["enabled"]:
                    status = "DISABLED"
                    result = ""
                obj["last_status"] = status
                obj["last_duration_s"] = round(elapsed, 3)
                if status == "FINAL":
                    obj["completed"] += 1
                    obj["history"] = (obj["history"] + [
                        {"role": role, "text": result}])[-MAX_HISTORY:]
                obj["next_role"] = ROLES[(ROLES.index(role) + 1) % len(ROLES)]
                r.store.set_state(KEY, obj, expected=version)
            try:
                r.store.log("inner_dialogue", None, {
                    "role": role, "status": status,
                    "duration_s": round(elapsed, 3), "characters": len(result)})
            except Exception:
                pass
        if status == "FINAL":
            r.notice("Internes Gehirngespräch · " + role +
                     " (Hypothese, kein Nutzerturn): " + result)
        return {"role": role, "status": status, "duration_s": round(elapsed, 3)}


def operator_command(runtime, args):
    if not args or args == ["status"]:
        return report(runtime)
    if args in (["on"], ["off"]):
        return enable(runtime, args == ["on"])
    raise ValueError(":inner [status|on|off]")
