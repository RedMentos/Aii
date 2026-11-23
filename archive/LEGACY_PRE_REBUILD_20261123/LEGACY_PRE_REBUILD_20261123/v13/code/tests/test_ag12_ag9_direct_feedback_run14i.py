"""Run14I test-first AG12 -> AG9 feedback must use the exact in-process run."""
from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.agi import hub
from v13.agi.generality import GeneralityEval, null_solver
from v13.agi import solver as solver_module


class FakeBodySolver:
    roles = ("C3_LANGUAGE",)
    stats = {}
    def __init__(self, confidence=0.25):
        self.confidence = confidence
    def __call__(self, view):
        return {"answer": "", "confidence": self.confidence}


class AG12AG9DirectFeedback(unittest.TestCase):
    def test_tampered_export_after_eval_does_not_change_ag9_feedback(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                self.assertEqual(runtime.cfg["learning_mode"], "RECORD_ONLY")
                growth = hub(runtime)
                original_run = growth.eval.run
                def tamper_after_run(*args, **kwargs):
                    completed = original_run(*args, **kwargs)
                    export = home / "exports/generality-last.json"
                    payload = json.loads(export.read_text())
                    payload["results"] = [
                        {"id": item["id"], "confidence": 1.0, "correct": 1}
                        for item in growth.eval.suite["items"]
                    ]
                    export.write_text(json.dumps(payload))
                    return completed
                with patch.object(growth.eval, "run", side_effect=tamper_after_run):
                    with patch.object(solver_module, "make_solver", return_value=FakeBodySolver()):
                        result = solver_module.run(growth, runtime, name="c3")
                self.assertEqual(result["status"], "DONE")
                pairs = growth.metacog.box.load()[0]["components"]["ag12:c3"]["pairs"]
                self.assertEqual(len(pairs), len(growth.eval.suite["items"]))
                self.assertTrue(all(c == 0.25 and correct == 0 for c, correct in pairs))
            finally:
                runtime.close()

    def test_explicit_german_eval_does_not_reuse_english_ag9_feedback(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                growth = hub(runtime)
                with patch.object(solver_module, "make_solver", return_value=FakeBodySolver(0.8)):
                    self.assertEqual(solver_module.run(growth, runtime, "c3")["status"], "DONE")
                en_pairs = list(growth.metacog.box.load()[0]["components"]["ag12:c3"]["pairs"])
                english = home / "exports/generality-last.json"
                en_bytes = english.read_bytes()
                growth.eval = GeneralityEval(runtime.store, home=home, lang="de")
                with patch.object(solver_module, "make_solver", return_value=FakeBodySolver(0.1)):
                    self.assertEqual(solver_module.run(growth, runtime, "c3")["status"], "DONE")
                components = growth.metacog.box.load()[0]["components"]
                self.assertEqual(components["ag12:c3"]["pairs"], en_pairs)
                self.assertEqual(len(components["ag12:c3:de"]["pairs"]), len(growth.eval.suite["items"]))
                self.assertTrue(all(c == 0.1 and correct == 0 for c, correct in components["ag12:c3:de"]["pairs"]))
                self.assertEqual(english.read_bytes(), en_bytes)
                self.assertTrue((home / "exports/generality-last-de.json").is_file())
            finally:
                runtime.close()

    def test_malformed_or_partial_memory_rows_cannot_update_ag9(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                growth = hub(runtime)
                run = growth.eval.run(null_solver, label="existing-export")
                self.assertEqual(run["status"], "DONE")
                suite = growth.eval.suite
                full = [{"id": i["id"], "confidence": 0.2, "correct": 0} for i in suite["items"]]
                for rows in (full[:-1],
                             [dict(full[0], id="wrong-id")] + full[1:],
                             [dict(full[0], confidence=math.nan)] + full[1:],
                             [dict(full[0], correct=True)] + full[1:]):
                    with self.subTest(rows=repr(rows[0])[:50], count=len(rows)):
                        invalid = dict(run, _results=rows)
                        solver_module._feed_metacog(growth, "c3", invalid)
                        self.assertNotIn("ag12:c3", growth.metacog.box.load()[0]["components"])
            finally:
                runtime.close()

    def test_opt_in_ephemeral_rows_never_enter_persisted_run_or_export(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                g = GeneralityEval(runtime.store, home=home)
                out = g.run(null_solver, include_results=True)
                self.assertEqual(len(out["_results"]), len(g.suite["items"]))
                self.assertNotIn("_results", g.box.load()[0]["runs"][-1])
                self.assertNotIn("_results", json.loads((home / "exports/generality-last.json").read_text()))
                self.assertNotIn("_results", g.run(null_solver))
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
