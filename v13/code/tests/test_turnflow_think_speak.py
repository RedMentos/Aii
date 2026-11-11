"""Dynamic thinking/speaking decision on real V13 latewatch entrypoint.

These tests prove scheduling only. They do NOT claim concurrent execution on
the Redmi; residency remains the existing physical eligibility check.
"""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from v13 import latewatch, turnflow
from v13.operator import Operator


class StateStore:
    def __init__(self):
        self.data = {}
    def state(self, key, default=None):
        row = self.data.get(key)
        return (deepcopy(row[0]), row[1]) if row else (deepcopy(default), None)
    def set_state(self, key, value, expected=None):
        actual = self.data.get(key)
        if (actual[1] if actual else None) != expected:
            raise ValueError("state compare-and-swap conflict")
        self.data[key] = (deepcopy(value), 1 + (actual[1] if actual else 0))


def test_default_measure_preserves_existing_observer():
    store = StateStore()
    meta = {"resource_mode": {"mode": "NORMAL"}, "focal": {"cycles": 2}}
    result = turnflow.plan(store, "event-measure", meta, 0, "B1_DETAIL")
    assert result["mode"] == "measure"
    assert result["start_optional_observer"]
    assert result["thinking_before_speech"]
    assert result["external_action_authority"] == "UNCHANGED_C5_GATE"
    assert store.state(turnflow.KEY)[0]["events"]["event-measure"]["feedback"] is None


def test_operator_explicit_activation_and_human_feedback_learn_when_to_overlap():
    store = StateStore()
    # First 6 turns have the same coarse state; no source text is retained.
    for i in range(6):
        evt = f"turn-{i}"
        r = turnflow.plan(store, evt, {}, 0, "B1_DETAIL")
        assert r["start_optional_observer"]
        turnflow.observe(store, evt, "AGREES")
        turnflow.feedback(store, evt, "wasteful")
    with pytest.raises(PermissionError):
        turnflow.set_mode(store, "active", origin="MODEL")
    runtime = SimpleNamespace(store=store)
    op = Operator(runtime)
    assert '"mode":"active"' in op.run(":turnflow active")
    selected = turnflow.plan(store, "turn-later", {}, 0, "B1_DETAIL")
    assert selected["schedule"] == "SPEAK_ONLY"
    assert not selected["start_optional_observer"]
    assert selected["adaptive_veto"] and selected["feedback_n"] == 6
    assert selected["estimated_usefulness"] < .35
    # No model output, external authority or content is stored in statistics.
    state = store.state(turnflow.KEY)[0]
    assert "turn-later" in state["events"]
    assert "source" not in str(state)
    assert '"feedback_patterns"' in op.run(":turnflow status")


def test_one_feedback_per_event_and_no_fabricated_training_data():
    store = StateStore()
    with pytest.raises(ValueError):
        turnflow.feedback(store, "not-recorded", "useful")
    turnflow.plan(store, "first", {}, 0, "B1_DETAIL", residency_ok=False)
    with pytest.raises(ValueError, match="not scheduled"):
        turnflow.feedback(store, "first", "useful")
    turnflow.plan(store, "second", {}, 0, "B1_DETAIL")
    with pytest.raises(ValueError, match="unobserved"):
        turnflow.feedback(store, "second", "useful")
    turnflow.observe(store, "second", "AFTER_OUTPUT")
    turnflow.feedback(store, "second", "useful")
    with pytest.raises(ValueError, match="already rated"):
        turnflow.feedback(store, "second", "wasteful")
    with pytest.raises(ValueError):
        turnflow.feedback(store, "second", "unsupported")


def test_adaptive_requires_at_least_six_outcomes_and_never_overrides_pressure():
    store = StateStore()
    turnflow.set_mode(store, "active", origin="OPERATOR_TTY")
    for i in range(5):
        evt = "check-" + str(i)
        assert turnflow.plan(store, evt, {}, 1, "B2_GIST")["start_optional_observer"]
        turnflow.observe(store, evt, "AGREES")
        turnflow.feedback(store, evt, "wasteful")
    assert turnflow.plan(store, "six", {}, 1, "B2_GIST")["start_optional_observer"]
    turnflow.observe(store, "six", "AGREES")
    turnflow.feedback(store, "six", "wasteful")
    assert not turnflow.plan(store, "seven", {}, 1, "B2_GIST")["start_optional_observer"]
    # Another pattern is independent, and memory safety cannot be undone.
    assert turnflow.plan(store, "fresh", {}, 0, "B1_DETAIL")["start_optional_observer"]
    blocked = turnflow.plan(store, "pressure", {}, 0, "B1_DETAIL", residency_ok=False)
    assert not blocked["start_optional_observer"]
    assert blocked["concurrent_models_claim"] is False
    assert "UNCHANGED_C5" in blocked["external_action_authority"]


