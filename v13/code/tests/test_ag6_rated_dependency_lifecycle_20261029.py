"""AG6 rated-answer declared dependency must remain valid until fit and approval.

Real SQLite Store and authored FakeLora/counting trainer only. No native weights.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.inputs import record_rating
from v13.agi.weights import WeightConsolidation, KEY
from v13.lora_trainer import AdapterRegistry
from tests.test_lora_trainer import FakeLora
from tests.test_ag6_staged_source_revocation_20261029 import CountingTrainer


class RatedDependencyLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.s = self.r.store
        for n in range(9):
            event = self.s.event(self.r.session, "Who owns project " + str(n) + "?")
            self.r.memory.feedback(event["event_id"], "fact", "Human" + str(n))
        event = self.s.event(self.r.session, "What is the approved budget?")
        self.dependency = self.s.source("Supporting human context: budget is 120 EUR.", "HUMAN_FACT")
        self.s.message(self.r.session, event["event_id"], "assistant",
                       "The budget is 120 EUR.", "FINAL",
                       {"model_generated": True,
                        "context_source_refs": [event["source_ref"], self.dependency]})
        record_rating(self.s, event["event_id"], 9, "EXPLICIT_NOTE")
        self.rated_id = "rating:" + event["event_id"]
        self.cfg = self.r.cfg | {"learning_mode": "SHADOW_UPDATE"}

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _stage(self, trainer):
        w = WeightConsolidation(self.s, self.cfg, trainer=trainer)
        result = w.stage(require_replay_pass=False, include_rated=True)
        self.assertEqual(result["status"], "STAGED", result)
        batch = w.batch(result["batch_id"])
        self.assertEqual(len(batch["items"]), 10)
        self.assertEqual(sum(i["memory_id"] == self.rated_id for i in batch["items"]), 1)
        return w, batch["id"]

    def _revoke(self):
        with self.s.tx() as conn:
            conn.execute("UPDATE sources SET deleted=1 WHERE id=?",
                         (self.dependency["source_id"],))

    def _fake_lora(self):
        model = self.home / "model.gguf"
        model.write_bytes(b"authored model fixture")
        return FakeLora(self.home, model, cand={
            "overall": .8, "unseen": .75, "forgetting": {"rate": 0.}})

    def test_supporting_source_revoked_after_stage_vetoes_fit(self):
        trainer = CountingTrainer()
        w, bid = self._stage(trainer)
        self._revoke()
        result = w.train(bid)
        self.assertEqual(result["status"], "SOURCE_INVALID")
        self.assertEqual(trainer.calls, [])

    def test_supporting_source_revoked_after_gate_vetoes_approval(self):
        w, bid = self._stage(self._fake_lora())
        gated = w.train_and_gate(bid)
        self.assertEqual(gated["status"], "PENDING_USER")
        rid = gated["request_id"]
        self._revoke()
        with self.assertRaisesRegex(ValueError, "Quelle|Source"):
            w.approve(bid)
        self.assertEqual(w.batch(bid)["status"], "PENDING_USER")
        self.assertEqual(self.s.one("SELECT status FROM requests WHERE id=?", (rid,))["status"], "PENDING")
        self.assertEqual(self.s.state(KEY)[0]["consolidated"], [])
        self.assertNotIn("C3_LANGUAGE", AdapterRegistry(self.s).report()["active"])

    def test_valid_declared_dependency_preserves_explicit_approval(self):
        w, bid = self._stage(self._fake_lora())
        gated = w.train_and_gate(bid)
        self.assertEqual(gated["status"], "PENDING_USER")
        self.assertEqual(w.approve(bid)["status"], "APPROVED")
        self.assertIn("C3_LANGUAGE", AdapterRegistry(self.s).report()["active"])

    def test_removed_dependency_snapshot_vetoes_fit(self):
        trainer = CountingTrainer()
        w, bid = self._stage(trainer)
        def corrupt(st):
            rated = next(i for i in st["batches"][bid]["items"]
                         if i["memory_id"] == self.rated_id)
            rated.pop("source_dependencies")
        w.box.mutate(corrupt)
        self.assertEqual(w.train(bid)["status"], "SOURCE_INVALID")
        self.assertEqual(trainer.calls, [])

    def test_removed_dependency_snapshot_vetoes_approval(self):
        w, bid = self._stage(self._fake_lora())
        self.assertEqual(w.train_and_gate(bid)["status"], "PENDING_USER")
        def corrupt(st):
            rated = next(i for i in st["batches"][bid]["items"]
                         if i["memory_id"] == self.rated_id)
            rated.pop("source_dependencies")
        w.box.mutate(corrupt)
        with self.assertRaisesRegex(ValueError, "Quelle|Source"):
            w.approve(bid)
        self.assertEqual(w.batch(bid)["status"], "PENDING_USER")

    def test_staged_rated_item_preserves_declared_dependency(self):
        w, bid = self._stage(CountingTrainer())
        rated = next(i for i in w.batch(bid)["items"] if i["memory_id"] == self.rated_id)
        self.assertEqual(rated["source_dependencies"][-1], self.dependency)


if __name__ == "__main__":
    unittest.main()
