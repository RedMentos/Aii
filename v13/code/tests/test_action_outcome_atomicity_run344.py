"""Run344 RED-first: exact-once atomic C5 ActionOutcome persistence.

Production Runtime/Store SQLite, synthetic local text outcomes only.
No native inference, no automatic authority or World-JEPA promotion.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from v13.runtime import Runtime


class ActionOutcomeAtomicityRun344(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        e = self.r.store.event(self.r.session, "A local C5 action with one outcome")
        self.event_id = e["event_id"]
        self.aid = self.r.store.start_action(
            self.event_id, e["brain_generation_id"],
            forecast={"profile": {"role": "SOURCE_COPY"},
                      "input_chars": 34, "duration_median_s": 1.0},
        )
        self.actual = {"role": "SOURCE_COPY", "characters": 12,
                       "action_duration_s": 1.5, "model_generated": False}

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def row(self):
        return self.r.store.one("SELECT status,outcome FROM actions WHERE id=?",
                                (self.aid,))

    def packets(self):
        return [json.loads(r["payload"]) for r in self.r.store.rows(
            "SELECT payload FROM packets WHERE kind='ActionOutcome' AND event_id=?",
            (self.event_id,),
        )]

    def test_same_exact_replay_is_one_action_and_one_packet(self):
        self.r.store.finish_action(self.aid, "FINAL", self.actual)
        first = dict(self.row())
        packets = self.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0]["action_id"], self.aid)
        self.r.store.finish_action(self.aid, "FINAL", dict(self.actual))
        self.assertEqual(dict(self.row()), first)
        self.assertEqual(self.packets(), packets)
        self.assertEqual(self.r.store.integrity(True), [])

    def test_conflicting_status_and_payload_are_rejected_without_mutation(self):
        self.r.store.finish_action(self.aid, "FINAL", self.actual)
        original = dict(self.row())
        packets = self.packets()
        with self.assertRaises(ValueError):
            self.r.store.finish_action(self.aid, "ERROR", self.actual)
        with self.assertRaises(ValueError):
            self.r.store.finish_action(self.aid, "FINAL", self.actual | {"characters": 99})
        self.assertEqual(dict(self.row()), original)
        self.assertEqual(self.packets(), packets)

    def test_packet_insert_and_action_update_share_one_rollback_boundary(self):
        with self.r.store.tx() as c:
            c.execute("""CREATE TRIGGER run344_block BEFORE UPDATE OF status,outcome
                         ON actions BEGIN SELECT RAISE(ABORT,'RUN344_SQL_ABORT'); END""")
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.r.store.finish_action(self.aid, "FINAL", self.actual)
        finally:
            with self.r.store.tx() as c:
                c.execute("DROP TRIGGER run344_block")
        self.assertEqual(self.row()["status"], "DISPATCHED")
        self.assertIsNone(self.row()["outcome"])
        self.assertEqual(self.packets(), [])  # no orphan terminal packet
        self.r.store.finish_action(self.aid, "FINAL", self.actual)
        self.assertEqual(len(self.packets()), 1)

    def test_duplicate_concurrent_calls_are_serialized_exactly_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.r.store.finish_action(
                self.aid, "FINAL", self.actual), range(2)))
        self.assertEqual(self.row()["status"], "FINAL")
        self.assertEqual(len(self.packets()), 1)

    def test_exact_receipt_survives_restart(self):
        self.r.store.finish_action(self.aid, "FINAL", self.actual)
        first = dict(self.row())
        packets = self.packets()
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.store.finish_action(self.aid, "FINAL", self.actual)
        self.assertEqual(dict(self.row()), first)
        self.assertEqual(self.packets(), packets)

    def test_unknown_action_and_nonfinite_payload_cannot_create_packet(self):
        with self.assertRaises(Exception):
            self.r.store.finish_action("nonexistent-run344-action", "FINAL", self.actual)
        with self.assertRaises((TypeError, ValueError, OverflowError)):
            self.r.store.finish_action(self.aid, "FINAL",
                                       self.actual | {"action_duration_s": float("nan")})
        self.assertEqual(self.row()["status"], "DISPATCHED")
        self.assertIsNone(self.row()["outcome"])
        self.assertEqual(self.packets(), [])


if __name__ == "__main__":
    unittest.main()