def test_mode_off_preserves_existing_scheduling_without_history():
    store = StateStore()
    turnflow.set_mode(store, "off", origin="OPERATOR_TTY")
    d = turnflow.plan(store, "no-history", {}, 0, "B1_DETAIL")
    assert d["start_optional_observer"]
    assert store.state(turnflow.KEY)[0]["events"] == {}


def test_actual_latewatch_hook_respects_usefulness_without_starting_extra_thread(monkeypatch):
    store = StateStore()
    r = SimpleNamespace(store=store, cfg={"observer_seconds": 1.,
                                         "observer_mode": "A_THEN_B_SEQUENTIAL"})
    e = {"event_id": "live-observer"}
    runner = SimpleNamespace(role="C3_LANGUAGE")
    meta = {"resource_mode": {"mode": "NORMAL"}}
    started = []
    monkeypatch.setattr(latewatch, "residency", lambda _r, _role: None)
    def fake_start(self, *_args):
        started.append(self.role)
        self.status = "RUNNING"
        return self
    monkeypatch.setattr(latewatch.Watcher, "start", fake_start)
    def one(event):
        return latewatch.start(r, {"event_id": event}, 1, [], time.monotonic() + 4,
                               dict(meta), runner)
    # MEASURE: pre-existing C3-with-B1 overlap still occurs.
    baseline = one("base")
    assert baseline.status == "RUNNING" and started == ["B1_DETAIL"]
    # After explicit human labels, ACTIVE may omit ONLY the optional observer.
    for i in range(6):
        n = f"rated-{i}"
        one(n)
        turnflow.observe(store, n, "AGREES")
        turnflow.feedback(store, n, "wasteful")
    turnflow.set_mode(store, "active", origin="OPERATOR_TTY")
    count = len(started)
    latest_meta = dict(meta)
    changed = latewatch.start(r, e, 1, [], time.monotonic() + 4,
                              latest_meta, runner)
    assert changed.status == "ADAPTIVE_SPEAK_ONLY"
    assert not changed.thread
    assert len(started) == count
    assert latest_meta["turnflow"]["adaptive_veto"]
    # Human may turn the adaptive scheduler off without enabling tools.
    turnflow.set_mode(store, "off", origin="OPERATOR_TTY")
    assert one("restored").status == "RUNNING"


def test_legacy_latewatch_modes_remain_authoritative(monkeypatch):
    store = StateStore()
    r = SimpleNamespace(store=store, cfg={"observer_seconds": 1.,
                                         "observer_mode": "off"})
    watcher = latewatch.start(r, {"event_id": "no-body"}, 1, [],
                              time.monotonic() + 5, {}, SimpleNamespace(role="C3_LANGUAGE"))
    assert watcher.status == "NOT_ELIGIBLE"
    assert store.state(turnflow.KEY)[0] is None


def test_coarse_state_and_feedback_are_bounded():
    store = StateStore()
    for i in range(150):
        turnflow.plan(store, "sample-" + str(i), {}, 0, "B1_DETAIL")
    st = store.state(turnflow.KEY)[0]
    assert len(st["events"]) == turnflow.MAX_EVENTS
    assert len(st["last"]) <= 16


