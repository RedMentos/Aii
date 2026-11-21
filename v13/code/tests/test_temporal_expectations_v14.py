"""Synthetic contract tests; no native Android or JEPA utility claim."""
import copy
from types import SimpleNamespace

import pytest
from v13 import temporal_expectations_v14 as temporal


class Store:
    def __init__(self):
        self.state = {}
    def get_state(self, key):
        return copy.deepcopy(self.state.get(key))
    def set_state(self, key, value):
        self.state[key] = copy.deepcopy(value)


def test_pending_deadline_is_censored_not_negative(monkeypatch):
    store = Store()
    runtime = SimpleNamespace(store=store)
    monkeypatch.setattr(temporal.world_model, "transitions", lambda *_args, **_kwargs: [])
    temporal.expect(runtime, expectation_id="e1", condition_source="source:1",
                    predicted_outcome="success", now_s=10, deadline_s=20,
                    probability=0.8)
    assert temporal.observe(runtime, now_s=21)["omission_learning"] == "OFF_NO_COVERAGE_PROOF"
    assert store.get_state(temporal.KEY)["pending"]["e1"]["status"] == "CENSORED"
    assert temporal.observe(runtime, now_s=22)["censored"] == 0


def test_committed_t8_is_observed_and_restart_idempotent(monkeypatch):
    store = Store()
    runtime = SimpleNamespace(store=store)
    row = {"action_id": "action:1", "a": "simple", "y": [0.2, 1.0, 0.1]}
    monkeypatch.setattr(temporal.world_model, "transitions",
                        lambda *_args, **_kwargs: [row])
    temporal.expect(runtime, expectation_id="action:1", condition_source="source:1",
                    predicted_outcome="success", now_s=10, deadline_s=200, probability=0.8)
    first = temporal.observe(runtime, now_s=100)
    assert first["observed"] == 1
    assert temporal.observe(SimpleNamespace(store=store), now_s=101)["observed"] == 0
    assert store.get_state(temporal.KEY)["resolved"]["action:1"]["evidence"]["kind"] == "T8_COMMITTED"


def test_refuse_bad_sources_and_unbounded_expectations():
    runtime = SimpleNamespace(store=Store())
    with pytest.raises(ValueError):
        temporal.expect(runtime, expectation_id="x", condition_source="",
                        predicted_outcome="ok", now_s=1, deadline_s=2,
                        probability=0.5)
    with pytest.raises(ValueError):
        temporal.expect(runtime, expectation_id="x", condition_source="s",
                        predicted_outcome="ok", now_s=1, deadline_s=100000,
                        probability=0.5)


def test_unrelated_t8_cannot_resolve_an_expectation(monkeypatch):
    store = Store()
    runtime = SimpleNamespace(store=store)
    temporal.expect(runtime, expectation_id="action:target", condition_source="source:target",
                    predicted_outcome="success", now_s=10, deadline_s=20, probability=0.9)
    monkeypatch.setattr(temporal.world_model, "transitions", lambda *_a, **_kw: [
        {"action_id": "action:other", "a": "simple", "y": [0.1, 1.0, 0.1]}])
    result = temporal.observe(runtime, now_s=21)
    assert result["observed"] == 0
    assert result["censored"] == 1
    assert store.get_state(temporal.KEY)["resolved"] == {}


def test_t8_success_scoring_is_restart_stable_and_censored_unscored(monkeypatch):
    store = Store()
    runtime = SimpleNamespace(store=store)
    temporal.expect(runtime, expectation_id="a1", condition_source="source:1",
                    predicted_outcome="success", now_s=1, deadline_s=10,
                    probability=0.8)
    temporal.expect(runtime, expectation_id="a2", condition_source="source:2",
                    predicted_outcome="success", now_s=1, deadline_s=10,
                    probability=0.9)
    monkeypatch.setattr(temporal.world_model, "transitions", lambda *_a, **_kw: [
        {"action_id": "a1", "a": "detail", "y": [0.2, 1.0, 0.1]}])
    result = temporal.observe(runtime, now_s=11)
    assert result["scored"] == 1
    state = store.get_state(temporal.KEY)
    assert state["resolved"]["a1"]["success_brier"] == 0.04
    assert state["pending"]["a2"]["status"] == "CENSORED"
    assert temporal.observe(SimpleNamespace(store=store), now_s=12)["scored"] == 0


def test_declared_binary_hypothesis_and_readback(monkeypatch):
    store = Store()
    runtime = SimpleNamespace(store=store)
    for key, hypothesis in (("success_id", "success"), ("failure_id", "failure"),
                            ("other_id", "rain")):
        temporal.expect(runtime, expectation_id=key, condition_source="source:" + key,
                        predicted_outcome=hypothesis, now_s=1, deadline_s=20,
                        probability=0.8)
    monkeypatch.setattr(temporal.world_model, "transitions", lambda *_a, **_kw: [
        {"action_id": key, "a": "simple", "y": [0.2, 1.0, 0.1]}
        for key in ("success_id", "failure_id", "other_id")])
    assert temporal.observe(runtime, now_s=10)["scored"] == 2
    rows = store.get_state(temporal.KEY)["resolved"]
    assert rows["success_id"]["success_brier"] == 0.04
    assert rows["failure_id"]["success_brier"] == 0.64
    assert rows["failure_id"]["hypothesis_label"] == 0.0
    assert rows["other_id"]["success_brier"] is None
    assert temporal.score_snapshot(SimpleNamespace(store=store)) == {
        "status": "IN_SAMPLE_ONLY", "scored": 2, "mean_brier": 0.34,
        "heldout_utility": "UNVERIFIED", "weights_updated": False}
    assert temporal.observe(runtime, now_s=11)["scored"] == 0
