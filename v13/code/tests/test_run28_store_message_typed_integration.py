"""Run28 cross-package: Run24 Store user-message provenance survives Run27 bridge."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import run18_step2_balanced_controls as balanced
from scripts import run23_store_typed_bridge_shadow as bridge
from v13.config import initialize
from v13.store import Store


class StoreMessageTypedIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        home = Path(self.temp.name)
        initialize(home)
        self.store = Store(home)
        self.session = self.store.new_session()
        self.case = next(x for x in balanced.FIXTURES if x["id"] == "Veldora")
        events = [self.store.event(self.session, text)
                  for text in (self.case["history"][0],
                               self.case["history"][2],
                               self.case["current"])]
        self.refs = dict(zip(("old", "sheet", "current"),
                             (x["event_id"] for x in events)))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def evaluate(self, session=None):
        return bridge.evaluate(
            self.store, session or self.session, self.case["id"],
            self.refs, self.case["temporal_mode"], "sheet")

    def test_clean_real_store_candidate_stays_shadow_only(self):
        result = self.evaluate()
        self.assertEqual(result["action"], self.case["oracle"]["action"])
        self.assertFalse(result["authority"])
        self.assertFalse(result["f5_decision_authority"])
        self.assertEqual(result["verification_scope"],
                         "EVENT_SOURCE_INTEGRITY_ONLY")

    def test_event_session_laundering_without_user_messages_refuses(self):
        other = self.store.new_session()
        with self.store.tx() as db:
            for ref in self.refs.values():
                db.execute("UPDATE events SET session_id=? WHERE id=?",
                           (other, ref))
        with self.assertRaises(bridge.Refusal):
            self.evaluate(other)

    def test_original_user_message_source_metadata_mutation_refuses(self):
        ref = self.refs["old"]
        with self.store.tx() as db:
            db.execute("UPDATE messages SET metadata=? WHERE event_id=? "
                       "AND role='user'", (json.dumps({"source_ref": {
                           "source_id": "src_forged", "sha256": "0" * 64,
                           "char_start": 0, "char_end": 0,
                           "modality": "text"}}), ref))
        with self.assertRaises(bridge.Refusal):
            self.evaluate()

    def test_original_user_message_status_mutation_refuses(self):
        with self.store.tx() as db:
            db.execute("UPDATE messages SET status='DRAFT' WHERE event_id=? "
                       "AND role='user'", (self.refs["sheet"],))
        with self.assertRaises(bridge.Refusal):
            self.evaluate()

    def test_duplicate_original_user_message_refuses(self):
        row = self.store.one(
            "SELECT session_id,event_id,role,text,status,metadata,created "
            "FROM messages WHERE event_id=? AND role='user'",
            (self.refs["old"],))
        with self.store.tx() as db:
            db.execute("INSERT INTO messages(session_id,event_id,role,text,"
                       "status,metadata,created) VALUES (?,?,?,?,?,?,?)",
                       tuple(row[k] for k in (
                           "session_id", "event_id", "role", "text",
                           "status", "metadata", "created")))
        with self.assertRaises(bridge.Refusal):
            self.evaluate()

    def test_corrupted_generation_manifest_refuses(self):
        row = self.store.one("SELECT generation_id FROM events WHERE id=?",
                             (self.refs["old"],))
        with self.store.tx() as db:
            db.execute("UPDATE generations SET hash=? WHERE id=?",
                       ("0" * 64, row["generation_id"]))
        with self.assertRaises(bridge.Refusal):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
