"""Run117BZ source-verified Sleep digest backlog paging; real SQLite, no native model."""
from pathlib import Path
import tempfile
import unittest

from v13.config import initialize
from v13.store import Store
from v13.history import native_history
from v13 import sleep_offline as S


class SleepBacklog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def turn(self, i, status="FINAL"):
        e = self.store.event(self.session, f"BACKLOG_SOURCE_{i:03d}")
        mid = self.store.message(
            self.session, e["event_id"], "assistant",
            f"BACKLOG_ANSWER_{i:03d}", status,
            {"direct_source_copy": True})
        return e, mid

    def entries(self):
        state, _ = self.store.state(S.KEY, None)
        return state["sessions"][self.session]

    def test_seventy_turns_are_caught_up_oldest_first_without_loss(self):
        for i in range(70):
            self.turn(i)
        first = S.digest(self.store)
        self.assertEqual(first["turns"], 64)
        self.assertEqual(first["backlog_sessions"], 1)
        d = self.entries()
        self.assertEqual(len(d["entries"]), 64)
        self.assertEqual(d["entries"][0]["user"], "BACKLOG_SOURCE_000")
        self.assertEqual(d["entries"][-1]["user"], "BACKLOG_SOURCE_063")
        second = S.digest(self.store)
        self.assertEqual(second["turns"], 6)
        self.assertEqual(second["backlog_sessions"], 0)
        d = self.entries()
        self.assertEqual(len(d["entries"]), 70)
        self.assertEqual(d["entries"][-1]["user"], "BACKLOG_SOURCE_069")
        self.assertEqual(S.digest(self.store)["turns"], 0)
        self.assertEqual(len({e["msg"] for e in d["entries"]}), 70)

    def test_odd_page_boundary_and_revoked_source_never_reenter_digest(self):
        first, _ = self.turn(0)
        self.store.message(self.session, first["event_id"], "system",
                           "synthetic extra row", "FINAL", {})
        for i in range(1, 70):
            self.turn(i)
        with self.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (first["source_ref"]["source_id"],))
        a = S.digest(self.store)
        self.assertEqual(a["turns"], 62)  # 63 complete pairs in first 128 rows, one revoked
        self.assertEqual(a["backlog_sessions"], 1)
        b = S.digest(self.store)
        self.assertEqual(b["turns"], 7)
        d = self.entries()
        self.assertEqual(len(d["entries"]), 69)
        self.assertNotIn("BACKLOG_SOURCE_000", [e["user"] for e in d["entries"]])
        self.assertEqual(d["entries"][0]["user"], "BACKLOG_SOURCE_001")
        self.assertEqual(d["entries"][-1]["user"], "BACKLOG_SOURCE_069")

    def test_unfinished_answer_blocks_cursor_until_final(self):
        self.turn(0)
        _, pending = self.turn(1, status="DRAFT")
        self.turn(2)
        first = S.digest(self.store)
        self.assertEqual(first["turns"], 1)
        self.assertEqual(first["backlog_sessions"], 1)
        self.assertEqual(self.entries()["entries"][0]["user"], "BACKLOG_SOURCE_000")
        self.store.finish_message(pending, "FINAL", {"direct_source_copy": True})
        second = S.digest(self.store)
        self.assertEqual(second["turns"], 2)
        self.assertEqual([e["user"] for e in self.entries()["entries"]],
                         [f"BACKLOG_SOURCE_{i:03d}" for i in range(3)])

    def test_forward_history_cursor_is_typed_and_source_valid(self):
        e, mid = self.turn(0)
        with self.assertRaisesRegex(ValueError, "INVALID_HISTORY_CURSOR_RED"):
            native_history(self.store, self.session, "", 64, after_id=True)
        rows, _ = native_history(self.store, self.session, "", 64, after_id=0)
        self.assertEqual([r["role"] for r in rows], ["user", "assistant"])
        rows, _ = native_history(self.store, self.session, "", 64, after_id=mid)
        self.assertEqual(rows, [])
        with self.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (e["source_ref"]["source_id"],))
        rows, _ = native_history(self.store, self.session, "", 64, after_id=0)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
