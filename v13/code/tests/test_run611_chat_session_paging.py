"""Run611 real SQLite/Runtime persistent chat list keyset paging tests."""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.operator import Operator


class ChatListPaging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.original = self.r.session
        self.last_session = self.r.store.meta("last_session")
        # 71 old/new chat rows with many identical timestamps. No model call.
        with self.r.store.tx() as c:
            for i in range(71):
                c.execute("INSERT INTO sessions(id,title,created) VALUES (?,?,?)",
                          ("chat-test-%03d" % i, "Chat %03d" % i,
                           2000000000.0 + i // 3))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_default_and_cursor_cover_all_72_with_timestamp_ties(self):
        p1 = json.loads(self.op.run(":chats"))
        self.assertEqual(len(p1), 50)
        p2 = json.loads(self.op.run(":chats --before " + p1[-1]["id"]))
        self.assertEqual(len(p2), 22)
        p3 = json.loads(self.op.run(":chats --before " + p2[-1]["id"]))
        self.assertEqual(p3, [])
        rows = p1 + p2
        self.assertEqual(len({r["id"] for r in rows}), 72)
        self.assertEqual(set(r["id"] for r in rows),
                         {self.original} | {"chat-test-%03d" % i for i in range(71)})
        self.assertEqual([(r["created"], r["id"]) for r in rows],
                         sorted(((r["created"], r["id"]) for r in rows), reverse=True))
        self.assertEqual(self.r.session, self.original)
        self.assertEqual(self.r.store.meta("last_session"), self.last_session)

    def test_explicit_legacy_all_preserves_full_listing_and_row_shape(self):
        rows = json.loads(self.op.run(":chats all"))
        self.assertEqual(len(rows), 72)
        self.assertTrue(all(set(r) == {"id", "title", "created"} for r in rows))
        self.assertEqual(rows[:50], json.loads(self.op.run(":chats")))

    def test_invalid_cursor_and_extra_args_fail_closed(self):
        for command in (":chats --before", ":chats --before nonexistent",
                        ":chats --before " + "x" * 5000,
                        ":chats --before chat-test-000 extra", ":chats all extra",
                        ":chats garbage", ":chats --before --before"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.op.run(command)
        self.assertEqual(self.r.session, self.original)
        self.assertEqual(self.r.store.meta("last_session"), self.last_session)

    def test_restart_keeps_paging_and_active_session(self):
        p1 = json.loads(self.op.run(":chats"))
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.assertEqual(self.r.session, self.original)
        p2 = json.loads(self.op.run(":chats --before " + p1[-1]["id"]))
        self.assertEqual(len(p2), 22)
        self.assertEqual(self.r.store.meta("last_session"), self.last_session)


if __name__ == "__main__":
    unittest.main()
