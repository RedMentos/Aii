"""Regression: malformed live outcomes must not poison persistent F FastForward weights."""
import math
import pytest
from v13 import fastforward as ff


class StateStore:
    def __init__(self):
        self.value = None
        self.version = 0
        self.writes = 0

    def state(self, key, default=None):
        return self.value, self.version

    def set_state(self, key, value, expected=None):
        assert expected == self.version
        self.value = value
        self.version += 1
        self.writes += 1


@pytest.mark.parametrize("change", [
    {"duration_s": float("nan")},
    {"duration_s": float("inf")},
    {"duration_s": -1.0},
    {"chars": -1},
    {"chars": float("nan")},
    {"x": [float("nan")] + [0.] * (len(ff.FEATURES) - 1)},
    {"x": [0.] * (len(ff.FEATURES) - 1)},
    {"x": [float("inf")] + [0.] * (len(ff.FEATURES) - 1)},
])
def test_invalid_outcome_never_mutates_persisted_weights(monkeypatch, change):
    monkeypatch.setattr(ff, "step", lambda *args: 1.)
    store = StateStore()
    learner = ff.FastForward(store)
    args = dict(event_id="turn", x=[1.] + [0.] * (len(ff.FEATURES) - 1),
                duration_s=1., status="FINAL", chars=12)
    args.update(change)
    with pytest.raises(ValueError, match="Invalid fast-forward"):
        learner.learn(**args)
    assert store.writes == 0
    assert store.value is None


def test_valid_outcome_updates_weights_and_restart_reads_them(monkeypatch):
    monkeypatch.setattr(ff, "step", lambda *args: 1.)
    store = StateStore()
    learner = ff.FastForward(store)
    x = [1.] + [0.] * (len(ff.FEATURES) - 1)
    learner.learn("turn", x, 2., "FINAL", 12)
    assert store.writes == 1
    assert store.value["n"] == 1
    assert ff.FastForward(store)._load()[0]["w"]["success"][0] > 0


def test_invalid_modulator_cannot_poison_weights(monkeypatch):
    monkeypatch.setattr(ff, "step", lambda *args: math.nan)
    store = StateStore()
    with pytest.raises(ValueError, match="modulation"):
        ff.FastForward(store).learn("turn", [1.] + [0.] * (len(ff.FEATURES)-1), 2., "FINAL", 12)
    assert store.writes == 0
