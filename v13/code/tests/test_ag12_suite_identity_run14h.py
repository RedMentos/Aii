"""Run14H test-first AG12 suite-hash scope and stale instance fail-closed checks."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval, oracle_solver, null_solver


class AG12SuiteIdentity(unittest.TestCase):
    def test_new_english_seed_is_due_without_inheriting_prior_curve(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                self.assertEqual(runtime.cfg["learning_mode"], "RECORD_ONLY")
                old = GeneralityEval(runtime.store, seed=13, lang="en")
                old.run(oracle_solver(old.suite), label="seed13")
                self.assertFalse(old.due())
                newer = GeneralityEval(runtime.store, seed=17, lang="en")
                self.assertNotEqual(old.suite["hash"], newer.suite["hash"])
                self.assertTrue(newer.due())
                self.assertEqual(newer.curve("overall"), [])
                self.assertEqual(newer.report()["runs"], 0)
                self.assertIsNone(newer.report()["last"])
                self.assertEqual(len(newer.box.load()[0]["runs"]), 1)  # audit history not deleted
                newer.run(null_solver, label="seed17")
                self.assertEqual(newer.report()["runs"], 1)
                self.assertEqual([x["value"] for x in newer.curve("overall")], [0.0])
                self.assertEqual(len(newer.box.load()[0]["runs"]), 2)
                for stale in (lambda: old.guard_training(["harmless"]),
                              old.practice_items, old.due, old.curve, old.report,
                              lambda: old.run(null_solver)):
                    with self.subTest(method=str(stale)):
                        with self.assertRaisesRegex(ValueError, "AG12_STALE_SUITE"):
                            stale()
                self.assertEqual(len(newer.box.load()[0]["runs"]), 2)
            finally:
                runtime.close()

    def test_german_seed_rotation_does_not_change_english_scope_or_exports(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                en = GeneralityEval(runtime.store, home=home, lang="en")
                en.run(oracle_solver(en.suite), label="english")
                english = home / "exports/generality-last.json"
                en_bytes = english.read_bytes()
                de13 = GeneralityEval(runtime.store, home=home, lang="de", seed=13)
                de13.run(null_solver, label="de13")
                de17 = GeneralityEval(runtime.store, home=home, lang="de", seed=17)
                self.assertTrue(de17.due())
                self.assertEqual(de17.curve(), [])
                self.assertEqual(de17.report()["runs"], 0)
                self.assertEqual(en.report()["runs"], 1)
                self.assertEqual(english.read_bytes(), en_bytes)
                with self.assertRaisesRegex(ValueError, "AG12_STALE_SUITE"):
                    de13.guard_training([de13.suite["items"][0]["prompt"]])
            finally:
                runtime.close()
            reopened = Runtime(home)
            try:
                de17_again = GeneralityEval(reopened.store, home=home, lang="de", seed=17)
                self.assertEqual(de17_again.report()["runs"], 0)
                self.assertEqual(len(de17_again.box.load()[0]["runs"]), 1)
                self.assertEqual(english.read_bytes(), en_bytes)
            finally:
                reopened.close()

    def test_inflight_seed_rotation_cannot_persist_stale_run_or_export(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                original = GeneralityEval(runtime.store, home=home, seed=13)
                original.run(null_solver, label="before-rotation")
                english = home / "exports/generality-last.json"
                before = english.read_bytes()
                changed = []
                def rotating_solver(view):
                    if not changed:
                        changed.append(GeneralityEval(runtime.store, home=home, seed=23))
                    return {"answer": "", "confidence": 0.0}
                with self.assertRaisesRegex(ValueError, "AG12_STALE_SUITE"):
                    original.run(rotating_solver, label="stale-should-not-save")
                self.assertEqual(english.read_bytes(), before)
                self.assertEqual(len(changed[0].box.load()[0]["runs"]), 1)
                self.assertEqual(changed[0].report()["runs"], 0)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
