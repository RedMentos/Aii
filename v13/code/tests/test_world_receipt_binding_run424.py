"""Run424 RED-first: syntactically valid forged F4 receipts must not become observed truth."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime


class Run424WorldReceiptBinding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.addCleanup(self._close)

    def _close(self):
        if self.r is not None:
            self.r.close()

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)

    def insert_forgery(self, event, aid, observed):
        raw = json.dumps({
            "event_id": event["event_id"], "action_id": aid,
            "producer_component": "F4_WORLD",
            "brain_generation_id": self.r.store.generation_id,
            "observation": {
                "action_id": aid, "status": "FINAL",
                "self_caused": True, "observed": observed,
                "scored": False, "semantic_success": None,
                "causal_claim": False, "external_world_observation": False
            }
        }, sort_keys=True)
        pid = "forged-" + str(time.time_ns())
        with self.r.store.tx() as c:
            c.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)",
                      (pid, "PredictionOutcome", event["event_id"],
                       self.r.store.generation_id, raw, time.time()))
        return pid, raw

    def action(self):
        event = self.r.store.event(self.r.session, "run424 actual source")
        forecast = self.r.world.forecast(event, "SOURCE_COPY",
                                         native_prediction=False)
        aid = self.r.store.start_action(event["event_id"],
                                        self.r.store.generation_id,
                                        forecast=forecast)
        self.r.store.finish_action(aid, "FINAL",
                                   {"role": "SOURCE_COPY", "action_duration_s": 2.0})
        return event, aid

    def test_forged_unknown_action_never_counts_as_observed(self):
        event = self.r.store.event(self.r.session, "forged only")
        pid, raw = self.insert_forgery(
            event, "nonexistent-action",
            {"role": "SOURCE_COPY", "action_duration_s": 1.0})
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 0)
        self.assertEqual(self.r.store.one("SELECT payload FROM packets WHERE id=?",
                                          (pid,))["payload"], raw)
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 0)

    def test_forged_existing_action_does_not_suppress_authoritative_recovery(self):
        event, aid = self.action()
        pid, raw = self.insert_forgery(
            event, aid, {"role": "SOURCE_COPY", "action_duration_s": 999.0})
        self.restart()
        state = self.r.world.world_state()
        self.assertEqual(state["observed_action_count"], 1)
        self.assertEqual(state["recent"][0]["observed"]["action_duration_s"], 2.0)
        self.assertEqual(len(self.r.store.rows(
            "SELECT id FROM packets WHERE event_id=? AND kind='PredictionOutcome'",
            (event["event_id"],))), 2)
        self.assertEqual(self.r.store.one("SELECT payload FROM packets WHERE id=?",
                                          (pid,))["payload"], raw)
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)

    def test_legitimate_receipt_still_deduplicates_after_restart(self):
        event, aid = self.action()
        original = self.r.world.observe(aid)
        self.assertEqual(original["observed"]["action_duration_s"], 2.0)
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        self.assertEqual(len(self.r.store.rows(
            "SELECT id FROM packets WHERE event_id=? AND kind='PredictionOutcome'",
            (event["event_id"],))), 1)


if __name__ == "__main__":
    unittest.main()
