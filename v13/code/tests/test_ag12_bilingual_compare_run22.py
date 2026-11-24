"""Run22 test-first AG12 bilingual read-only comparison, real Runtime/SQLite."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval, KEY, null_solver, oracle_solver
from v13.agi.language_compare import compare_languages


class AG12BilingualCompareRun22(unittest.TestCase):
    def test_empty_operator_comparison_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                before = (rt.store.state(KEY, None), rt.store.state(KEY + "_DE", None))
                from v13.agi import operator_command
                report = json.loads(operator_command(rt, ["eval", "compare", "en-de"]))
                self.assertEqual(report["status"], "MISSING_EN")
                self.assertEqual((rt.store.state(KEY, None), rt.store.state(KEY + "_DE", None)), before)
            finally:
                rt.close()

    def test_english_only_does_not_bootstrap_german_on_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                en = GeneralityEval(rt.store, lang="en")
                en.run(oracle_solver(en.suite), solver_name="v13")
                en_before = rt.store.state(KEY, None)
                de_before = rt.store.state(KEY + "_DE", None)
                self.assertEqual(de_before, (None, 0))
                report = compare_languages(rt.store, solver="v13")
                self.assertEqual(report["status"], "MISSING_DE")
                self.assertFalse(report["learning_proven"])
                self.assertEqual(rt.store.state(KEY, None), en_before)
                self.assertEqual(rt.store.state(KEY + "_DE", None), de_before)
                self.assertEqual(rt.cfg["learning_mode"], "RECORD_ONLY")
            finally:
                rt.close()

    def test_same_generation_complete_en_de_delta_persists_and_operator_exposes_it(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            rt = Runtime(home)
            try:
                en = GeneralityEval(rt.store, lang="en")
                de = GeneralityEval(rt.store, lang="de")
                en.run(oracle_solver(en.suite), solver_name="v13")
                de.run(null_solver, solver_name="v13")
                before = (rt.store.state(KEY, None), rt.store.state(KEY + "_DE", None))
                report = compare_languages(rt.store, solver="v13")
                self.assertEqual(report["status"], "DIAGNOSTIC_ONLY")
                self.assertEqual(report["en"]["overall"], 1.0)
                self.assertEqual(report["de"]["overall"], 0.0)
                self.assertEqual(report["delta_de_minus_en"]["overall"], -1.0)
                self.assertFalse(report["learning_proven"])
                self.assertEqual(report["evidence_level"], "SOFTWARE_PERSISTED_SCORES_ONLY")
                self.assertEqual((rt.store.state(KEY, None), rt.store.state(KEY + "_DE", None)), before)
                from v13.agi import hub, operator_command
                hub(rt)
                after_hub = (rt.store.state(KEY, None), rt.store.state(KEY + "_DE", None))
                output = json.loads(operator_command(rt, ["eval", "compare", "en-de", "v13"]))
                self.assertEqual(output["status"], "DIAGNOSTIC_ONLY")
                self.assertNotIn("Compute:", json.dumps(output))
                self.assertNotIn("answer", json.dumps(output))
                self.assertEqual((rt.store.state(KEY, None), rt.store.state(KEY + "_DE", None)), after_hub)
            finally:
                rt.close()
            rt = Runtime(home)
            try:
                self.assertEqual(compare_languages(rt.store, solver="v13")["status"], "DIAGNOSTIC_ONLY")
            finally:
                rt.close()

    def test_latest_partial_and_different_generation_cannot_compare(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                en = GeneralityEval(rt.store, lang="en")
                de = GeneralityEval(rt.store, lang="de")
                en.run(oracle_solver(en.suite), solver_name="v13")
                de.run(null_solver, solver_name="v13", generation="different-generation")
                self.assertEqual(compare_languages(rt.store)["status"], "GENERATION_MISMATCH")
                de.run(null_solver, solver_name="v13")
                self.assertEqual(compare_languages(rt.store)["status"], "DIAGNOSTIC_ONLY")
                cancelled = threading.Event()
                cancelled.set()
                de.run(null_solver, solver_name="v13", cancel=cancelled)
                self.assertEqual(compare_languages(rt.store)["status"], "INCOMPLETE_DE")
            finally:
                rt.close()

    def test_mismatched_suite_and_corrupt_metric_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                en = GeneralityEval(rt.store, lang="en")
                de = GeneralityEval(rt.store, lang="de")
                en.run(oracle_solver(en.suite), solver_name="v13")
                de.run(null_solver, solver_name="v13")
                for bad in ("nan", True, 10 ** 1000, -0.1, 1.1):
                    with self.subTest(malformed=type(bad).__name__):
                        def corrupt(st):
                            st["runs"][-1]["summary"]["overall"] = bad
                        de.box.mutate(corrupt)
                        self.assertEqual(compare_languages(rt.store)["status"], "INVALID_METRIC_DE")
                rotated = GeneralityEval(rt.store, lang="de", seed=17)
                self.assertEqual(compare_languages(rt.store)["status"], "SUITE_MISMATCH_DE")
                self.assertEqual(rotated.report()["runs"], 0)
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()
