"""Run420 RED-first: corrupt durable PredictionOutcome must not brick World restart.

No native models, no semantic-truth or learning promotion. Corrupt raw packets
must remain in SQLite while valid sibling actions can still recover.
"""
import tempfile
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime


class Run420WorldPacketRecoveryTests(unittest.TestCase):
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

    def insert_corrupt(self, event_id, raw):
        pid = "corrupt-" + str(time.time_ns())
        with self.r.store.tx() as c:
            c.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)",
                      (pid, "PredictionOutcome", event_id,
                       self.r.store.generation_id, raw, time.time()))
        return pid

    def action(self):
        event = self.r.store.event(self.r.session, "world recovery source")
        forecast = self.r.world.forecast(event, "SOURCE_COPY",
                                         native_prediction=False)
        aid = self.r.store.start_action(event["event_id"],
                                        self.r.store.generation_id,
                                        forecast=forecast)
        self.r.store.finish_action(aid, "FINAL",
                                   {"role": "SOURCE_COPY",
                                    "action_duration_s": 2.0})
        return event, aid

    def test_invalid_prediction_packet_does_not_brick_restart(self):
        event = self.r.store.event(self.r.session, "malformed world packet")
        pid = self.insert_corrupt(event["event_id"], "{not-json")
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 0)
        self.assertEqual(self.r.store.one("SELECT payload FROM packets WHERE id=?",
                                          (pid,))["payload"], "{not-json")
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 0)

    def test_invalid_prediction_packet_does_not_block_valid_action_recovery(self):
        event, aid = self.action()
        pid = self.insert_corrupt(event["event_id"], "{bad")
        self.restart()
        packets = self.r.store.rows(
            "SELECT payload FROM packets WHERE kind='PredictionOutcome' AND event_id=?",
            (event["event_id"],))
        self.assertEqual(len(packets), 2)
        self.assertEqual(self.r.store.one("SELECT payload FROM packets WHERE id=?",
                                          (pid,))["payload"], "{bad")
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)

    def test_valid_json_with_wrong_observation_shape_does_not_block_recovery(self):
        event, aid = self.action()
        pid = self.insert_corrupt(event["event_id"],
                                  '{"action_id":"' + aid + '","observation":"invalid"}')
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        self.assertIsNotNone(self.r.store.one("SELECT payload FROM packets WHERE id=?",
                                              (pid,)))
        self.assertEqual(len(self.r.store.rows(
            "SELECT payload FROM packets WHERE kind='PredictionOutcome' AND event_id=?",
            (event["event_id"],))), 2)


if __name__ == "__main__":
    unittest.main()
