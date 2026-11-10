"""V13 JEF/C2 turn-flow scheduler for thinking WHILE C3 speaks.

The real overlap primitive already exists in latewatch: one bounded B1/B2
observer can run alongside a streaming C3 if both fit in RAM. This scheduler
learns WHEN to attempt that extra pass. It cannot manufacture extra hardware,
parallelise the same model process or bypass C5 tool permissions.

A successful text turn is not evidence that an extra observer was useful.
Only explicit local-operator useful/wasteful outcomes train this selector.
MEASURE is default: suggestions are recorded but execution is unchanged.
ACTIVE may *omit* speculative work after sufficient negative feedback; it
cannot force extra resource use, silence C3, authorise tools or override the
human-controlled latewatch cut/revision policy.
"""
from __future__ import annotations

import hashlib

KEY = "JEF_TURN_FLOW_V1"
REVISION = "turn-flow-v1"
MODES = ("measure", "active", "off")
MIN_FEEDBACK = 6
MIN_USEFUL_RATIO = 0.35
MIN_LATE_ONLY = 12   # only optional simple-turn observers, not focal/critical paths
EXPLORE_FRACTION = 4  # one in four eligible turns still probes the body
MAX_EVENTS = 128
MAX_PATTERNS = 48


def _blank():
    return {"revision": REVISION, "mode": "measure", "events": {},
            "patterns": {}, "last": []}


def _read(store):
    value, version = store.state(KEY, None)
    if value is None:
        return _blank(), version
    if type(value) is not dict or value.get("revision") != REVISION:
        raise ValueError("turn-flow revision mismatch")
    if (type(value.get("events")) is not dict or
            type(value.get("patterns")) is not dict or
            value.get("mode") not in MODES):
        raise ValueError("turn-flow state corrupt")
    return value, version


def _mutate(store, func):
    for retry in (0, 1):
        state, version = _read(store)
        result = func(state)
        try:
            store.set_state(KEY, state, expected=version)
            return result
        except ValueError:
            if retry:
                raise


def mode(store):
    return _read(store)[0]["mode"]


def set_mode(store, target, origin="MODEL"):
    """Changing the actual scheduler requires the local operator."""
    if target not in MODES:
        raise ValueError(":turnflow measure|active|off")
    if target == "active" and origin != "OPERATOR_TTY":
        raise PermissionError("Only a local operator may enable adaptive timing")
    return _mutate(store, lambda state: state.__setitem__("mode", target) or target)


def _signals(meta, preoffers, late_role):
    data = meta.get("resource_mode") or {}
    if not isinstance(data, dict):
        data = {}
    focal = meta.get("focal") or {}
    if not isinstance(focal, dict):
        focal = {}
    cycles = focal.get("cycles", 0)
    if type(cycles) is not int or cycles < 0:
        cycles = 0
    # Coarse buckets generalise across different users' messages. No raw text
    # or source material is retained in policy state.
    key = (
        "pre" + ("many" if preoffers >= 2 else str(preoffers)) + "/"
        + ("focal" if cycles else "no_focal") + "/"
        + late_role
    )
    return key, data.get("mode", "UNKNOWN"), cycles


def decide(state, pattern, eligible, residency_ok, event_id=""):
    """Pure choice: a bounded, partly self-trained OPTIONAL-work veto.

    Human-labelled uselessness is independent of timed-out observer evidence.
    A C3 turn with ZERO prior preanswer/focal checks may learn to stop asking
    a consistently late body. The exploration quota guarantees revisits;
    any focal or preanswer reasoning remains unaffected.
    """
    proposals = state.get("patterns", {})
    data = proposals.get(pattern) or {}
    useful = data.get("useful", 0)
    wasted = data.get("wasteful", 0)
    total = useful + wasted
    on_time = data.get("on_time", 0)
    late = data.get("too_late", 0)
    human_veto = total >= MIN_FEEDBACK and (useful + 1) / (total + 2) < MIN_USEFUL_RATIO
    auto_veto = (pattern.startswith("pre0/no_focal/") and
                 late >= MIN_LATE_ONLY and on_time == 0 and useful == 0)
    probe = bool(event_id) and hashlib.sha256(event_id.encode("utf-8")).digest()[0] % EXPLORE_FRACTION == 0
    suppress = state.get("mode") == "active" and (
        human_veto or (auto_veto and not probe)
    )
    usable = eligible and residency_ok
    reason = ("HUMAN_FEEDBACK" if human_veto else
              "REPEATED_UNTIMELY_OBSERVER" if auto_veto and not probe else
              "TIMELINESS_EXPLORATION" if auto_veto and probe else "NO_VETO")
    return {
        "schedule": "SPEAK_AND_CHECK" if usable and not suppress else "SPEAK_ONLY",
        "suggestion": "SPEAK_ONLY" if human_veto or auto_veto and not probe else "SPEAK_AND_CHECK",
        "proposed_concurrency": bool(usable and not suppress),
        "start_optional_observer": bool(usable and not suppress),
        "adaptive_veto": bool(suppress),
        "adaptive_reason": reason,
        "human_feedback_n": total,
        "observer_on_time": on_time,
        "observer_too_late": late,
        "exploration_turn": bool(auto_veto and probe),
        "feedback_n": total,
        "estimated_usefulness": round((useful + 1) / (total + 2), 4),
        "mode": state.get("mode"),
    }


