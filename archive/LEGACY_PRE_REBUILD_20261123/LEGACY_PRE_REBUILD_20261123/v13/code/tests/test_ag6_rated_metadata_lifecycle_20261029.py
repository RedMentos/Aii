"""AG6 stale explicit rating / FINAL metadata must not authorize a staged weight candidate.

Real SQLite Store, authored FakeLora and counting trainer; no native model.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.inputs import record_rating
from v13.common import dumps
from v13.agi.weights import WeightConsolidation, KEY
from v13.lora_trainer import AdapterRegistry
from tests.test_lora_trainer import FakeLora
from tests.test_ag6_staged_source_revocation_20261029 import CountingTrainer


class RatedMetadataLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.s = self.r.store
        for n in range(9):
            e = self.s.event(self.r.session, "What is the project " + str(n) + "?")
            self.r.memory.feedback(e["event_id"], "fact", "Name" + str(n))
        event = self.s.event(self.r.session, "What is the approved budget?")
        self.event_id = event["event_id"]
        self.dep = self.s.source("Human supporting fact: 120 EUR.", "HUMAN_FACT")
        self.metadata = {"model_generated": True,
                         "context_source_refs": [event["source_ref"], self.dep]}
        self.s.message(self.r.session, self.event_id, "assistant",
                       "The budget is 120 EUR.", "FINAL", self.metadata)
        record_rating(self.s, self.event_id, 9, "EXPLICIT_NOTE")
        self.cfg = self.r.cfg | {"learning_mode": "SHADOW_UPDATE"}

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _stage(self, trainer):
        w = WeightConsolidation(self.s, self.cfg, trainer=trainer)
        result = w.stage(require_replay_pass=False, include_rated=True)
        self.assertEqual(result["status"], "STAGED", result)
        bid = result["batch_id"]
        self.assertEqual(len(w.batch(bid)["items"]), 10)
        return w, bid

    def _fake(self):
        model = self.home / "model.gguf"
        model.write_bytes(b"authored model fixture")
        return FakeLora(self.home, model, cand={
            "overall": .8, "unseen": .75, "forgetting": {"rate": 0.}})

    def _downgrade(self):
        record_rating(self.s, self.event_id, 2, "EXPLICIT_NOTE")

    def _change_final(self, *, text=None, metadata=None):
        with self.s.tx() as c:
            if text is not None:
                c.execute("UPDATE messages SET text=? WHERE event_id=? AND role='assistant' AND status='FINAL'",
                          (text, self.event_id))
            if metadata is not None:
                c.execute("UPDATE messages SET metadata=? WHERE event_id=? AND role='assistant' AND status='FINAL'",
                          (dumps(metadata), self.event_id))

    def test_explicit_rating_downgrade_after_stage_vetoes_fit(self):
        t = CountingTrainer()
        w, bid = self._stage(t)
        self._downgrade()
        self.assertEqual(w.train(bid)["status"], "SOURCE_INVALID")
        self.assertEqual(t.calls, [])

    def test_changed_final_text_after_stage_vetoes_fit(self):
        t = CountingTrainer()
        w, bid = self._stage(t)
        self._change_final(text="Mutated answer: 999 EUR.")
        self.assertEqual(w.train(bid)["status"], "SOURCE_INVALID")
        self.assertEqual(t.calls, [])

    def test_removed_declared_metadata_after_stage_vetoes_fit(self):
        t = CountingTrainer()
        w, bid = self._stage(t)
        self._change_final(metadata={"model_generated": True})
        self.assertEqual(w.train(bid)["status"], "SOURCE_INVALID")
        self.assertEqual(t.calls, [])

    def test_rating_downgrade_after_gate_vetoes_manual_approval(self):
        w, bid = self._stage(self._fake())
        gated = w.train_and_gate(bid)
        self.assertEqual(gated["status"], "PENDING_USER")
        rid = gated["request_id"]
        self._downgrade()
        with self.assertRaisesRegex(ValueError, "Quelle|Source"):
            w.approve(bid)
        self.assertEqual(w.batch(bid)["status"], "PENDING_USER")
        self.assertEqual(self.s.one("SELECT status FROM requests WHERE id=?", (rid,))["status"], "PENDING")
        self.assertEqual(self.s.state(KEY)[0]["consolidated"], [])
        self.assertNotIn("C3_LANGUAGE", AdapterRegistry(self.s).report()["active"])

    def test_new_ambiguous_final_after_stage_vetoes_fit(self):
        t = CountingTrainer()
        w, bid = self._stage(t)
        self.s.message(self.r.session, self.event_id, "assistant",
                       "Contradictory new FINAL.", "FINAL", self.metadata)
        self.assertEqual(w.train(bid)["status"], "SOURCE_INVALID")
        self.assertEqual(t.calls, [])

    def test_changed_final_text_after_gate_vetoes_approval(self):
        w, bid = self._stage(self._fake())
        gated = w.train_and_gate(bid)
        self.assertEqual(gated["status"], "PENDING_USER")
        self._change_final(text="Changed after gate.")
        with self.assertRaisesRegex(ValueError, "Quelle|Source"):
            w.approve(bid)
        self.assertEqual(w.batch(bid)["status"], "PENDING_USER")

    def test_unchanged_rated_answer_preserves_manual_approval(self):
        w, bid = self._stage(self._fake())
        self.assertEqual(w.train_and_gate(bid)["status"], "PENDING_USER")
        self.assertEqual(w.approve(bid)["status"], "APPROVED")
        self.assertIn("C3_LANGUAGE", AdapterRegistry(self.s).report()["active"])


if __name__ == "__main__":
    unittest.main()
