"""Run431 RED-first: corrupt recent packets must not evict valid F4 receipts.

These are software/SQLite restart tests, never native or Redmi evidence.
"""
import tempfile
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime


class Run431WorldValidRecentWindow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.addCleanup(self.close)

    def close(self):
        if self.r is not None:
            self.r.close()
            self.r = None

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)

    def action_with_receipt(self):
        event = self.r.store.event(self.r.session, "run431 legitimate digital source")
        forecast = self.r.world.forecast(event, "SOURCE_COPY",
                                         native_prediction=False)
        aid = self.r.store.start_action(event["event_id"],
                                        self.r.store.generation_id,
                                        forecast=forecast)
        self.r.store.finish_action(aid, "FINAL",
                                   {"role": "SOURCE_COPY", "action_duration_s": 2.0})
        receipt = self.r.world.observe(aid)
        self.assertIsNotNone(receipt)
        return event, aid

    def test_140_newer_corrupt_receipts_cannot_hide_older_valid_recent(self):
        event, aid = self.action_with_receipt()
        with self.r.store.tx() as c:
            for n in range(140):
                c.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)",
                          ("run431-corrupt-" + str(n), "PredictionOutcome",
                           event["event_id"], self.r.store.generation_id,
                           "{malformed-json", time.time() + n + 10))
        self.restart()
        state = self.r.world.world_state()
        self.assertEqual(state["observed_action_count"], 1)
        self.assertEqual(len(state["recent"]), 1)
        self.assertEqual(state["recent"][0]["action_id"], aid)
        self.assertEqual(state["recent"][0]["observed"]["action_duration_s"], 2.0)
        self.assertEqual(state["last_event_id"], event["event_id"])
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE payload='{malformed-json'")["n"], 140)
        self.restart()
        self.assertEqual(len(self.r.world.world_state()["recent"]), 1)

    def test_refresh_drops_stale_state_when_last_receipt_corrupts(self):
        event, aid = self.action_with_receipt()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET payload=? WHERE kind='PredictionOutcome' AND event_id=?",
                      ("{corrupt-after-materialization", event["event_id"]))
        self.r.world._refresh(self.r.session)
        state = self.r.world.world_state()
        self.assertEqual(state["observed_action_count"], 0)
        self.assertEqual(state["recent"], [])
        self.assertEqual(state["mode"], "NO_OBSERVATIONS")
        self.assertIsNone(state.get("last_event_id"))
        self.assertEqual(self.r.store.one(
            "SELECT payload FROM packets WHERE kind='PredictionOutcome' AND event_id=?",
            (event["event_id"],))["payload"], "{corrupt-after-materialization")


if __name__ == "__main__":
    unittest.main()
