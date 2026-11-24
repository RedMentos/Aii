"""AG6 must revalidate staged source refs before any trainer.fit call.

Real Store and authored counting trainer; no model weights or training.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation


class CountingTrainer:
    method = "counting-no-model"
    role = "C3_LANGUAGE"
    cfg = {}
    def __init__(self):
        self.calls = []
    def fit(self, items, base_generation, cancel=None, deadline=None):
        self.calls.append([x["memory_id"] for x in items])
        return {"artifact": None, "hash": None, "method": self.method, "metrics": {}}


class StagedSourceRecheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.s = self.r.store
        self.t = CountingTrainer()
        self.w = WeightConsolidation(self.s, self.r.cfg | {
            "learning_mode": "SHADOW_UPDATE"}, trainer=self.t)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _memory(self, name):
        event = self.s.event(self.r.session, "What is the name of " + name + "?")
        self.r.memory.feedback(event["event_id"], "fact", name)
        return event

    def _stage(self):
        batch = self.w.stage(require_replay_pass=False)
        self.assertEqual(batch["status"], "STAGED", batch)
        return self.w.batch(batch["batch_id"])

    def _revoke(self, ref):
        with self.s.tx() as conn:
            conn.execute("UPDATE sources SET deleted=1 WHERE id=?",
                         (ref["source_id"],))

    def test_revoked_single_staged_source_vetoes_fit(self):
        self._memory("Mira")
        batch = self._stage()
        self._revoke(batch["items"][0]["source_ref"])
        out = self.w.train(batch["id"])
        self.assertEqual(out["status"], "SOURCE_INVALID")
        self.assertEqual(self.t.calls, [])
        self.assertEqual(self.w.batch(batch["id"])["status"], "SOURCE_INVALID")

    def test_one_revoked_source_vetoes_whole_batch_not_subset(self):
        self._memory("Mira")
        self._memory("Lena")
        batch = self._stage()
        self.assertEqual(len(batch["items"]), 2)
        self._revoke(batch["items"][0]["source_ref"])
        out = self.w.train(batch["id"])
        self.assertEqual(out["status"], "SOURCE_INVALID")
        self.assertEqual(self.t.calls, [])
        # A later stage may use the surviving item, but the failed batch is
        # preserved with its original dataset hash and source set.
        newer = self.w.stage(require_replay_pass=False)
        self.assertEqual(newer["status"], "STAGED")
        self.assertNotEqual(newer["batch_id"], batch["id"])
        self.assertEqual(self.w.batch(batch["id"])["status"], "SOURCE_INVALID")

    def test_valid_staged_source_still_calls_trainer(self):
        self._memory("Mira")
        batch = self._stage()
        out = self.w.train(batch["id"])
        self.assertEqual(out["status"], "NO_TRAINER")
        self.assertEqual(len(self.t.calls), 1)
        self.assertEqual(len(self.t.calls[0]), 1)


if __name__ == "__main__":
    unittest.main()
