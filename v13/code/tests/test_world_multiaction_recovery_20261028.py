"""Synthetic Store/Runtime regression: multiple actions of one event recover independently.

This exercises real SQLite/packet persistence, not model or Redmi inference.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime


class WorldMultiActionRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def pair(self):
        r = self.r
        event = r.store.event(r.session, "Two local text actions, one authoritative event")
        forecast = r.world.forecast(event, "C3_LANGUAGE", native_prediction=False)
        actions = []
        for seconds in (2.0, 3.0):
            aid = r.store.start_action(event["event_id"], r.store.generation_id, forecast=forecast)
            r.store.finish_action(aid, "FINAL", {
                "role": "C3_LANGUAGE", "action_duration_s": seconds,
                "model_generated": False,
            })
            actions.append(aid)
        self.assertNotEqual(actions[0], actions[1])
        return event, actions

    def receipts(self, event_id):
        rows = self.r.store.rows(
            "SELECT payload FROM packets WHERE kind='PredictionOutcome' AND event_id=?",
            (event_id,),
        )
        import json
        return [json.loads(row["payload"])["action_id"] for row in rows]

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)

    def test_two_observed_actions_same_event_count_as_two_actions(self):
        event, (first, second) = self.pair()
        self.r.world.observe(first)
        self.r.world.observe(second)
        state = self.r.world.world_state()
        self.assertEqual(state["observed_action_count"], 2)
        self.assertEqual(set(self.receipts(event["event_id"])), {first, second})
        self.assertEqual(
            {row["action_id"] for row in state["recent"]}, {first, second}
        )

    def test_restart_recovers_missing_second_action_receipt(self):
        event, (first, second) = self.pair()
        self.r.world.observe(first)
        self.assertEqual(self.receipts(event["event_id"]), [first])
        self.restart()
        self.assertEqual(set(self.receipts(event["event_id"])), {first, second})
        state = self.r.world.world_state()
        self.assertEqual(state["observed_action_count"], 2)
        self.assertEqual({row["action_id"] for row in state["recent"]}, {first, second})
        self.restart()
        self.assertEqual(len(self.receipts(event["event_id"])), 2)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 2)

    def test_restart_recovers_missing_first_action_receipt(self):
        event, (first, second) = self.pair()
        self.r.world.observe(second)
        self.assertEqual(self.receipts(event["event_id"]), [second])
        self.restart()
        self.assertEqual(set(self.receipts(event["event_id"])), {first, second})
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 2)

    def test_single_action_count_unchanged(self):
        event = self.r.store.event(self.r.session, "Single local action")
        forecast = self.r.world.forecast(event, "C3_LANGUAGE", native_prediction=False)
        aid = self.r.store.start_action(event["event_id"], self.r.store.generation_id, forecast=forecast)
        self.r.store.finish_action(aid, "FINAL", {
            "role": "C3_LANGUAGE", "action_duration_s": 1.0,
        })
        self.r.world.observe(aid)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        self.restart()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)


if __name__ == "__main__":
    unittest.main()
