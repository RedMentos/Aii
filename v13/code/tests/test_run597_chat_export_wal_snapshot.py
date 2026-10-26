"""Run597: SQLite WAL read snapshot stays coherent during live Store writes."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import chat_export as CE


class ChatExportWalSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.sid = self.r.session
        with self.r.store.tx() as db:
            db.executemany(
                "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                "VALUES (?,?,?,?,?,?,?)",
                [(self.sid, None, "user", f"ORIGINAL-{i}", "FINAL", "{}", 0.)
                 for i in range(5)])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_update_delete_and_append_after_first_page_do_not_change_snapshot(self):
        real = CE._page
        writes = []
        def mutate_after_first(conn, session, cursor, bound, size):
            page = real(conn, session, cursor, bound, size)
            if not writes:
                with self.r.store.tx() as db:
                    db.execute("UPDATE messages SET text='MUTATED',status='ERROR' "
                               "WHERE session_id=? AND text='ORIGINAL-3'", (self.sid,))
                    db.execute("DELETE FROM messages WHERE session_id=? AND text='ORIGINAL-4'",
                               (self.sid,))
                    db.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                               "VALUES (?,?,?,?,?,?,?)",
                               (self.sid, None, "user", "APPENDED", "FINAL", "{}", 0.))
                writes.append("COMMITTED_WHILE_READER_ACTIVE")
            return page
        with patch.object(CE, "_page", side_effect=mutate_after_first):
            path = Path(CE.export_chat(self.r.store, self.sid, "json", page_size=2))
        rows = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(writes, ["COMMITTED_WHILE_READER_ACTIVE"])
        self.assertEqual([x["text"] for x in rows],
                         [f"ORIGINAL-{i}" for i in range(5)])
        self.assertTrue(all(x["status"] == "FINAL" for x in rows))
        live = self.r.store.rows(
            "SELECT text,status FROM messages WHERE session_id=? ORDER BY id", (self.sid,))
        self.assertIn({"text": "MUTATED", "status": "ERROR"}, live)
        self.assertIn({"text": "APPENDED", "status": "FINAL"}, live)
        self.assertEqual(len(live), 5)

    def test_markdown_snapshot_keeps_preupdate_text_and_status(self):
        real = CE._page
        once = []
        def mutate(conn, session, cursor, bound, size):
            page = real(conn, session, cursor, bound, size)
            if not once:
                with self.r.store.tx() as db:
                    db.execute("UPDATE messages SET text='AFTER',status='ERROR' "
                               "WHERE session_id=? AND text='ORIGINAL-4'", (self.sid,))
                once.append(True)
            return page
        with patch.object(CE, "_page", side_effect=mutate):
            md = Path(CE.export_chat(self.r.store, self.sid, "md", page_size=2)).read_text()
        self.assertIn("ORIGINAL-4", md)
        self.assertNotIn("AFTER", md)
        self.assertNotIn("**user · ERROR**", md)

    def test_export_reader_is_strictly_read_only(self):
        real = CE._page
        def attempt_write(conn, session, cursor, bound, size):
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("UPDATE messages SET text='FORBIDDEN' WHERE session_id=?",
                             (self.sid,))
            return real(conn, session, cursor, bound, size)
        with patch.object(CE, "_page", side_effect=attempt_write):
            rows = json.loads(Path(CE.export_chat(self.r.store, self.sid,
                                                  page_size=2)).read_text())
        self.assertEqual(len(rows), 5)
        self.assertFalse(any(r["text"] == "FORBIDDEN" for r in rows))

    def test_missing_session_does_not_create_partial_export(self):
        with self.assertRaisesRegex(ValueError, "Chat-ID"):
            CE.export_chat(self.r.store, "chat_missing", page_size=2)
        self.assertFalse((self.home / "exports" / "chat_missing.json").exists())
        self.assertEqual(list((self.home / "exports").glob(".pending-chat-*")), [])


if __name__ == "__main__":
    unittest.main()