def test_actual_latewatch_finish_confirms_observer_before_feedback():
    store=StateStore()
    event_id="completed-observer"
    turnflow.plan(store,event_id,{},0,"B1_DETAIL")
    with pytest.raises(ValueError,match="unobserved"):
        turnflow.feedback(store,event_id,"wasteful")
    runtime=SimpleNamespace(store=store)
    watcher=latewatch.Watcher(runtime,{"event_id":event_id},{},"shadow",
                              role="B1_DETAIL",status="RUNNING")
    watcher.thread=object()  # a simulated observer thread completed
    watcher.done.set()
    result=watcher.finish(None,[],"answer",time.monotonic()+1,None)
    assert result==""
    assert watcher.status=="NO_OFFER"
    assert store.state(turnflow.KEY)[0]["events"][event_id]["observer_status"]=="NO_OFFER"
    with pytest.raises(ValueError, match="unobserved"):
        turnflow.feedback(store,event_id,"wasteful")
    assert turnflow.report(store)["events_with_confirmed_overlap"]==0


def test_self_learning_from_persistently_late_optional_checks_keeps_exploration():
    """No ratings, no invented quality scores: learn only observed TIMELINESS."""
    store = StateStore()
    for i in range(12):
        evt = f"late-{i}"
        plan = turnflow.plan(store, evt, {}, 0, "B1_DETAIL")
        assert plan["start_optional_observer"]
        assert turnflow.observe(store, evt, "STILL_RUNNING") == "STILL_RUNNING"
    state = turnflow.report(store)
    counts = state["feedback_patterns"]["pre0/no_focal/B1_DETAIL"]
    assert counts["too_late"] == 12 and counts["on_time"] == 0
    assert counts["useful"] == 0 and counts["wasteful"] == 0
    # Measure is non-authoritative, so no unapproved policy change is made.
    assert turnflow.plan(store, "measure", {}, 0, "B1_DETAIL")["start_optional_observer"]
    turnflow.set_mode(store, "active", "OPERATOR_TTY")
    observed = [
        turnflow.plan(store, f"adaptive-{i}", {}, 0, "B1_DETAIL")
        for i in range(32)
    ]
    assert 0 < sum(d["start_optional_observer"] for d in observed) < 16
    assert any(d["adaptive_reason"] == "REPEATED_UNTIMELY_OBSERVER" for d in observed)
    assert any(d["adaptive_reason"] == "TIMELINESS_EXPLORATION" for d in observed)
    assert all(not d["thinking_before_speech"] for d in observed)
    # Even after many late simple checks, focal/preanswer work is not skipped.
    assert turnflow.plan(store, "focal", {"focal": {"cycles": 2}},
                         0, "B1_DETAIL")["start_optional_observer"]
    assert turnflow.plan(store, "preoffer", {}, 1, "B1_DETAIL")["start_optional_observer"]


def test_repeated_no_offer_does_not_train_timeliness_or_veto_observer():
    store = StateStore()
    for i in range(12):
        evt = f"no-offer-{i}"
        assert turnflow.plan(store, evt, {}, 0, "B1_DETAIL")["start_optional_observer"]
        assert turnflow.observe(store, evt, "NO_OFFER") == "NO_OFFER"
    report = turnflow.report(store)
    assert report["feedback_patterns"] == {}
    assert report["events_with_confirmed_overlap"] == 0
    assert report["actual_observer_outcomes"]["NO_OFFER"] == 12
    turnflow.set_mode(store, "active", "OPERATOR_TTY")
    decisions = [turnflow.plan(store, f"no-offer-active-{i}", {}, 0, "B1_DETAIL") for i in range(12)]
    assert all(d["start_optional_observer"] for d in decisions)
    assert all(not d["adaptive_veto"] for d in decisions)


def test_one_timely_exploration_reopens_the_optional_observer():
    store = StateStore()
    for i in range(12):
        evt = f"lasted-{i}"
        turnflow.plan(store, evt, {}, 0, "B1_DETAIL")
        turnflow.observe(store, evt, "STILL_RUNNING")
    turnflow.set_mode(store, "active", "OPERATOR_TTY")
    candidate = next(
        f"probe-{i}" for i in range(100)
        if turnflow.plan(store, f"probe-{i}", {}, 0, "B1_DETAIL")["exploration_turn"]
    )
    sample = turnflow.plan(store, candidate, {}, 0, "B1_DETAIL")
    assert sample["start_optional_observer"]
    turnflow.observe(store, candidate, "WOULD_INTERRUPT")
    after = turnflow.plan(store, "fresh-known-situation", {}, 0, "B1_DETAIL")
    assert after["start_optional_observer"] and not after["adaptive_veto"]
    assert after["observer_on_time"] == 1
