"""Run14D: real SQLite Runtime/Operator AG9+AG12 Age0 lifecycle proof."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13.agi import hub


class RealSQLiteGrowthLifecycle(unittest.TestCase):
    def test_invalid_component_and_nan_oracle_survive_restart_without_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            r = Runtime(home)
            try:
                self.assertEqual(r.cfg["learning_mode"], "RECORD_ONLY")
                g = hub(r)
                for i in range(20):
                    g.metacog.record("C3_LANGUAGE", i / 19, i >= 10)
                self.assertIsInstance(g.metacog.calibrated("C3_LANGUAGE", 0.75), float)
                version = g.metacog.box.load()[1]
                self.assertEqual(g.metacog.decide([], 0.75), {
                    "calibrated": None, "second_attempt": False,
                    "abstain": True, "reason": "INVALID_COMPONENT",
                })
                self.assertEqual(g.metacog.box.load()[1], version)
                answers = {row["id"]: row["answer"] for row in g.eval.suite["items"]}
                result = g.eval.run(
                    lambda v: {"answer": answers[v["id"]], "confidence": float("nan")},
                    label="run14d-invalid")
                self.assertEqual(result["status"], "DONE")
                self.assertEqual(result["summary"]["overall"], 0.0)
                view = json.loads(Operator(r).run(":growth eval"))
                self.assertEqual(view["last"]["summary"]["overall"], 0.0)
                status = json.loads(Operator(r).run(":growth status"))
                self.assertEqual(status["AG12"]["last"]["summary"]["overall"], 0.0)
            finally:
                r.close()

            reopened = Runtime(home)
            try:
                self.assertEqual(reopened.cfg["learning_mode"], "RECORD_ONLY")
                g2 = hub(reopened)
                self.assertIsInstance(g2.metacog.calibrated("C3_LANGUAGE", 0.75), float)
                self.assertEqual(g2.eval.report()["last"]["summary"]["overall"], 0.0)
                self.assertEqual(g2.eval.report()["last"]["label"], "run14d-invalid")
                self.assertEqual(g2.metacog.decide({}, 0.75)["reason"],
                                 "INVALID_COMPONENT")
            finally:
                reopened.close()

    def test_finite_oracle_and_invalid_batch_are_separate_persisted_runs(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            r = Runtime(home)
            try:
                g = hub(r)
                answers = {row["id"]: row["answer"] for row in g.eval.suite["items"]}
                finite = g.eval.run(
                    lambda v: {"answer": answers[v["id"]], "confidence": 1.0},
                    label="run14d-finite")
                self.assertEqual(finite["summary"]["overall"], 1.0)
                self.assertEqual(finite["summary"]["calibration"]["ece"], 0.0)

                class Batch:
                    def batch(self, views, cancel, deadline):
                        return {v["id"]: {"answer": answers[v["id"]],
                                           "confidence": float("inf")} for v in views}

                invalid = g.eval.run(Batch(), label="run14d-batch-invalid")
                self.assertEqual(invalid["summary"]["overall"], 0.0)
                self.assertEqual(g.eval.report()["runs"], 2)
            finally:
                r.close()

            reopened = Runtime(home)
            try:
                g2 = hub(reopened)
                self.assertEqual(g2.eval.report()["runs"], 2)
                self.assertEqual(g2.eval.report()["last"]["label"],
                                 "run14d-batch-invalid")
                self.assertEqual(reopened.cfg["learning_mode"], "RECORD_ONLY")
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
