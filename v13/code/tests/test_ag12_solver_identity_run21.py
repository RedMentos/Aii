"""Run21 test-first: AG12 solver names must not alias at the 32-character boundary."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval, null_solver, oracle_solver


PREFIX = "S" * 32
NAME_A = PREFIX + "-body-detail"
NAME_B = PREFIX + "-body-gist"


class AG12SolverIdentityRun21(unittest.TestCase):
    def test_long_names_have_independent_forgetting_and_restart_curves(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            rt = Runtime(home)
            try:
                g = GeneralityEval(rt.store, home=home, seed=13, lang="en")
                first = g.run(oracle_solver(g.suite), solver_name=NAME_A)
                second = g.run(null_solver, solver_name=NAME_B)
                third = g.run(null_solver, solver_name=NAME_A)
                a, b = first["solver"], second["solver"]
                self.assertNotEqual(a, b, "distinct models must not share an AG12 forgetting baseline")
                self.assertLessEqual(len(a), 32)
                self.assertLessEqual(len(b), 32)
                self.assertEqual(a, third["solver"])
                self.assertIsNone(second["summary"]["forgetting"])
                self.assertEqual(third["summary"]["forgetting"]["rate"], 1.0)
                self.assertEqual(len(g.curve(solver=a)), 2)
                self.assertEqual(len(g.curve(solver=b)), 1)
                self.assertEqual(rt.cfg["learning_mode"], "RECORD_ONLY")
            finally:
                rt.close()
            reopened = Runtime(home)
            try:
                g = GeneralityEval(reopened.store, home=home, seed=13, lang="en")
                self.assertEqual(len(g.curve(solver=a)), 2)
                self.assertEqual(len(g.curve(solver=b)), 1)
                self.assertTrue(g.guard_training(["unrelated benign string"]))
            finally:
                reopened.close()

    def test_short_names_and_default_unchanged_and_invalid_names_veto(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                g = GeneralityEval(rt.store)
                self.assertEqual(g.run(null_solver, solver_name="C3")["solver"], "C3")
                self.assertEqual(g.run(null_solver)["solver"], "default")
                before = len(g.box.load()[0]["runs"])
                for bad in (False, True, 0, 12, object(), " " * 5, "X" * 257):
                    with self.subTest(bad=repr(bad)):
                        with self.assertRaises(ValueError):
                            g.run(null_solver, solver_name=bad)
                self.assertEqual(len(g.box.load()[0]["runs"]), before)
            finally:
                rt.close()

    def test_german_names_do_not_alias_or_mutate_english_curves(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                en = GeneralityEval(rt.store, lang="en")
                en.run(null_solver, solver_name="C3")
                de = GeneralityEval(rt.store, lang="de")
                a = de.run(oracle_solver(de.suite), solver_name=NAME_A)
                b = de.run(null_solver, solver_name=NAME_B)
                self.assertNotEqual(a["solver"], b["solver"])
                self.assertIsNone(b["summary"]["forgetting"])
                self.assertEqual(en.report()["runs"], 1)
                self.assertEqual(de.report()["runs"], 2)
                self.assertNotEqual(en.box.key, de.box.key)
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()
