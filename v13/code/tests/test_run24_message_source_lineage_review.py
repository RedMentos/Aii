"""Run24 RED-first: EventEnvelope source integrity also needs Store user-message lineage.

Actual ephemeral Store SQLite and blobs, software only. No native model/Runtime.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run21_event_source_adapter_shadow as adapter
from v13.config import initialize
from v13.store import Store


class UserMessageLineageReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        home = Path(self.temp.name)
        initialize(home)
        self.store = Store(home)
        self.session = self.store.new_session()
        self.old = self.store.event(
            self.session, "Projekt Nerava Auftaktnotiz: Budget 189 Euro. "
            "Frist 13 Tage. Lokalpflicht ja.")
        self.sheet = self.store.event(
            self.session, "Projekt Nerava Lieferantenblatt. "
            "Option A: Kosten 166 Euro, Dauer 12 Tage, lokal ja. "
            "Option B: Kosten 176 Euro, Dauer 11 Tage, lokal nein.")
        self.current = self.store.event(
            self.session, "Projekt Nerava. Nutze die früheren verbindlichen Regeln "
            "und das aktuelle Lieferantenblatt. Berechne.")
        self.refs = {"old": self.old["event_id"],
                     "sheet": self.sheet["event_id"],
                     "current": self.current["event_id"]}

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def reader(self, session=None):
        return adapter.EventSourceReader(
            self.store, session or self.session, "Nerava", self.refs)

    def test_original_store_messages_still_verify_without_authority(self):
        reader = self.reader()
        for ref in self.refs.values():
            result = reader(ref)
            self.assertTrue(result["verified"])
            self.assertFalse(result["authority"])
            self.assertEqual(result["verification_scope"],
                             "EVENT_SOURCE_INTEGRITY_ONLY")

    def test_event_session_reassignment_cannot_launder_original_user_input(self):
        other = self.store.new_session()
        with self.store.tx() as db:
            for ref in self.refs.values():
                db.execute("UPDATE events SET session_id=? WHERE id=?",
                           (other, ref))
        with self.assertRaises(adapter.Refusal):
            self.reader(other)

    def test_user_message_role_status_session_text_metadata_are_bound(self):
        ref = self.refs["old"]
        original = self.store.one(
            "SELECT id,session_id,role,text,status,metadata FROM messages "
            "WHERE event_id=? AND role='user'", (ref,))
        self.assertIsNotNone(original)
        other = self.store.new_session()
        variants = {
            "role": "assistant",
            "status": "DRAFT",
            "session_id": other,
            "text": original["text"] + " forged",
            "metadata": json.dumps({"source_ref": {
                "source_id": "src_forged", "sha256": "0" * 64,
                "char_start": 0, "char_end": 0, "modality": "text"}}),
        }
        for field, value in variants.items():
            with self.subTest(field=field):
                with self.store.tx() as db:
                    db.execute(f"UPDATE messages SET {field}=? WHERE id=?",
                               (value, original["id"]))
                try:
                    with self.assertRaises(adapter.Refusal):
                        self.reader()
                finally:
                    with self.store.tx() as db:
                        db.execute(f"UPDATE messages SET {field}=? WHERE id=?",
                                   (original[field], original["id"]))

    def test_missing_original_user_message_refuses(self):
        with self.store.tx() as db:
            db.execute("DELETE FROM messages WHERE event_id=? AND role='user'",
                       (self.refs["old"],))
        with self.assertRaises(adapter.Refusal):
            self.reader()

    def test_duplicate_original_user_message_refuses(self):
        row = self.store.one(
            "SELECT session_id,event_id,role,text,status,metadata,created "
            "FROM messages WHERE event_id=? AND role='user'",
            (self.refs["old"],))
        with self.store.tx() as db:
            db.execute(
                "INSERT INTO messages(session_id,event_id,role,text,status,"
                "metadata,created) VALUES (?,?,?,?,?,?,?)",
                tuple(row[k] for k in (
                    "session_id", "event_id", "role", "text",
                    "status", "metadata", "created")))
        with self.assertRaises(adapter.Refusal):
            self.reader()

    def test_source_revoked_during_read_must_not_be_reported_active(self):
        source_id = self.old["source_ref"]["source_id"]
        original = self.store.read_source
        changed = []
        def revoke_during_read(ref):
            text = original(ref)
            if not changed:
                changed.append(True)
                with self.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (source_id,))
            return text
        with patch.object(self.store, "read_source", revoke_during_read):
            with self.assertRaises(adapter.Refusal):
                self.reader()
        self.assertEqual(changed, [True])

    def test_corrupted_generation_manifest_hash_refuses(self):
        row = self.store.one(
            "SELECT generation_id FROM events WHERE id=?",
            (self.refs["old"],))
        with self.store.tx() as db:
            db.execute("UPDATE generations SET hash=? WHERE id=?",
                       ("0" * 64, row["generation_id"]))
        with self.assertRaises(adapter.Refusal):
            self.reader()


if __name__ == "__main__":
    unittest.main()
