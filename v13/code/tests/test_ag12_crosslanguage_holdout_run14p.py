"""Run14P preregistered: training exclusion is shared across registered EN/DE AG12 suites.

Software SQLite proof only. Evaluation curves and StateBox ownership stay language-local.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval, KEY


def unseen(g):
    return next(i["prompt"] for i in g.suite["items"] if i["split"] == "unseen")


class AG12CrossLanguageHoldout(unittest.TestCase):
    def test_symmetric_registered_unseen_rejected_and_restart_without_cross_writes(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            rt = Runtime(home)
            try:
                self.assertEqual(rt.cfg["learning_mode"], "RECORD_ONLY")
                en = GeneralityEval(rt.store, seed=13, lang="en")
                de = GeneralityEval(rt.store, seed=13, lang="de")
                prompts = (unseen(en), unseen(de))
                self.assertNotEqual(*prompts)
                snapshots = {g.box.key: g.box.load()[0] for g in (en, de)}
                for g in (en, de):
                    for prompt in prompts:
                        with self.subTest(guard=g.suite["lang"], prompt=prompt):
                            with self.assertRaisesRegex(ValueError, "AG12-Holdout"):
                                g.guard_training([prompt])
                    self.assertTrue(g.guard_training(["independent unrelated text"]))
                for g in (en, de):
                    self.assertEqual(g.box.load()[0], snapshots[g.box.key])
            finally:
                rt.close()
            rt = Runtime(home)
            try:
                en = GeneralityEval(rt.store, seed=13, lang="en")
                de = GeneralityEval(rt.store, seed=13, lang="de")
                for g in (en, de):
                    for prompt in prompts:
                        with self.subTest(restarted=g.suite["lang"], prompt=prompt):
                            with self.assertRaisesRegex(ValueError, "AG12-Holdout"):
                                g.guard_training([prompt])
            finally:
                rt.close()

    def test_cross_language_historical_seed_rotation_remains_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                en13 = GeneralityEval(rt.store, seed=13, lang="en")
                de13 = GeneralityEval(rt.store, seed=13, lang="de")
                old_en, old_de = unseen(en13), unseen(de13)
                en17 = GeneralityEval(rt.store, seed=17, lang="en")
                de17 = GeneralityEval(rt.store, seed=17, lang="de")
                for g in (en17, de17):
                    for prompt in (old_en, old_de, unseen(en17), unseen(de17)):
                        with self.subTest(guard=g.suite["lang"], prompt=prompt):
                            with self.assertRaisesRegex(ValueError, "AG12-Holdout"):
                                g.guard_training([prompt])
                self.assertEqual(len(en17.box.load()[0]["holdout_registry"]), 2)
                self.assertEqual(len(de17.box.load()[0]["holdout_registry"]), 2)
            finally:
                rt.close()

    def test_other_language_corrupt_or_unknown_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                en = GeneralityEval(rt.store, lang="en")
                de = GeneralityEval(rt.store, lang="de")
                holdout = list(de.box.load()[0]["holdout"])
                de.box.mutate(lambda st: st.update(holdout=[]))
                with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_INTEGRITY"):
                    en.guard_training(["unrelated text"])
                de.box.mutate(lambda st: st.update(holdout=holdout))
                de.box.mutate(lambda st: st.update(holdout_history_unknown=True))
                with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_HISTORY_UNKNOWN"):
                    en.guard_training(["unrelated text"])
            finally:
                rt.close()

    def test_unregistered_language_does_not_require_bootstrap_or_write(self):
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                en = GeneralityEval(rt.store, lang="en")
                self.assertIsNone(rt.store.state(KEY + "_DE", None)[0])
                self.assertTrue(en.guard_training(["independent unrelated text"]))
                with self.assertRaisesRegex(ValueError, "AG12-Holdout"):
                    en.guard_training([unseen(en)])
                self.assertIsNone(rt.store.state(KEY + "_DE", None)[0])
            finally:
                rt.close()
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            try:
                de = GeneralityEval(rt.store, lang="de")
                self.assertIsNone(rt.store.state(KEY, None)[0])
                self.assertTrue(de.guard_training(["independent unrelated text"]))
                with self.assertRaisesRegex(ValueError, "AG12-Holdout"):
                    de.guard_training([unseen(de)])
                self.assertIsNone(rt.store.state(KEY, None)[0])
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()
