"""Run380: AG8 must not promote invalid or rounded-away regressions.

Real Runtime/Store SQLite and human-gated proposal path, deterministic synthetic
evaluation scores. No model/Redmi/learning utility claim.
"""
import math
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.age import AgeControl
from v13.agi.self_improve import SelfImprovement


class AG8ShieldMetricsRun380(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.si = SelfImprovement(self.r.store, self.r.cfg, AgeControl(self.r.store, self.r.cfg))
        self.base = {"overall": 0.5, "seen": 0.5, "unseen": 0.5}

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def request_count(self):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM requests WHERE kind='SELF_IMPROVEMENT'"
        )["n"]

    def propose_and_evaluate(self, base, candidate):
        pid = self.si.propose("knob", {"memory_top_k": 4}, origin="USER")
        return pid, self.si.evaluate(
            pid, lambda settings: base if settings is None else candidate
        )

    def test_sub_rounding_regression_is_not_approved(self):
        pid, result = self.propose_and_evaluate(
            self.base, {"overall": 0.54, "seen": 0.5, "unseen": 0.47996}
        )
        self.assertEqual(result["status"], "SHIELD_FAIL")
        self.assertIn("unseen", result["shield"]["regressions"])
        self.assertLess(result["shield"]["axes"]["unseen"]["delta"], -0.02)
        self.assertIsNone(result["request_id"])
        self.assertEqual(self.request_count(), 0)

    def test_sub_rounding_gain_does_not_cross_minimum(self):
        pid, result = self.propose_and_evaluate(
            self.base, {"overall": 0.50996, "seen": 0.5, "unseen": 0.5}
        )
        self.assertEqual(result["status"], "SHIELD_FAIL")
        self.assertLess(result["shield"]["gain"], 0.01)
        self.assertEqual(self.request_count(), 0)

    def test_invalid_or_incomplete_metrics_cannot_create_request(self):
        cases = {
            "nan_unseen": (self.base, {"overall": 0.54, "seen": 0.5, "unseen": math.nan}),
            "inf_overall": (self.base, {"overall": math.inf, "seen": 0.5, "unseen": 0.5}),
            "missing_unseen": (self.base, {"overall": 0.54, "seen": 0.5}),
            "bool_seen": (self.base, {"overall": 0.54, "seen": True, "unseen": 0.5}),
            "outside_range": (self.base, {"overall": 1.1, "seen": 0.5, "unseen": 0.5}),
            "one_sided_forgetting": (
                dict(self.base, forgetting={"rate": 0.1}),
                {"overall": 0.54, "seen": 0.5, "unseen": 0.5},
            ),
            "inf_forgetting": (
                dict(self.base, forgetting={"rate": 0.1}),
                {"overall": 0.54, "seen": 0.5, "unseen": 0.5,
                 "forgetting": {"rate": math.inf}},
            ),
        }
        for label, (base, candidate) in cases.items():
            with self.subTest(label=label):
                pid = self.si.propose("knob", {"memory_top_k": 4}, origin="USER")
                before = self.request_count()
                with self.assertRaises(ValueError):
                    self.si.evaluate(
                        pid, lambda settings: base if settings is None else candidate
                    )
                self.assertEqual(self.si.get(pid)["status"], "PROPOSED")
                self.assertEqual(self.request_count(), before)

    def test_forgetting_regression_above_exact_threshold_blocks_gain(self):
        pid, result = self.propose_and_evaluate(
            dict(self.base, forgetting={"rate": 0.1}),
            {"overall": 0.54, "seen": 0.5, "unseen": 0.5,
             "forgetting": {"rate": 0.12004}},
        )
        self.assertEqual(result["status"], "SHIELD_FAIL")
        self.assertIn("forgetting", result["shield"]["regressions"])
        self.assertEqual(self.request_count(), 0)

    def test_invalid_baseline_cannot_be_masked_by_candidate_gain(self):
        pid = self.si.propose("knob", {"memory_top_k": 4}, origin="USER")
        with self.assertRaises(ValueError):
            self.si.evaluate(pid, lambda settings:
                {"overall": 0.5, "seen": 0.5, "unseen": float("nan")}
                if settings is None else
                {"overall": 0.9, "seen": 0.9, "unseen": 0.9})
        self.assertEqual(self.si.get(pid)["status"], "PROPOSED")
        self.assertEqual(self.request_count(), 0)

    def test_complete_finite_improvement_remains_human_gated(self):
        pid, result = self.propose_and_evaluate(
            dict(self.base, forgetting={"rate": 0.1}),
            {"overall": 0.54, "seen": 0.5, "unseen": 0.5,
             "forgetting": {"rate": 0.1}},
        )
        self.assertEqual(result["status"], "PENDING_USER")
        self.assertEqual(self.request_count(), 1)
        self.assertEqual(self.r.cfg["memory_top_k"], 3)
        self.assertEqual(self.si.approve(pid)["settings"]["memory_top_k"], 4)
        self.assertEqual(self.r.cfg["memory_top_k"], 3)


if __name__ == "__main__":
    unittest.main()
