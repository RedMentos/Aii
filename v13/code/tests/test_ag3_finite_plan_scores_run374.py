"""Run374 RED-first: AG3 evaluator must not rank nonfinite/untyped plan scores."""
import copy
import math
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub


class FinitePlanScoresRun374(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.goals = hub(self.runtime).goals
        self.gid = self.goals.add("User plan", steps=["One bounded step"])
        self.before = copy.deepcopy(self.goals.box.load()[0])

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_finite_scores_rank_and_preserve_stable_ties_and_shape(self):
        scores = {
            "first": {"value": 0.9, "risk": 0.1},
            "second": {"value": 0.8, "risk": 0.0},
            "third": {"value": 0.5, "risk": 0.3},
        }
        ranked = self.goals.score_plans(self.gid, list(scores), lambda goal, p: scores[p])
        self.assertEqual([x["plan"] for x in ranked], ["first", "second", "third"])
        self.assertEqual(set(ranked[0]), {"plan", "value", "risk"})
        self.assertEqual(self.goals.box.load()[0], self.before)

    def test_bad_value_or_risk_fails_closed(self):
        for bad in (float("nan"), float("inf"), float("-inf"), True, False, "0.9", None):
            for key in ("value", "risk"):
                with self.subTest(key=key, bad=repr(bad)):
                    def evaluate(goal, p):
                        return {key: bad}
                    with self.assertRaises(ValueError):
                        self.goals.score_plans(self.gid, ["candidate"], evaluate)
                    self.assertEqual(self.goals.box.load()[0], self.before)

    def test_finite_components_with_overflowing_margin_rejected(self):
        for value, risk in ((1e308, -1e308), (-1e308, 1e308)):
            with self.subTest(value=value, risk=risk):
                with self.assertRaises(ValueError):
                    self.goals.score_plans(self.gid, ["candidate"],
                                           lambda goal, p: {"value": value, "risk": risk})
        self.assertEqual(self.goals.box.load()[0], self.before)

    def test_invalid_candidate_cannot_outrank_valid_one(self):
        def evaluate(goal, p):
            return {"value": float("inf"), "risk": 0} if p == "bad" else {"value": 0.9, "risk": 0.1}
        with self.assertRaises(ValueError):
            self.goals.score_plans(self.gid, ["valid", "bad"], evaluate)
        self.assertEqual(self.goals.box.load()[0], self.before)


if __name__ == "__main__":
    unittest.main()
