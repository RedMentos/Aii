"""Run345 RED-first: C5 ActionIntent, CorollaryCopy and action row share one commit.

Production Runtime/Store SQLite, synthetic local action intents; no native or tool execution.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from v13.runtime import Runtime


class ActionIntentAtomicityRun345(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.e = self.r.store.event(self.r.session, "Local pre-dispatch action lineage")
        self.forecast = {"profile": {"role": "SOURCE_COPY"},
                         "input_chars": 33, "duration_median_s": 1.0}

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def packets(self, kind):
        return [json.loads(x["payload"]) for x in self.r.store.rows(
            "SELECT payload FROM packets WHERE event_id=? AND kind=?",
            (self.e["event_id"], kind),
        )]

    def action_rows(self):
        return self.r.store.rows("SELECT * FROM actions WHERE event_id=?",
                                 (self.e["event_id"],))

    def start(self):
        return self.r.store.start_action(
            self.e["event_id"], self.e["brain_generation_id"],
            forecast=self.forecast,
        )

    def test_action_insert_abort_rolls_back_both_predispatch_packets(self):
        with self.r.store.tx() as c:
            c.execute("""CREATE TRIGGER run345_abort_action BEFORE INSERT ON actions
                         BEGIN SELECT RAISE(ABORT,'RUN345_ACTION_ABORT'); END""")
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.start()
        finally:
            with self.r.store.tx() as c:
                c.execute("DROP TRIGGER run345_abort_action")
        self.assertEqual(self.packets("ActionIntent"), [])
        self.assertEqual(self.packets("CorollaryCopy"), [])
        self.assertEqual(self.action_rows(), [])
        aid = self.start()
        self.assertEqual(self.action_rows()[0]["id"], aid)

    def test_corollary_insert_abort_does_not_leave_orphan_intent(self):
        with self.r.store.tx() as c:
            c.execute("""CREATE TRIGGER run345_abort_copy BEFORE INSERT ON packets
                         WHEN NEW.kind='CorollaryCopy'
                         BEGIN SELECT RAISE(ABORT,'RUN345_COPY_ABORT'); END""")
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.start()
        finally:
            with self.r.store.tx() as c:
                c.execute("DROP TRIGGER run345_abort_copy")
        self.assertEqual(self.packets("ActionIntent"), [])
        self.assertEqual(self.packets("CorollaryCopy"), [])
        self.assertEqual(self.action_rows(), [])

    def test_successful_start_has_exact_three_way_source_bound_lineage(self):
        aid = self.start()
        action = self.action_rows()[0]
        intent = self.packets("ActionIntent")[0]
        copy = self.packets("CorollaryCopy")[0]
        self.assertEqual(action["id"], aid)
        self.assertEqual(action["status"], "DISPATCHED")
        self.assertIsNone(action["outcome"])
        self.assertEqual(intent["action_id"], aid)
        self.assertEqual(copy["action_id"], aid)
        self.assertEqual(copy["packet_id"], action["corollary_id"])
        self.assertEqual(copy["expected"], json.loads(action["expected"]))
        self.assertEqual(intent["event_id"], self.e["event_id"])
        self.assertEqual(copy["event_id"], self.e["event_id"])
        self.assertEqual(intent["brain_generation_id"], self.e["brain_generation_id"])
        self.assertEqual(copy["brain_generation_id"], self.e["brain_generation_id"])
        self.assertEqual(self.r.store.integrity(True), [])

    def test_unknown_event_or_mismatched_generation_creates_no_orphan(self):
        with self.assertRaises(Exception):
            self.r.store.start_action("evt_missing_run345", self.e["brain_generation_id"],
                                      forecast=self.forecast)
        with self.assertRaises(ValueError):
            self.r.store.start_action(self.e["event_id"], "gen_wrong_run345",
                                      forecast=self.forecast)
        self.assertEqual(self.packets("ActionIntent"), [])
        self.assertEqual(self.packets("CorollaryCopy"), [])
        self.assertEqual(self.action_rows(), [])

    def test_two_concurrent_actions_keep_distinct_corollary_bindings(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            aids = list(pool.map(lambda _: self.start(), range(2)))
        self.assertEqual(len(set(aids)), 2)
        self.assertEqual({r["id"] for r in self.action_rows()}, set(aids))
        self.assertEqual({p["action_id"] for p in self.packets("ActionIntent")}, set(aids))
        self.assertEqual({p["action_id"] for p in self.packets("CorollaryCopy")}, set(aids))
        self.assertEqual(self.r.store.integrity(True), [])

    def test_start_lineage_survives_restart_without_reconstruction(self):
        aid = self.start()
        intent = self.packets("ActionIntent")
        copy = self.packets("CorollaryCopy")
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(self.packets("ActionIntent"), intent)
        self.assertEqual(self.packets("CorollaryCopy"), copy)
        self.assertEqual(self.action_rows()[0]["id"], aid)


if __name__ == "__main__":
    unittest.main()
