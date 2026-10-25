"""Run300 RED/GREEN: procedural READY needs real finite estimated latency advantage.

Actual production Runtime/Store SQLite, synthetic durations, no native models.
"""
from pathlib import Path
import math
import tempfile
import unittest

from v13.runtime import Runtime
from v13.fastforward import FastForward, SKILL


class FastForwardLatencyGateRun300(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.f = FastForward(self.r.store)

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.temp.cleanup()

    def train_shadow(self, key, prediction):
        for _ in range(SKILL["compile_after_successes"]):
            self.f.record_turn(key, "none", "FINAL", 5.0)
        self.assertEqual(self.f.report()["procedures"][key]["stage"], "SHADOW")
        for _ in range(SKILL["shadow_cycles"]):
            self.f.record_turn(key, "none", "FINAL", 5.0, predicted_fast_s=prediction)
        return self.f.report()["procedures"][key]

    def test_missing_latency_estimate_never_grants_ready_even_after_restart(self):
        key = "run300-missing-latency"
        state = self.train_shadow(key, None)
        self.assertEqual(state["stage"], "SHADOW")
        self.f.set_mode("ACTIVE", "EXPLICIT_HUMAN")
        self.assertFalse(self.f.procedural(key, {})["apply"])
        self.r.close()
        self.r = Runtime(self.home)
        self.f = FastForward(self.r.store)
        self.assertEqual(self.f.report()["procedures"][key]["stage"], "SHADOW")
        self.assertFalse(self.f.procedural(key, {})["apply"])

    def test_invalid_or_nonimproving_predictions_never_grant_ready(self):
        for i, prediction in enumerate((-1.0, 0.0, float("nan"), float("inf"),
                                        True, 5.0)):
            with self.subTest(prediction=str(prediction)):
                state = self.train_shadow(f"run300-invalid-{i}", prediction)
                self.assertEqual(state["stage"], "SHADOW")

    def test_strictly_faster_finite_estimate_retains_shadow_to_ready_path(self):
        key = "run300-positive"
        state = self.train_shadow(key, 3.0)
        self.assertEqual(state["stage"], "READY")
        self.assertTrue(state["gate"]["latency_ok"])
        self.assertEqual(state["gate"]["latency_evidence"], "PREDICTOR_ESTIMATE_NOT_MEASURED")
        self.assertFalse(state["gate"]["canonical_gate_pass"])
        self.assertFalse(self.f.procedural(key, {})["apply"])
        self.f.set_mode("ACTIVE", "EXPLICIT_HUMAN")
        self.assertTrue(self.f.procedural(key, {})["apply"])


if __name__ == "__main__":
    unittest.main()
