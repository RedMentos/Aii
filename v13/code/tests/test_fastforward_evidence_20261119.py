"""Regression: procedural wake authority requires measured speed and a current gate."""
from v13.fastforward import FastForward, SKILL


class Store:
    def __init__(self):
        self.data = None
        self.version = 0

    def state(self, key, default):
        import copy
        return copy.deepcopy(self.data), self.version

    def set_state(self, key, value, expected=None):
        import copy
        assert expected == self.version
        self.data = copy.deepcopy(value)
        self.version += 1


def _shadow_ready_candidate():
    f = FastForward(Store())
    key = "simple|BOOT|short|nonum|nomem|familiar"
    for _ in range(SKILL["compile_after_successes"]):
        f.record_turn(key, "none", "FINAL", 10.0)
    assert f.procedural(key)["stage"] == "SHADOW"
    return f, key


def test_missing_latency_evidence_never_promotes_ready():
    f, key = _shadow_ready_candidate()
    for _ in range(SKILL["shadow_cycles"]):
        f.record_turn(key, "none", "FINAL", 10.0, predicted_fast_s=None)
    assert f.procedural(key)["stage"] == "SHADOW"
    assert not f.procedural(key)["apply"]


def test_measured_speed_can_promote_but_failure_revokes_gate():
    f, key = _shadow_ready_candidate()
    for _ in range(SKILL["shadow_cycles"]):
        f.record_turn(key, "none", "FINAL", 10.0, predicted_fast_s=2.0)
    assert f.procedural(key)["stage"] == "READY"
    f.set_mode("ACTIVE", "EXPLICIT_HUMAN")
    assert f.procedural(key)["apply"]
    f.record_turn(key, "none", "ERROR", 10.0)
    assert not f.procedural(key)["apply"]
    assert f.procedural(key)["stage"] == "OBSERVE"


def test_nonfinite_or_nonpositive_latency_never_promotes():
    for value in (float("nan"), float("inf"), -1.0, 0.0):
        f, key = _shadow_ready_candidate()
        for _ in range(SKILL["shadow_cycles"]):
            f.record_turn(key, "none", "FINAL", 10.0, predicted_fast_s=value)
        assert f.procedural(key)["stage"] == "SHADOW"
