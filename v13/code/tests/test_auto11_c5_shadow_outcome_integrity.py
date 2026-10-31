"""Real SQLite C5 SHADOW outcome-null and no competing output tests."""
import json
import unittest
from unittest.mock import patch

from tests.test_run82_jef_b1b2_c3_dual_source import DualSourceEnvelopeTests
from v13 import jef_b1b2_c3_c5c6_draft_shadow as bridge
from v13.c5_shadow_action_binding import _c5_shadow
from v13.common import dumps, now


class ShadowOutcomeTests(unittest.TestCase):
    setUp = DualSourceEnvelopeTests.setUp
    tearDown = DualSourceEnvelopeTests.tearDown

    @staticmethod
    def callback(messages, schema):
        return dumps({"action": json.loads(messages[1]["content"])[
            "typed_jef_action"]})

    def stage(self):
        r = bridge.evaluate(
            self.r, self.event, self.offers, self.ids, self.callback,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(r["status"], bridge.STATUS, r)
        return r

    def verify(self, staged):
        return _c5_shadow(
            self.r.store, staged["c5_action_id"],
            self.event["event_id"], self.r.session)

    def insert_assistant(self, event_id, status):
        self.r.store.db.execute(
            "INSERT INTO messages(session_id,event_id,role,text,status,"
            "metadata,created) VALUES (?,?,?,?,?,?,?)",
            (self.r.session, event_id, "assistant", "untrusted output",
             status, "{}", now()))
        self.r.store.db.commit()

    def test_valid_shadow_has_null_outcome_and_no_visible_output(self):
        r = self.stage()
        self.assertIsNotNone(self.verify(r))
        row = self.r.store.one(
            "SELECT status,outcome FROM actions WHERE id=?",
            (r["c5_action_id"],))
        self.assertEqual(row["status"], "SHADOW_DRAFT")
        self.assertIsNone(row["outcome"])

    def test_outcome_write_without_status_change_rejected(self):
        r = self.stage()
        self.r.store.db.execute(
            "UPDATE actions SET outcome='external result' WHERE id=?",
            (r["c5_action_id"],))
        self.r.store.db.commit()
        self.assertIsNone(self.verify(r))

    def test_competing_final_assistant_rejected(self):
        r = self.stage()
        self.insert_assistant(self.event["event_id"], "FINAL")
        self.assertIsNone(self.verify(r))

    def test_competing_output_committed_assistant_rejected(self):
        r = self.stage()
        self.insert_assistant(self.event["event_id"], "OUTPUT_COMMITTED")
        self.assertIsNone(self.verify(r))

    def test_competing_streaming_assistant_rejected(self):
        r = self.stage()
        self.insert_assistant(self.event["event_id"], "STREAMING")
        self.assertIsNone(self.verify(r))

    def test_foreign_event_final_does_not_corrupt_current_c5_binding(self):
        r = self.stage()
        foreign = self.r.store.event(self.r.session, "other user turn")
        self.insert_assistant(foreign["event_id"], "FINAL")
        self.assertIsNotNone(self.verify(r))

    def test_c6_outcome_tamper_fails_and_quarantines_without_erasure(self):
        original = bridge._c6_preflight
        staged = {}

        def tamper(*args, **kwargs):
            staged.update(args[-1])
            self.r.store.db.execute(
                "UPDATE actions SET outcome='external result' WHERE id=?",
                (staged["c5_action_id"],))
            self.r.store.db.commit()
            return original(*args, **kwargs)

        with patch.object(bridge, "_c6_preflight", side_effect=tamper):
            r = bridge.evaluate(
                self.r, self.event, self.offers, self.ids, self.callback,
                operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(r["status"], "C6_DRAFT_PREFLIGHT_RED", r)
        self.assertTrue(r["quarantine_complete"])
        row = self.r.store.one(
            "SELECT status,outcome FROM actions WHERE id=?",
            (staged["c5_action_id"],))
        self.assertEqual(row["status"], "SHADOW_QUARANTINED")
        self.assertEqual(row["outcome"], "external result")
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='FINAL'")["n"], 0)


if __name__ == "__main__":
    unittest.main()
