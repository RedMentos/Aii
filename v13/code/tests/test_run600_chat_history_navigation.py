"""Run600: real SQLite/Runtime/Operator persistent chat navigation, no models."""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.operator import Operator


class ChatHistoryNavigation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.first = self.r.session
        self.second = self.op.run(":new")
        self.op.run(":open " + self.first)
        with self.r.store.tx() as db:
            for i in range(42):
                sid = self.first if i % 2 == 0 else self.second
                db.execute(
                    "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (sid, None, "user", "HISTORY_NEEDLE_%02d" % i,
                     "FINAL", "{}", float(i)))
            db.execute(
                "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                "VALUES (?,?,?,?,?,?,?)",
                (self.second, None, "user", "PERCENT%_literal", "FINAL", "{}", 43.))
            db.execute(
                "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                "VALUES (?,?,?,?,?,?,?)",
                (self.first, None, "user", "PERCENTabc_literal", "FINAL", "{}", 44.))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_cross_chat_search_cursor_covers_all_42_without_duplicates(self):
        page1 = json.loads(self.op.run(":search HISTORY_NEEDLE"))
        self.assertEqual(len(page1), 30)
        self.assertEqual(sorted((x["id"] for x in page1), reverse=True),
                         [x["id"] for x in page1])
        page2 = json.loads(self.op.run(":search HISTORY_NEEDLE --before %d" % page1[-1]["id"]))
        self.assertEqual(len(page2), 12)
        self.assertEqual(len({x["id"] for x in page1 + page2}), 42)
        self.assertEqual({x["session_id"] for x in page1 + page2},
                         {self.first, self.second})
        self.assertEqual(json.loads(self.op.run(
            ":search HISTORY_NEEDLE --before %d" % page2[-1]["id"])), [])

    def test_like_wildcards_are_literal_with_and_without_cursor(self):
        rows = json.loads(self.op.run(":search PERCENT%_literal"))
        self.assertEqual([x["text"] for x in rows], ["PERCENT%_literal"])
        after = json.loads(self.op.run(":search PERCENT%_literal --before %d" % (rows[0]["id"]+1)))
        self.assertEqual([x["text"] for x in after], ["PERCENT%_literal"])

    def test_invalid_cursors_fail_without_mutating_history(self):
        for cmd in (":search HISTORY_NEEDLE --before 0",
                    ":search HISTORY_NEEDLE --before -1",
                    ":search HISTORY_NEEDLE --before nope",
                    ":search HISTORY_NEEDLE --before 2 --before 3",
                    ":search --before 12"):
            with self.subTest(cmd=cmd), self.assertRaises(ValueError):
                self.op.run(cmd)
        self.assertEqual(len(json.loads(self.op.run(":search HISTORY_NEEDLE"))), 30)

    def test_legacy_search_and_current_export_remain_usable(self):
        rows = json.loads(self.op.run(":search HISTORY_NEEDLE_00"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_id"], self.first)
        self.assertIsInstance(rows[0]["id"], int)
        path = Path(self.op.run(":export chat"))
        self.assertEqual(path.name, self.first + ".json")
        self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 22)

    def test_named_chat_json_export_does_not_switch_active_chat(self):
        before = self.r.store.meta("last_session")
        path = Path(self.op.run(":export chat json " + self.second))
        self.assertEqual(path.name, self.second + ".json")
        rows = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 22)
        self.assertTrue(any(x["text"] == "PERCENT%_literal" for x in rows))
        self.assertEqual(self.r.session, self.first)
        self.assertEqual(self.r.store.meta("last_session"), before)

    def test_named_chat_markdown_export_does_not_switch_active_chat(self):
        path = Path(self.op.run(":export chat md " + self.second))
        self.assertEqual(path.name, self.second + ".md")
        md = path.read_text(encoding="utf-8")
        self.assertIn("PERCENT%_literal", md)
        self.assertNotIn("PERCENTabc_literal", md)
        self.assertEqual(self.r.session, self.first)

    def test_invalid_chat_id_and_format_do_not_create_export(self):
        for cmd in (":export chat yaml " + self.second,
                    ":export chat json chat_missing",
                    ":export chat json " + self.second + " extra"):
            with self.subTest(cmd=cmd), self.assertRaises(ValueError):
                self.op.run(cmd)
        self.assertEqual(list((self.home / "exports").glob("*")), [])

    def test_restart_preserves_active_chat_and_old_chat_export(self):
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.assertEqual(self.r.session, self.first)
        path = Path(self.op.run(":export chat json " + self.second))
        self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 22)
        self.assertEqual(self.r.session, self.first)


if __name__ == "__main__":
    unittest.main()
