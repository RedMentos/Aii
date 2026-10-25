"""Run366: invalid native probability must not become AG12/JEF confidence.

RED-first source and actual Runtime/Store persistence checks; no native model.
"""
import json
import math
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub
from v13.agi import solver as sv
from v13.agi.base import clamp01


class FiniteConfidenceRun366(unittest.TestCase):
    def test_shared_clamp_fails_closed_for_nonfinite_numbers(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=repr(value)):
                self.assertEqual(clamp01(value), 0.0)
        self.assertEqual(clamp01(-0.2), 0.0)
        self.assertEqual(clamp01(0.65), 0.65)
        self.assertEqual(clamp01(1.8), 1.0)

    def test_native_field_nonfinite_never_becomes_certain(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=repr(value)):
                confidence, source = sv.confidence({"token_confidence": {"field_min_prob": value}})
                self.assertEqual(confidence, 0.0)
                self.assertEqual(source, "nonfinite")
        self.assertEqual(sv.confidence({"token_confidence": {"field_min_prob": 0.75}}), (0.75, "field_min_prob"))
        self.assertEqual(sv.confidence({}), (0.5, "none"))

    def test_nonfinite_and_unbounded_votes_cannot_overpower_valid_coalition(self):
        for poisoned in (float("nan"), float("inf"), 10.0):
            with self.subTest(poisoned=repr(poisoned)):
                result = sv.combine([
                    {"role": "B1_DETAIL", "answer": "wrong", "confidence": poisoned},
                    {"role": "B2_GIST", "answer": "correct", "confidence": 0.9},
                    {"role": "C3_LANGUAGE", "answer": "correct", "confidence": 0.9},
                ])
                self.assertEqual(result["answer"], "correct")
                self.assertEqual(result["agree"], 2)
                self.assertTrue(math.isfinite(result["confidence"]))
                self.assertTrue(all(math.isfinite(x) for x in result["votes"].values()))

    def test_actual_sqlite_generality_calibration_does_not_promote_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            r = Runtime(home)
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                growth = hub(r)
                out = growth.eval.run(
                    lambda view: {"answer": "definitely-wrong", "confidence": float("nan")},
                    solver_name="run366_invalid",
                )
                self.assertEqual(out["status"], "DONE")
                self.assertEqual(out["summary"]["overall"], 0.0)
                self.assertEqual(out["summary"]["calibration"]["ece"], 0.0)
                self.assertEqual(out["summary"]["calibration"]["brier"], 0.0)
                persisted = json.loads((home / "exports" / "generality-last.json").read_text())
                self.assertTrue(persisted["results"])
                self.assertTrue(all(row["confidence"] == 0.0 for row in persisted["results"]))
                self.assertTrue(math.isfinite(persisted["summary"]["calibration"]["ece"]))
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
