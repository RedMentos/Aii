"""Run343 RED-first: per-action WorldState recovery after a partial crash.

Real Runtime/Store SQLite, synthetic local text action outcomes, no native model.
No World/JEPA gate promotion.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime


class WorldMultiActionRecoveryRun343(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.e = self.r.store.event(self.r.session, "Two separately completed local actions")
        self.aids = []
        for i in range(2):
            forecast = {
                "profile": {"role": "SOURCE_COPY"},
                "input_chars": 46,
                "resource_state": "NORMAL",
                "duration_median_s": 1.0,
            }
            aid = self.r.store.start_action(
                self.e["event_id"], self.e["brain_generation_id"], forecast=forecast
            )
            self.r.store.finish_action(aid, "FINAL", {
                "role": "SOURCE_COPY",
                "action_duration_s": 1.0 + i,
                "characters": 10 + i,
            })
            self.aids.append(aid)

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def packets(self):
        rows = self.r.store.rows(
            "SELECT payload FROM packets WHERE event_id=? AND kind='PredictionOutcome'",
            (self.e["event_id"],),
        )
        return [json.loads(row["payload"]) for row in rows]

    def test_partial_crash_recovers_second_action_even_if_first_has_packet(self):
        self.assertEqual(self.r.world.observe(self.aids[0])["status"], "FINAL")
        self.assertEqual(len(self.packets()), 1)
        self.r.close()
        self.r = Runtime(self.home)  # real startup WorldState.recover()
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual({p["action_id"] for p in self.packets()}, set(self.aids))
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 2)
        self.assertEqual(self.r.store.integrity(True), [])

    def test_two_observed_actions_same_event_are_counted_separately(self):
        for aid in self.aids:
            self.assertEqual(self.r.world.observe(aid)["status"], "FINAL")
        self.assertEqual(len(self.packets()), 2)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 2)

    def test_repeated_recovery_and_observe_are_idempotent(self):
        self.r.world.observe(self.aids[0])
        self.r.world.recover()
        self.r.world.recover()
        self.r.world.observe(self.aids[1])
        self.assertEqual(len(self.packets()), 2)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 2)
        self.assertEqual(self.r.store.integrity(True), [])

    def test_unfinished_second_action_never_becomes_a_fabricated_outcome(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE actions SET outcome=NULL,status='DISPATCHED' WHERE id=?",
                      (self.aids[1],))
        self.r.world.observe(self.aids[0])
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual({p["action_id"] for p in self.packets()}, {self.aids[0]})
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)

    def test_two_distinct_events_remain_two_observed_actions(self):
        self.r.world.observe(self.aids[0])
        e2 = self.r.store.event(self.r.session, "Separate user event")
        aid = self.r.store.start_action(
            e2["event_id"], e2["brain_generation_id"],
            forecast={"profile": {"role": "SOURCE_COPY"},
                      "input_chars": 19, "duration_median_s": 1.0},
        )
        self.r.store.finish_action(aid, "FINAL", {
            "role": "SOURCE_COPY", "action_duration_s": 1.2, "characters": 5
        })
        self.r.world.observe(aid)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 2)


if __name__ == "__main__":
    unittest.main()
