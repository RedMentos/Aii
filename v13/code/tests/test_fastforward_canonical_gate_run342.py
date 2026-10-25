"""Run342 RED-first: unmeasured FastForward READY cannot skip deliberation.

Production FastForward/Runtime/SQLite; synthetic timing only, no native models.
Canon §85.6/G-PROCEDURALIZATION-004 remains unpassed.
"""
import tempfile
import unittest
from pathlib import Path

from v13.fastforward import FastForward, KEY, SKILL
from v13.runtime import Runtime


class ProceduralMeasuredGateRun342(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.f = FastForward(self.r.store)
        self.key = "run342-predicted-only"
        for _ in range(SKILL["compile_after_successes"]):
            self.f.record_turn(self.key, "none", "FINAL", 5.0)
        for _ in range(SKILL["shadow_cycles"]):
            self.f.record_turn(self.key, "none", "FINAL", 5.0, predicted_fast_s=3.0)
        self.assertEqual(self.f.report()["procedures"][self.key]["stage"], "READY")
        self.f.set_mode("ACTIVE", "EXPLICIT_HUMAN")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_predicted_only_ready_must_not_gain_action_authority(self):
        state = self.f.report()["procedures"][self.key]
        self.assertFalse(state["gate"]["canonical_gate_pass"])
        self.assertEqual(state["gate"]["latency_evidence"], "PREDICTOR_ESTIMATE_NOT_MEASURED")
        decision = self.f.procedural(self.key, {})
        self.assertFalse(decision["apply"])
        self.assertEqual(decision["reason"], "CANONICAL_PROCEDURAL_GATE_UNVERIFIED")
        self.assertEqual(decision["stage"], "READY")
        self.assertEqual(decision["key"], self.key)

    def test_boolean_only_spoof_does_not_turn_prediction_into_measurement(self):
        state, version = self.f._load()
        state["procs"][self.key]["gate"]["canonical_gate_pass"] = True
        self.r.store.set_state(KEY, state, expected=version)
        decision = self.f.procedural(self.key, {})
        self.assertFalse(decision["apply"])
        self.assertEqual(decision["reason"], "CANONICAL_PROCEDURAL_GATE_UNVERIFIED")

    def test_missing_gate_stays_untrusted_after_restart(self):
        state, version = self.f._load()
        state["procs"][self.key].pop("gate")
        self.r.store.set_state(KEY, state, expected=version)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.f = FastForward(self.r.store)
        self.assertFalse(self.f.procedural(self.key, {})["apply"])

    def test_shadow_and_novelty_still_bypass_procedure(self):
        self.assertFalse(self.f.procedural(self.key, {"novelty": 0.9})["apply"])
        self.f.set_mode("SHADOW")
        self.assertFalse(self.f.procedural(self.key, {})["apply"])


if __name__ == "__main__":
    unittest.main()
