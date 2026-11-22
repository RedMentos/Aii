"""Run14G test-first: English and German AG12 exports cannot overwrite each other.

These are software/SQLite tests only, not German model learning evidence.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval, oracle_solver, null_solver


class AG12ExportLanguageIsolation(unittest.TestCase):
    def test_english_export_is_byte_stable_during_two_german_runs(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                self.assertEqual(runtime.cfg["learning_mode"], "RECORD_ONLY")
                en = GeneralityEval(runtime.store, home=home, lang="en")
                en_run = en.run(oracle_solver(en.suite), label="run14g-en")
                english = home / "exports/generality-last.json"
                german = home / "exports/generality-last-de.json"
                self.assertTrue(english.is_file())
                self.assertFalse(german.exists())
                original_en = english.read_bytes()
                self.assertEqual(json.loads(original_en)["suite_hash"], en.suite["hash"])
                self.assertEqual(json.loads(original_en)["summary"]["overall"], 1.0)

                de = GeneralityEval(runtime.store, home=home, lang="de")
                de_run = de.run(null_solver, label="run14g-de-1")
                self.assertTrue(german.is_file())
                self.assertEqual(english.read_bytes(), original_en)
                self.assertEqual(json.loads(german.read_bytes())["suite_hash"], de.suite["hash"])
                self.assertEqual(json.loads(german.read_bytes())["summary"]["overall"], 0.0)
                first_de = german.read_bytes()
                self.assertNotEqual(en_run["suite_hash"], de_run["suite_hash"])
                de.run(null_solver, label="run14g-de-2")
                self.assertEqual(english.read_bytes(), original_en)
                self.assertNotEqual(german.read_bytes(), first_de)
                self.assertEqual(json.loads(german.read_bytes())["label"], "run14g-de-2")
                self.assertEqual(en.report()["runs"], 1)
                self.assertEqual(de.report()["runs"], 2)
            finally:
                runtime.close()

    def test_restart_and_new_english_run_preserve_german_export(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                de = GeneralityEval(runtime.store, home=home, lang="de")
                de.run(null_solver, label="run14g-de-before-restart")
                german = home / "exports/generality-last-de.json"
                english = home / "exports/generality-last.json"
                self.assertTrue(german.is_file())
                self.assertFalse(english.exists())
                before = german.read_bytes()
            finally:
                runtime.close()
            reopened = Runtime(home)
            try:
                self.assertEqual(reopened.cfg["learning_mode"], "RECORD_ONLY")
                en2 = GeneralityEval(reopened.store, home=home, lang="en")
                de2 = GeneralityEval(reopened.store, home=home, lang="de")
                self.assertEqual(de2.report()["runs"], 1)
                self.assertEqual(en2.report()["runs"], 0)
                en2.run(oracle_solver(en2.suite), label="run14g-en-after-restart")
                self.assertTrue(english.is_file())
                self.assertEqual(german.read_bytes(), before)
                self.assertEqual(json.loads(english.read_bytes())["suite_hash"], en2.suite["hash"])
                self.assertEqual(de2.report()["last"]["label"], "run14g-de-before-restart")
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
