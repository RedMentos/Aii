"""Run594: actual SQLite/Operator complete, atomic, local chat export."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.operator import Operator
from v13.runtime import Runtime


class ChatExportStream(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def insert(self, count, prefix="ROW", session=None):
        session = session or self.r.session
        with self.r.store.tx() as db:
            db.executemany(
                "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                "VALUES (?,?,?,?,?,?,?)",
                [(session, None, "user", f"{prefix}-{i:04d}", "FINAL", "{}", 0.)
                 for i in range(count)])

    def test_full_json_export_is_not_limited_by_context_history(self):
        self.insert(1205)
        with patch.object(self.r.store, "history", side_effect=AssertionError("history truncates")):
            path = Path(self.op.run(":export chat json"))
        rows = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 1205)
        self.assertEqual(rows[0]["text"], "ROW-0000")
        self.assertEqual(rows[-1]["text"], "ROW-1204")
        self.assertEqual([r["id"] for r in rows], sorted(r["id"] for r in rows))
        self.assertEqual(path.parent, self.home / "exports")

    def test_markdown_and_json_keep_separate_sessions(self):
        a = self.r.session
        self.insert(2, prefix="ÄLTER")
        b = self.op.run(":new")
        self.insert(3, prefix="NEU")
        md = Path(self.op.run(":export chat md")).read_text(encoding="utf-8")
        self.assertIn("NEU-0002", md)
        self.assertNotIn("ÄLTER", md)
        self.op.run(":open " + a)
        rows = json.loads(Path(self.op.run(":export chat")).read_text(encoding="utf-8"))
        self.assertEqual([r["text"] for r in rows], ["ÄLTER-0000", "ÄLTER-0001"])
        self.assertNotEqual(a, b)

    def test_midstream_failure_preserves_existing_export(self):
        self.insert(300)
        path = Path(self.op.run(":export chat json"))
        original = path.read_bytes()
        self.insert(1, prefix="AFTER")
        real_rows = self.r.store.rows
        calls = 0
        def fail_second_page(sql, args=()):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("simulated SQLite read failure")
            return real_rows(sql, args)
        with patch.object(self.r.store, "rows", side_effect=fail_second_page):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                self.op.run(":export chat json")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(path.parent.glob(".pending-chat-*")), [])

    def test_high_water_excludes_append_during_export(self):
        self.insert(300)
        real_rows = self.r.store.rows
        calls = 0
        def append_once(sql, args=()):
            nonlocal calls
            result = real_rows(sql, args)
            calls += 1
            if calls == 1:
                self.insert(1, prefix="LATE")
            return result
        with patch.object(self.r.store, "rows", side_effect=append_once):
            rows = json.loads(Path(self.op.run(":export chat json")).read_text())
        self.assertEqual(len(rows), 300)
        self.assertNotIn("LATE-0000", [r["text"] for r in rows])
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE session_id=?",
            (self.r.session,))["n"], 301)

    def test_imported_unsafe_session_id_cannot_escape_export_directory(self):
        sid = "../escape-session"
        with self.r.store.tx() as db:
            db.execute("INSERT INTO sessions VALUES (?,?,?)", (sid, "imported", 0.))
        self.r.session = sid
        self.insert(1, session=sid)
        path = Path(self.op.run(":export chat json"))
        self.assertEqual(path.parent, self.home / "exports")
        self.assertTrue(path.name.startswith("chat-"))
        self.assertEqual(len(json.loads(path.read_text())), 1)
        self.assertFalse((self.home / "escape-session.json").exists())

    def test_invalid_export_arguments_rejected(self):
        with self.assertRaises(ValueError):
            self.op.run(":export chat json unexpected")
        with self.assertRaises(ValueError):
            self.op.run(":export chat xml")


if __name__ == "__main__":
    unittest.main()
