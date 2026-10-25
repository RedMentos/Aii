"""Run299 RED/GREEN: offline FastForward replay may not clobber live learning.

Production Runtime/Store SQLite; synthetic observed timing only. No models.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13 import fastforward as F


class FastForwardSleepCASRun299(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.f = F.FastForward(self.r.store)
        self.x = F.features("Question with numbers 20 and 40", "simple", "none")
        for i in range(12):
            e = self.r.store.event(self.r.session, f"sleep observation {i}")
            self.f.learn(e["event_id"], self.x, 1.0 + i * .05, "FINAL", 25 + i)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_live_learning_during_checkpoint_must_not_be_lost(self):
        captured = {}
        def live_update():
            if captured:
                return
            event = self.r.store.event(self.r.session, "new live outcome during sleep")
            self.f.learn(event["event_id"], self.x, 120.0, "FINAL", 400)
            captured["weights"] = self.f._load()[0]["w"]
            captured["version"] = self.f._load()[1]
        result = self.f.consolidate(epochs=1, lr=0.0, checkpoint=live_update)
        self.assertEqual(result["status"], "SKIPPED_STALE_LIVE_STATE")
        after, version = self.f._load()
        self.assertEqual(after["w"], captured["weights"])
        self.assertEqual(version, captured["version"])
        self.assertEqual(after.get("sleep_updates", 0), 0)
        self.assertEqual(after["n"], 13)
        self.assertEqual(len(after["replay"]), 13)

    def test_procedural_state_change_also_blocks_stale_sleep_candidate(self):
        captured = {}
        def live_procedure():
            if captured:
                return
            self.f.record_turn("live-procedure", "none", "FINAL", 1.0)
            captured["version"] = self.f._load()[1]
        result = self.f.consolidate(epochs=1, lr=0.0, checkpoint=live_procedure)
        self.assertEqual(result["status"], "SKIPPED_STALE_LIVE_STATE")
        state, version = self.f._load()
        self.assertEqual(version, captured["version"])
        self.assertIn("live-procedure", state["procs"])
        self.assertEqual(state.get("sleep_updates", 0), 0)

    def test_unchanged_version_keeps_valid_consolidation(self):
        before, version = self.f._load()
        result = self.f.consolidate(epochs=1, lr=0.0)
        self.assertEqual(result["status"], "KEPT")
        after, new_version = self.f._load()
        self.assertEqual(after["w"], before["w"])
        self.assertEqual(after["n"], before["n"])
        self.assertEqual(after["sleep_updates"], 1)
        self.assertEqual(new_version, version + 1)

    def test_too_few_replay_rows_still_skip(self):
        self.r.store.set_state(F.KEY, F.empty())
        result = self.f.consolidate()
        self.assertEqual(result["status"], "SKIPPED_TOO_FEW")


if __name__ == "__main__":
    unittest.main()
