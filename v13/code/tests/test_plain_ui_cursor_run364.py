"""Run364: plain Termux UI must not lose >8 outputs between render ticks.

Actual Runtime/Store SQLite, no model. The initial screen remains a bounded
history window; subsequent output is drained by a durable monotonic cursor.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.ui import visible_delta


class PlainCursorRun364(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.event = self.r.store.event(self.r.session, "run364 fixture")["event_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def add(self, count, prefix="out"):
        for i in range(count):
            self.r.store.message(self.r.session, self.event, "assistant",
                                 f"{prefix}-{i}", status="FINAL")

    def test_initial_window_then_burst_over_eight_drains_every_message_once(self):
        self.add(12, "old")
        seen = {}
        cursor, output = visible_delta(self.r.store, self.r.session, None, seen)
        self.assertEqual([part[1] for part in output], [f"old-{i}" for i in range(4, 12)])
        self.add(25, "burst")
        cursor, output = visible_delta(self.r.store, self.r.session, cursor, seen)
        self.assertEqual([part[1] for part in output], [f"burst-{i}" for i in range(25)])
        cursor, output = visible_delta(self.r.store, self.r.session, cursor, seen)
        self.assertEqual(output, [])

    def test_streaming_message_only_emits_suffix_and_preserves_prefix(self):
        seen = {}
        cursor, _ = visible_delta(self.r.store, self.r.session, None, seen)
        mid = self.r.store.message(self.r.session, self.event, "assistant", "hello", status="DRAFT")
        cursor, output = visible_delta(self.r.store, self.r.session, cursor, seen)
        self.assertEqual(output, [("assistant", "hello", True)])
        self.r.store.append_message(mid, " world")
        cursor, output = visible_delta(self.r.store, self.r.session, cursor, seen)
        self.assertEqual(output, [("assistant", " world", False)])
        self.r.store.finish_message(mid, "FINAL", {})
        cursor, output = visible_delta(self.r.store, self.r.session, cursor, seen)
        self.assertEqual(output, [])

    def test_cursor_paginates_bursts_and_seen_memory_stays_bounded(self):
        seen = {}
        cursor, _ = visible_delta(self.r.store, self.r.session, None, seen)
        self.add(120, "many")
        got = []
        for _ in range(10):
            cursor, output = visible_delta(self.r.store, self.r.session, cursor, seen, limit=17)
            got.extend(part[1] for part in output)
        self.assertEqual(got, [f"many-{i}" for i in range(120)])
        self.assertLessEqual(len(seen), 40)

    def test_new_session_can_reinitialize_without_reusing_old_seen_ids(self):
        seen = {}
        self.add(2, "first")
        cursor, output = visible_delta(self.r.store, self.r.session, None, seen)
        self.assertEqual(len(output), 2)
        session2 = self.r.store.new_session("run364 second")
        event2 = self.r.store.event(session2, "new session")["event_id"]
        self.r.store.message(session2, event2, "assistant", "new-session", status="FINAL")
        seen.clear()
        cursor, output = visible_delta(self.r.store, session2, None, seen)
        self.assertEqual(output, [("assistant", "new-session", True)])


if __name__ == "__main__":
    unittest.main()
