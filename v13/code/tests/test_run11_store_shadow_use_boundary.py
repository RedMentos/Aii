"""Run11 independent real SQLite use-boundary SHADOW integrity tests.

No model inference, Runtime, F5 authorization or learning. This suite starts
RED until scripts.run11_store_shadow_use_boundary is implemented.
"""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run18_step2_balanced_controls as balanced
from scripts import run23_store_typed_bridge_shadow as bridge
from scripts import run11_store_shadow_use_boundary as boundary
from v13.config import initialize
from v13.store import Store


class StoreShadowUseBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.case = next(c for c in balanced.FIXTURES if c["id"] == "Veldora")
        events = [self.store.event(self.session, t) for t in
                  (self.case["history"][0], self.case["history"][2],
                   self.case["current"])]
        self.refs = dict(zip(("old", "sheet", "current"),
                             (e["event_id"] for e in events)))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def seal(self):
        return boundary.seal_candidate(
            self.store, self.session, self.case["id"], self.refs,
            self.case["temporal_mode"], "sheet")

    def inspect(self, ticket, session=None, project=None, store=None):
        return boundary.inspect_shadow(
            store or self.store, ticket,
            self.session if session is None else session,
            self.case["id"] if project is None else project)

    def test_clean_real_store_and_restart_are_shadow_only(self):
        ticket = self.seal()
        output = self.inspect(ticket)
        self.assertEqual(output["action"], self.case["oracle"]["action"])
        self.assertEqual(output["status"], "SHADOW_ONLY")
        self.assertIs(output["authority"], False)
        self.assertIs(output["f5_decision_authority"], False)
        self.assertIs(output["native_executed"], False)
        self.assertIs(output["canonical_gate_pass"], False)
        self.assertEqual(output["verification_scope"], "EVENT_SOURCE_INTEGRITY_ONLY")
        self.store.close()
        self.store = Store(self.home)
        self.assertEqual(self.inspect(ticket)["action"], output["action"])

    def test_late_source_revocation_refuses(self):
        ticket = self.seal()
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=("
                       "SELECT source_id FROM events WHERE id=?)",
                       (self.refs["old"],))
        with self.assertRaises(boundary.Refusal):
            self.inspect(ticket)

    def test_late_user_message_status_refuses(self):
        ticket = self.seal()
        with self.store.tx() as db:
            db.execute("UPDATE messages SET status='DRAFT' "
                       "WHERE event_id=? AND role='user'",
                       (self.refs["sheet"],))
        with self.assertRaises(boundary.Refusal):
            self.inspect(ticket)

    def test_late_original_user_message_text_refuses(self):
        ticket = self.seal()
        with self.store.tx() as db:
            db.execute("UPDATE messages SET text='forged' "
                       "WHERE event_id=? AND role='user'",
                       (self.refs["current"],))
        with self.assertRaises(boundary.Refusal):
            self.inspect(ticket)

    def test_late_event_sequence_change_with_same_hash_refuses(self):
        ticket = self.seal()
        before = self.store.one(
            "SELECT e.rowid AS seq,s.hash FROM events e "
            "JOIN sources s ON s.id=e.source_id WHERE e.id=?",
            (self.refs["old"],))
        end = self.store.one("SELECT rowid AS seq FROM events WHERE id=?",
                             (self.refs["current"],))["seq"]
        with self.store.tx() as db:
            db.execute("UPDATE events SET rowid=? WHERE id=?",
                       (end + 1000, self.refs["old"]))
        after = self.store.one(
            "SELECT e.rowid AS seq,s.hash FROM events e "
            "JOIN sources s ON s.id=e.source_id WHERE e.id=?",
            (self.refs["old"],))
        self.assertEqual(before["hash"], after["hash"])
        self.assertNotEqual(before["seq"], after["seq"])
        with self.assertRaises(boundary.Refusal):
            self.inspect(ticket)

    def test_candidate_action_mutation_refuses(self):
        ticket = self.seal()
        forged = copy.deepcopy(ticket)
        forged["candidate"]["action"] = "B" if ticket["candidate"]["action"] != "B" else "A"
        with self.assertRaises(boundary.Refusal):
            self.inspect(forged)

    def test_ticket_digest_mutation_refuses(self):
        forged = copy.deepcopy(self.seal())
        forged["seal_sha256"] = "0" * 64
        with self.assertRaises(boundary.Refusal):
            self.inspect(forged)

    def test_wrong_consumer_session_or_project_refuses(self):
        ticket = self.seal()
        other = self.store.new_session()
        with self.assertRaises(boundary.Refusal):
            self.inspect(ticket, session=other)
        with self.assertRaises(boundary.Refusal):
            self.inspect(ticket, project="Other")

    def test_other_store_does_not_reuse_ticket(self):
        ticket = self.seal()
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            initialize(home)
            other = Store(home)
            try:
                with self.assertRaises(boundary.Refusal):
                    self.inspect(ticket, store=other)
            finally:
                other.close()

    def test_corrupted_generation_manifest_refuses(self):
        ticket = self.seal()
        generation = self.store.one(
            "SELECT generation_id FROM events WHERE id=?",
            (self.refs["old"],))["generation_id"]
        with self.store.tx() as db:
            db.execute("UPDATE generations SET hash=? WHERE id=?",
                       ("0" * 64, generation))
        with self.assertRaises(boundary.Refusal):
            self.inspect(ticket)

    def test_change_after_second_evaluation_refuses(self):
        ticket = self.seal()
        original = bridge.evaluate

        def revoke_after_recompute(*args, **kwargs):
            result = original(*args, **kwargs)
            with self.store.tx() as db:
                db.execute("UPDATE sources SET deleted=1 WHERE id=("
                           "SELECT source_id FROM events WHERE id=?)",
                           (self.refs["old"],))
            return result

        with patch.object(bridge, "evaluate", revoke_after_recompute):
            with self.assertRaises(boundary.Refusal):
                self.inspect(ticket)

    def test_change_after_first_evaluation_refuses_seal(self):
        original = bridge.evaluate

        def mutate_after_evaluate(*args, **kwargs):
            result = original(*args, **kwargs)
            with self.store.tx() as db:
                db.execute("UPDATE messages SET status='DRAFT' "
                           "WHERE event_id=? AND role='user'",
                           (self.refs["old"],))
            return result

        with patch.object(bridge, "evaluate", mutate_after_evaluate):
            with self.assertRaises(boundary.Refusal):
                self.seal()

    def test_malformed_or_type_confused_ticket_refuses(self):
        ticket = self.seal()
        for value in (None, {}, [], "x", 7):
            with self.subTest(value=value):
                with self.assertRaises(boundary.Refusal):
                    self.inspect(value)
        forged = copy.deepcopy(ticket)
        forged["sources"]["old"]["seq"] = True
        with self.assertRaises(boundary.Refusal):
            self.inspect(forged)


if __name__ == "__main__":
    unittest.main()
