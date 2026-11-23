"""AG6 manual approval must not activate weights trained from a revoked source.

Real SQLite request/adapter journal, authored FakeLora fixture; no native model.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation, KEY
from v13.lora_trainer import AdapterRegistry
from tests.test_lora_trainer import FakeLora


class ApprovalSourceRecheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.s = self.r.store
        model = self.home / "model.gguf"
        model.write_bytes(b"authored model fixture")
        event = self.s.event(self.r.session, "What is the project name?")
        self.r.memory.feedback(event["event_id"], "fact", "Mira")
        cfg = self.r.cfg | {"learning_mode": "SHADOW_UPDATE"}
        self.w = WeightConsolidation(
            self.s, cfg,
            trainer=FakeLora(self.home, model, cand={
                "overall": .8, "unseen": .75, "forgetting": {"rate": 0.}}))
        self.bid = self.w.stage(require_replay_pass=False)["batch_id"]
        result = self.w.train_and_gate(self.bid)
        self.assertEqual(result["status"], "PENDING_USER")
        self.rid = result["request_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _pending_unchanged(self):
        self.assertEqual(self.w.batch(self.bid)["status"], "PENDING_USER")
        self.assertEqual(self.s.one(
            "SELECT status FROM requests WHERE id=?", (self.rid,))["status"],
            "PENDING")
        self.assertEqual(self.s.state(KEY)[0]["consolidated"], [])
        self.assertNotIn("C3_LANGUAGE",
                         AdapterRegistry(self.s).report()["active"])

    def test_revoked_source_blocks_manual_approval_without_side_effects(self):
        ref = self.w.batch(self.bid)["items"][0]["source_ref"]
        with self.s.tx() as conn:
            conn.execute("UPDATE sources SET deleted=1 WHERE id=?",
                         (ref["source_id"],))
        with self.assertRaisesRegex(ValueError, "Quelle|Source"):
            self.w.approve(self.bid)
        self._pending_unchanged()

    def test_mutated_staged_source_hash_blocks_manual_approval(self):
        def mutate(st):
            st["batches"][self.bid]["items"][0]["source_ref"]["sha256"] = "0" * 64
        self.w.box.mutate(mutate)
        with self.assertRaisesRegex(ValueError, "Quelle|Source"):
            self.w.approve(self.bid)
        self._pending_unchanged()

    def test_valid_source_keeps_existing_explicit_approval(self):
        self.assertEqual(self.w.approve(self.bid)["status"], "APPROVED")
        self.assertEqual(self.s.one(
            "SELECT status FROM requests WHERE id=?", (self.rid,))["status"],
            "APPROVED")
        self.assertIn("C3_LANGUAGE", AdapterRegistry(self.s).report()["active"])


if __name__ == "__main__":
    unittest.main()
