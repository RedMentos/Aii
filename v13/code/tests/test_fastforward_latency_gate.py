"""Regression: procedural READY needs measured improvement, not absent timing."""
import unittest
from v13.fastforward import FastForward, SKILL

class StateStore:
    def __init__(self):
        self.value = None
        self.version = 0
    def state(self, key, default=None):
        return self.value, self.version
    def set_state(self, key, value, expected=None):
        if expected != self.version:
            raise ValueError("stale")
        self.value = value
        self.version += 1

class ProceduralLatencyEvidence(unittest.TestCase):
    def run_policy(self, predicted):
        f = FastForward(StateStore())
        key = "simple|boot|short|nonum|nomem|familiar"
        for _ in range(SKILL["compile_after_successes"]):
            f.record_turn(key, "both", "FINAL", 5.)
        self.assertEqual(f.procedural(key)["stage"], "SHADOW")
        for _ in range(SKILL["shadow_cycles"]):
            f.record_turn(key, "both", "FINAL", 5., predicted_fast_s=predicted)
        return f.procedural(key)["stage"]

    def test_no_measurement_cannot_promote(self):
        self.assertEqual(self.run_policy(None), "SHADOW")

    def test_equal_or_slower_cannot_promote(self):
        self.assertEqual(self.run_policy(5.), "SHADOW")
        self.assertEqual(self.run_policy(6.), "SHADOW")

    def test_measured_improvement_can_promote(self):
        self.assertEqual(self.run_policy(2.), "READY")

    def test_nonfinite_prediction_cannot_promote(self):
        self.assertEqual(self.run_policy(float("nan")), "SHADOW")
        self.assertEqual(self.run_policy(float("inf")), "SHADOW")

if __name__ == "__main__":
    unittest.main()
