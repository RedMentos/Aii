"""Run14Q test-first: Sleep TTT staging must not leak registered AG12 unseen prompts.

Uses real Runtime/SQLite/source lineage with mocked language model output; no native calls.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13 import sleep_offline as S
from v13.agi.generality import GeneralityEval, KEY
from tests.test_sleep_offline import Base


def unseen(g):
    return next(i["prompt"] for i in g.suite["items"] if i["split"] == "unseen")


def staged(home):
    path = home / "exports/sleep-ttt-candidates.jsonl"
    return [json.loads(s) for s in path.read_text().splitlines() if s]


class SleepAG12Staging(Base):
    def test_registered_english_german_inputs_targets_and_context_excluded(self):
        en = GeneralityEval(self.r.store, lang="en")
        de = GeneralityEval(self.r.store, lang="de")
        en_prompt, de_prompt = unseen(en), unseen(de)
        self.turn("Ordinary context number zero about a recipe?", "The answer is to simmer gently.")
        self.turn(en_prompt, "This must not become a training label.")
        self.turn("A harmless question?", de_prompt)  # holdout in target, not just input
        self.turn(de_prompt, "This must not become a training label either.")
        for i in range(7):
            self.turn("Ordinary followup number %d about the recipe?" % i,
                      "Use clean water and keep the pot covered number %d." % i)
        self.assertGreaterEqual(S.digest(self.r.store)["turns"], 10)
        rep = S.stage_ttt(self.r.store, self.home)
        rows = staged(self.home)
        self.assertEqual(rep["candidates"], len(rows))
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(all(r["status"] == "CANDIDATE_NOT_TRAINED" for r in rows))
        for row in rows:
            serialized = json.dumps(row, ensure_ascii=False)
            self.assertNotIn(en_prompt, serialized)
            self.assertNotIn(de_prompt, serialized)
        self.assertEqual(en.report()["runs"], 0)
        self.assertEqual(de.report()["runs"], 0)

    def test_historical_german_holdout_filtered_after_seed_rotation_and_restart(self):
        en = GeneralityEval(self.r.store, lang="en", seed=13)
        de13 = GeneralityEval(self.r.store, lang="de", seed=13)
        old = unseen(de13)
        GeneralityEval(self.r.store, lang="de", seed=17)
        self.turn("Ordinary starter question?", "Answer starter.")
        self.turn(old, "A heldout prompt was observed but not a training label.")
        for i in range(7):
            self.turn("Ordinary followup number %d?" % i, "Ordinary answer %d." % i)
        S.digest(self.r.store)
        S.stage_ttt(self.r.store, self.home)
        self.assertTrue(staged(self.home))
        self.assertTrue(all(old not in json.dumps(x, ensure_ascii=False) for x in staged(self.home)))
        self.r.close()
        reopened = Runtime(self.home)
        try:
            S.stage_ttt(reopened.store, self.home)
            self.assertTrue(all(old not in json.dumps(x, ensure_ascii=False) for x in staged(self.home)))
            self.assertEqual(reopened.cfg["learning_mode"], "RECORD_ONLY")
        finally:
            reopened.close()
        # Base.tearDown calls close again; Store.close is idempotent.

    def test_no_ag12_registration_does_not_bootstrap_a_suite(self):
        self.assertIsNone(self.r.store.state(KEY, None)[0])
        self.assertIsNone(self.r.store.state(KEY + "_DE", None)[0])
        self.turn("One ordinary message?", "An ordinary answer.")
        self.turn("Two ordinary messages?", "Another ordinary answer.")
        S.digest(self.r.store)
        self.assertEqual(S.stage_ttt(self.r.store, self.home)["candidates"], 1)
        self.assertIsNone(self.r.store.state(KEY, None)[0])
        self.assertIsNone(self.r.store.state(KEY + "_DE", None)[0])

    def test_damaged_registry_refuses_to_publish_new_export(self):
        en = GeneralityEval(self.r.store, lang="en")
        self.turn("One ordinary message?", "An ordinary answer.")
        self.turn("Two ordinary messages?", "Another ordinary answer.")
        S.digest(self.r.store)
        path = self.home / "exports/sleep-ttt-candidates.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("OLDER_UNTRUSTED_EXPORT\n")
        en.box.mutate(lambda st: st.update(holdout=[]))
        with self.assertRaisesRegex(ValueError, "AG12_HOLDOUT_INTEGRITY"):
            S.stage_ttt(self.r.store, self.home)
        self.assertEqual(path.read_text(), "OLDER_UNTRUSTED_EXPORT\n")


if __name__ == "__main__":
    unittest.main()
