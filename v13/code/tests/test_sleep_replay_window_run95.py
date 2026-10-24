"""Run95: bounded Sleep A replay index must not starve newer source rows.

Real SQLite JOIN/ORDER/LIMIT exercised with the production ReplayQueue.sync.
No native models, no age promotion, no dream factual authority.
"""
import sqlite3
import unittest

from v13.sleep import MAX_ITEMS, ReplayQueue, default_policy, empty_schedule


class StoreStub:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE events (id TEXT PRIMARY KEY, session_id TEXT)")
        self.db.execute(
            "CREATE TABLE replay (id TEXT PRIMARY KEY, event_id TEXT, kind TEXT, "
            "priority REAL, status TEXT, created REAL)"
        )

    def insert(self, index, created=None):
        eid = "e%05d" % index
        rid = "r%05d" % index
        self.db.execute("INSERT INTO events VALUES (?, ?)", (eid, "session"))
        self.db.execute(
            "INSERT INTO replay VALUES (?, ?, ?, ?, ?, ?)",
            (rid, eid, "EPISODIC", 0.9, "SLEEP_QUEUED",
             float(index if created is None else created)),
        )
        return rid

    def rows(self, sql, params=()):
        return self.db.execute(sql, params).fetchall()

    def close(self):
        self.db.close()


class SleepReplayWindowRun95(unittest.TestCase):
    def setUp(self):
        self.store = StoreStub()
        self.queue = ReplayQueue(self.store)
        self.policy = default_policy()
        self.schedule = empty_schedule()

    def tearDown(self):
        self.store.close()

    def test_new_human_corrections_are_not_starved_after_capacity(self):
        for i in range(MAX_ITEMS):
            self.store.insert(i)
        added, overflow = self.queue.sync(self.schedule, self.policy)
        self.assertEqual(added, MAX_ITEMS)
        self.assertFalse(overflow)
        for i in range(MAX_ITEMS, MAX_ITEMS + 3):
            self.store.insert(i)
        added, overflow = self.queue.sync(self.schedule, self.policy)
        self.assertTrue(overflow)
        self.assertEqual(added, 3)
        for i in range(MAX_ITEMS, MAX_ITEMS + 3):
            rid = "r%05d" % i
            self.assertIn(rid, self.schedule["items"])
            self.assertIsNone(self.schedule["items"][rid]["retired"])
        self.assertNotIn("r00000", self.schedule["items"])
        self.assertLessEqual(len(self.schedule["items"]), MAX_ITEMS)
        due = {rid for rid, _ in self.queue.due(self.schedule, MAX_ITEMS + 20)}
        self.assertIn("r%05d" % (MAX_ITEMS + 2), due)

    def test_first_sync_over_capacity_keeps_newest_rows(self):
        for i in range(MAX_ITEMS + 3):
            self.store.insert(i)
        added, overflow = self.queue.sync(self.schedule, self.policy)
        self.assertTrue(overflow)
        self.assertEqual(added, MAX_ITEMS)
        self.assertEqual(len(self.schedule["items"]), MAX_ITEMS)
        self.assertNotIn("r00000", self.schedule["items"])
        self.assertIn("r%05d" % (MAX_ITEMS + 2), self.schedule["items"])

    def test_retired_in_window_and_protected_replay_history_are_preserved(self):
        for i in range(MAX_ITEMS):
            self.store.insert(i)
        self.queue.sync(self.schedule, self.policy)
        self.schedule["items"]["r01000"]["retired"] = "SUPERSEDED"
        self.schedule["items"]["r01000"]["reps"] = 3
        self.schedule["items"]["r02000"]["reps"] = 7
        for i in range(MAX_ITEMS, MAX_ITEMS + 4):
            self.store.insert(i)
        self.queue.sync(self.schedule, self.policy)
        self.assertEqual(self.schedule["items"]["r01000"]["retired"], "SUPERSEDED")
        self.assertEqual(self.schedule["items"]["r01000"]["reps"], 3)
        self.assertEqual(self.schedule["items"]["r02000"]["reps"], 7)
        self.assertLessEqual(len(self.schedule["items"]), MAX_ITEMS)
        # No replay rows, event provenance or retired histories were deleted.
        self.assertEqual(
            self.store.db.execute("SELECT COUNT(*) FROM replay").fetchone()[0],
            MAX_ITEMS + 4,
        )

    def test_equal_timestamps_use_deterministic_id_tiebreak(self):
        for i in range(MAX_ITEMS + 3):
            self.store.insert(i, created=100.)
        self.queue.sync(self.schedule, self.policy)
        self.assertNotIn("r00000", self.schedule["items"])
        self.assertIn("r%05d" % (MAX_ITEMS + 2), self.schedule["items"])
        self.assertEqual(len(self.schedule["items"]), MAX_ITEMS)


if __name__ == "__main__":
    unittest.main()
