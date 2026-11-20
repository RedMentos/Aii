"""Regression: a procedural policy needs measured latency evidence before READY.

No native model or phone claim: this exercises the real FastForward state machine.
"""
from v13.fastforward import FastForward, SKILL


class Store:
    def __init__(self):
        self.value = None
        self.version = 0

    def state(self, key, default=None):
        return self.value, self.version

    def set_state(self, key, value, expected=None):
        assert expected == self.version
        self.value = value
        self.version += 1


def drive(measured):
    f = FastForward(Store())
    key = "simple|BOOT|short|nonum|nomem|familiar"
    for _ in range(SKILL["compile_after_successes"]):
        assert f.record_turn(key, "none", "FINAL", 5.0) in {"OBSERVE", "SHADOW"}
    assert f.report()["procedures"][key]["stage"] == "SHADOW"
    for _ in range(SKILL["shadow_cycles"]):
        f.record_turn(key, "none", "FINAL", 5.0, predicted_fast_s=2.0 if measured else None)
    return f, key


def test_no_latency_measurement_cannot_promote_ready():
    f, key = drive(False)
    assert f.report()["procedures"][key]["stage"] == "SHADOW"
    assert f.procedural(key)["apply"] is False


def test_measured_noninferior_latency_can_promote_ready():
    f, key = drive(True)
    assert f.report()["procedures"][key]["stage"] == "READY"
    assert f.procedural(key)["apply"] is False  # still requires human ACTIVE


def test_measured_slower_latency_does_not_promote():
    f = FastForward(Store())
    key = "slow"
    for _ in range(SKILL["compile_after_successes"]):
        f.record_turn(key, "none", "FINAL", 5.0)
    for _ in range(SKILL["shadow_cycles"]):
        f.record_turn(key, "none", "FINAL", 5.0, predicted_fast_s=10.0)
    assert f.report()["procedures"][key]["stage"] == "SHADOW"
