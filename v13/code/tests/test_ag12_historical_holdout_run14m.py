"""Run14M test-first: historical AG12 unseen prompts remain excluded."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval, null_solver


def unseen_prompt(g):
    return next(i["prompt"] for i in g.suite["items"] if i["split"] == "unseen")


class AG12HistoricalHoldout(unittest.TestCase):
    def test_old_and_new_unseen_prompt_rejected_after_rotation_and_restart(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                old = GeneralityEval(runtime.store, seed=13)
                old_prompt = unseen_prompt(old)
                old.run(null_solver, label="seed13")
                new = GeneralityEval(runtime.store, seed=17)
                new_prompt = unseen_prompt(new)
                self.assertNotEqual(old.suite["hash"], new.suite["hash"])
                self.assertEqual(new.report()["runs"], 0)
                self.assertEqual(len(new.box.load()[0]["runs"]), 1)
                for prompt in (old_prompt, new_prompt):
                    with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                        new.guard_training([prompt])
                with self.assertRaisesRegex(ValueError, "AG12_STALE_SUITE"):
                    old.guard_training([old_prompt])
            finally:
                runtime.close()
            reopened = Runtime(home)
            try:
                current = GeneralityEval(reopened.store, seed=17)
                for prompt in (old_prompt, new_prompt):
                    with self.subTest(restart=prompt), self.assertRaises(ValueError):
                        current.guard_training([prompt])
                self.assertEqual(len(current.box.load()[0]["runs"]), 1)
            finally:
                reopened.close()

    def test_registry_cap_rejects_rotation_without_eviction_or_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                current = None
                for seed in range(100, 132):
                    current = GeneralityEval(runtime.store, seed=seed)
                before = current.box.load()[0]
                self.assertEqual(len(before["holdout_registry"]), 32)
                with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_CAP"):
                    GeneralityEval(runtime.store, seed=132)
                self.assertEqual(current.box.load()[0], before)
                with self.assertRaises(ValueError):
                    current.guard_training([unseen_prompt(current)])
            finally:
                runtime.close()

    def test_legacy_missing_historical_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                first = GeneralityEval(runtime.store, seed=13)
                first.run(null_solver)
                second = GeneralityEval(runtime.store, seed=17)
                second.run(null_solver)
                def make_legacy(st):
                    st.pop("holdout_registry", None)
                    st.pop("holdout_history_unknown", None)
                    st["holdout"] = sorted({
                        __import__("v13.common", fromlist=["digest"]).digest(
                            __import__("v13.agi.generality", fromlist=["normalize"]).normalize(
                                i["prompt"]))
                        for i in second.suite["items"] if i["split"] == "unseen"
                    })
                second.box.mutate(make_legacy)
                rotated = GeneralityEval(runtime.store, seed=23)
                st = rotated.box.load()[0]
                self.assertTrue(st["holdout_history_unknown"])
                self.assertEqual(len(st["runs"]), 2)
                with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_HISTORY_UNKNOWN"):
                    rotated.guard_training(["benign unrelated training text"])
                with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_HISTORY_UNKNOWN"):
                    rotated.practice_items()
            finally:
                runtime.close()

    def test_corrupted_union_fails_closed_not_repaired_silently(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                g = GeneralityEval(runtime.store, seed=13)
                g.box.mutate(lambda st: st.update(holdout=[]))
                with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_INTEGRITY"):
                    g.guard_training(["benign unrelated training text"])
                with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_INTEGRITY"):
                    GeneralityEval(runtime.store, seed=17)
            finally:
                runtime.close()

    def test_language_isolation_with_historical_holdout(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                en = GeneralityEval(runtime.store, seed=13, lang="en")
                de13 = GeneralityEval(runtime.store, seed=13, lang="de")
                old_de = unseen_prompt(de13)
                de17 = GeneralityEval(runtime.store, seed=17, lang="de")
                with self.assertRaises(ValueError):
                    de17.guard_training([old_de])
                with self.assertRaises(ValueError):
                    en.guard_training([unseen_prompt(en)])
                self.assertEqual(en.box.load()[0]["suite_hash"], en.suite["hash"])
                self.assertNotEqual(en.box.key, de17.box.key)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
