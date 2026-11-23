"""Run14B: AG12 rejects nonfinite/boolean confidence before scoring."""
from __future__ import annotations

import copy
import math
import unittest

from v13.agi.generality import GeneralityEval


class MemoryStore:
    generation_id = "run14b-software"

    def __init__(self):
        self.data = {}
        self.version = 0
        self.logs = []

    def state(self, key, default):
        return copy.deepcopy(self.data.get(key, default)), self.version

    def set_state(self, key, state, expected=None):
        if expected != self.version:
            raise ValueError("STATE_VERSION_CHANGED")
        self.data[key] = copy.deepcopy(state)
        self.version += 1

    def log(self, name, source, payload):
        self.logs.append((name, source, copy.deepcopy(payload)))


class BatchSolver:
    def __init__(self, answers, confidence):
        self.answers, self.confidence = answers, confidence

    def batch(self, views, cancel, deadline):
        return {v["id"]: {"answer": self.answers[v["id"]],
                           "confidence": self.confidence} for v in views}


class AG12SolverConfidenceContainment(unittest.TestCase):
    def _run(self, confidence, batch=False):
        store = MemoryStore()
        evaluator = GeneralityEval(store)
        answers = {row["id"]: row["answer"] for row in evaluator.suite["items"]}
        solver = (BatchSolver(answers, confidence) if batch else
                  lambda view: {"answer": answers[view["id"]],
                                "confidence": confidence})
        result = evaluator.run(solver, label="run14b")
        return result, store

    def test_invalid_confidence_never_credits_correct_answer(self):
        for value in (float("nan"), float("inf"), float("-inf"),
                      True, False, "NaN", "Infinity"):
            with self.subTest(value=repr(value)):
                result, store = self._run(value)
                self.assertEqual(result["status"], "DONE")
                self.assertEqual(result["summary"]["overall"], 0.0)
                self.assertEqual(result["summary"]["calibration"]["ece"], 0.0)
                self.assertTrue(math.isfinite(result["summary"]["calibration"]["brier"]))
                self.assertTrue(store.logs)

    def test_invalid_batch_confidence_cannot_credit_task(self):
        for value in (float("nan"), float("inf"), True):
            with self.subTest(value=repr(value)):
                result, _ = self._run(value, batch=True)
                self.assertEqual(result["summary"]["overall"], 0.0)
                self.assertEqual(result["status"], "DONE")

    def test_valid_finite_confidence_preserves_correctness(self):
        for value in (0.0, 0.5, 1.0, "0.75", -2, 2):
            with self.subTest(value=repr(value)):
                result, _ = self._run(value)
                self.assertEqual(result["summary"]["overall"], 1.0)
                self.assertTrue(math.isfinite(result["summary"]["calibration"]["ece"]))
        result, _ = self._run(1.0, batch=True)
        self.assertEqual(result["summary"]["overall"], 1.0)
        self.assertEqual(result["summary"]["calibration"]["ece"], 0.0)

    def test_existing_solver_error_still_counts_wrong(self):
        store = MemoryStore()
        evaluator = GeneralityEval(store)
        def failing(_):
            raise RuntimeError("expected")
        self.assertEqual(evaluator.run(failing)["summary"]["overall"], 0.0)


if __name__ == "__main__":
    unittest.main()
