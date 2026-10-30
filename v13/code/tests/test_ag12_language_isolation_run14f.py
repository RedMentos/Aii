"""Run14F: English and German AG12 evaluation state must never alias."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval, KEY, build_suite, oracle_solver, null_solver


class AG12LanguageStateIsolation(unittest.TestCase):
    def test_real_sqlite_en_de_runs_and_curves_are_disjoint_across_restart(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                self.assertEqual(runtime.cfg["learning_mode"], "RECORD_ONLY")
                en = GeneralityEval(runtime.store, lang="en")
                de = GeneralityEval(runtime.store, lang="de")
                self.assertEqual(en.box.key, KEY)
                self.assertEqual(de.box.key, KEY + "_DE")
                self.assertNotEqual(en.suite["hash"], de.suite["hash"])
                en_run = en.run(oracle_solver(en.suite), label="run14f-english")
                de_run = de.run(null_solver, label="run14f-german")
                self.assertEqual(en_run["summary"]["overall"], 1.0)
                self.assertEqual(de_run["summary"]["overall"], 0.0)
                self.assertEqual(en.report()["runs"], 1)
                self.assertEqual(de.report()["runs"], 1)
                self.assertEqual(en.curve("overall")[0]["value"], 1.0)
                self.assertEqual(de.curve("overall")[0]["value"], 0.0)
                self.assertEqual(en.report()["suite"]["lang"], "en")
                self.assertEqual(de.report()["suite"]["lang"], "de")
            finally:
                runtime.close()

            reopened = Runtime(home)
            try:
                en2 = GeneralityEval(reopened.store, lang="en")
                de2 = GeneralityEval(reopened.store, lang="de")
                self.assertEqual(en2.report()["runs"], 1)
                self.assertEqual(de2.report()["runs"], 1)
                self.assertEqual(en2.report()["last"]["label"], "run14f-english")
                self.assertEqual(de2.report()["last"]["label"], "run14f-german")
                self.assertEqual(reopened.cfg["learning_mode"], "RECORD_ONLY")
            finally:
                reopened.close()

    def test_language_holdout_and_default_english_hash_remain_intact(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                en = GeneralityEval(runtime.store)
                expected_en = build_suite(13, lang="en")
                self.assertEqual(en.suite["hash"], expected_en["hash"])
                de = GeneralityEval(runtime.store, lang="de")
                en_holdout = next(i["prompt"] for i in en.suite["items"]
                                  if i["split"] == "unseen")
                de_holdout = next(i["prompt"] for i in de.suite["items"]
                                  if i["split"] == "unseen")
                with self.assertRaises(ValueError):
                    en.guard_training([en_holdout])
                with self.assertRaises(ValueError):
                    de.guard_training([de_holdout])
                self.assertEqual(en.box.load()[0]["suite_hash"], expected_en["hash"])
                self.assertEqual(de.box.load()[0]["suite_hash"], de.suite["hash"])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