def plan(store, event_id, meta, preoffers, role, eligible=True, residency_ok=True):
    """Called immediately before a C3 token stream, never on every token."""
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("source event id required")
    if type(preoffers) is not int or preoffers < 0:
        raise ValueError("invalid preanswer offer count")
    if role not in ("B1_DETAIL", "B2_GIST"):
        raise ValueError("unknown optional observer role")
    pattern, resource_mode, cycles = _signals(meta, preoffers, role)
    state, _ = _read(store)
    # Scheduling may only DELETE optional extra work, never bypass the
    # already-computed pre-answer deliberation or any C5 permission gate.
    decision = decide(state, pattern, bool(eligible), bool(residency_ok), event_id)
    if state["mode"] in ("measure", "off"):
        decision["start_optional_observer"] = bool(eligible and residency_ok)
        decision["adaptive_veto"] = False
    decision.update({
        "pattern": pattern,
        "resource_mode": resource_mode,
        "preanswer_offers": preoffers,
        "focal_cycles": cycles,
        "thinking_before_speech": bool(preoffers or cycles),
        "concurrent_models_claim": bool(decision["start_optional_observer"] and residency_ok),
        "external_action_authority": "UNCHANGED_C5_GATE",
        "evidence": "SCHEDULE_ONLY_NOT_PROOF_OF_ANSWER_QUALITY",
    })
    if state["mode"] != "off":
        def register(value):
            if event_id not in value["events"]:
                value["events"][event_id] = {"pattern": pattern, "feedback": None,
                                             "scheduled": decision["schedule"]}
            if len(value["events"]) > MAX_EVENTS:
                for old in list(value["events"])[:len(value["events"]) - MAX_EVENTS]:
                    del value["events"][old]
            value["last"] = (value.get("last", []) + [
                {"event": event_id, "schedule": decision["schedule"],
                 "adaptive_veto": decision["adaptive_veto"]}
            ])[-16:]
        _mutate(store, register)
    return decision



OBSERVED_STATUSES = frozenset({
    "AGREES", "WOULD_INTERRUPT", "INTERRUPTED", "AFTER_OUTPUT",
    "NO_OFFER", "STILL_RUNNING",
})


def observe(store, event_id, status):
    """Confirm the existing latewatch actually ran; no success claim is inferred.

    Output status (FINAL etc.) is intentionally irrelevant: a correct answer
    does not imply the concurrent B1/B2 pass helped produce that answer.
    """
    if status not in OBSERVED_STATUSES:
        return None
    def update(state):
        event = state["events"].get(event_id)
        if not event or event.get("scheduled") != "SPEAK_AND_CHECK":
            return None
        if event.get("observer_status") is not None:
            return event["observer_status"]
        event["observer_status"] = status
        # Actual timeliness is an automatically observable cost, not a
        # reward/accuracy claim. A late pass may still help next-turn memory.
        counts = state["patterns"].setdefault(
            event["pattern"], {"useful": 0, "wasteful": 0,
                               "on_time": 0, "too_late": 0}
        )
        field = "on_time" if status in ("AGREES", "WOULD_INTERRUPT", "INTERRUPTED") else "too_late"
        counts[field] = counts.get(field, 0) + 1
        return status
    return _mutate(store, update)



def feedback(store, event_id, outcome):
    """One *explicit* human usefulness label per observed turn.

    "useful" means the optional concurrent observer helped; "wasteful" means
    it did not. Neither is inferred from FINAL status or an automatic critic.
    """
    if outcome not in ("useful", "wasteful"):
        raise ValueError(":turnflow feedback EVENT_ID useful|wasteful")
    def update(state):
        observation = state["events"].get(event_id)
        if observation is None:
            raise ValueError("unknown event; no turn-flow observation")
        if observation["feedback"] is not None:
            raise ValueError("this event was already rated")
        if observation["scheduled"] != "SPEAK_AND_CHECK":
            raise ValueError("cannot rate an observer that was not scheduled")
        if observation.get("observer_status") not in OBSERVED_STATUSES:
            raise ValueError("cannot rate an unobserved concurrent check")
        pattern = observation["pattern"]
        counts = state["patterns"].setdefault(
            pattern, {"useful": 0, "wasteful": 0, "on_time": 0, "too_late": 0}
        )
        counts[outcome] = counts.get(outcome, 0) + 1
        observation["feedback"] = outcome
        if len(state["patterns"]) > MAX_PATTERNS:
            # Never delete the just updated pattern.
            for name in list(state["patterns"]):
                if len(state["patterns"]) <= MAX_PATTERNS:
                    break
                if name != pattern:
                    del state["patterns"][name]
        return {"event_id": event_id, "pattern": pattern,
                "outcome": outcome, "n": counts["useful"] + counts["wasteful"]}
    return _mutate(store, update)


def report(store):
    state, _ = _read(store)
    return {
        "revision": REVISION, "mode": state["mode"],
        "feedback_patterns": {key: dict(value) for key, value in state["patterns"].items()},
        "recent": state["last"][-12:],
        "actual_observer_outcomes": {
            key: sum(v.get("observer_status") == key for v in state["events"].values())
            for key in sorted(OBSERVED_STATUSES)
        },
        "events_with_confirmed_overlap": sum(
            v.get("observer_status") in OBSERVED_STATUSES for v in state["events"].values()
        ),
        "claim_limit": "Only optional late B1/B2 overlap; no forced concurrency, active model thinking, tools, or age-gate changes"
    }


def operator_command(runtime, args):
    """Called only through local Operator.run(origin='OPERATOR_TTY')."""
    store = runtime.store
    if not args or args == ["status"]:
        return report(store)
    if args in (["measure"], ["active"], ["off"]):
        return {"mode": set_mode(store, args[0], origin="OPERATOR_TTY")}
    if len(args) == 3 and args[0] == "feedback":
        return feedback(store, args[1], args[2])
    raise ValueError(":turnflow [status|measure|active|off|feedback EVENT_ID useful|wasteful]")
