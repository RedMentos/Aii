"""Real SQLite same-process orphan SHADOW DRAFT quarantine tests."""
import json
import unittest
from unittest.mock import patch

from tests.test_run82_jef_b1b2_c3_dual_source import DualSourceEnvelopeTests
from v13 import jef_b1b2_c3_c5c6_draft_shadow as bridge
from v13.common import dumps


class OrphanDraftTests(unittest.TestCase):
    setUp = DualSourceEnvelopeTests.setUp
    tearDown = DualSourceEnvelopeTests.tearDown

    @staticmethod
    def callback(messages, schema):
        return dumps({"action": json.loads(messages[1]["content"])[
            "typed_jef_action"]})

    def call(self):
        return bridge.evaluate(
            self.r, self.event, self.offers, self.ids, self.callback,
            operator_opt_in=True, callback_opt_in=True)

    def state(self, staged):
        msg = self.r.store.one(
            "SELECT status,metadata,text FROM messages WHERE id=?",
            (staged["draft_message_id"],))
        action = self.r.store.one(
            "SELECT status,expected,outcome FROM actions WHERE id=?",
            (staged["c5_action_id"],))
        return dict(msg), dict(action)

    def test_good_draft_remains_shadow_not_quarantined(self):
        r = self.call()
        self.assertEqual(r["status"], bridge.STATUS, r)
        msg, action = self.state(r)
        self.assertEqual((msg["status"], action["status"]),
                         ("DRAFT", "SHADOW_DRAFT"))
        self.assertIsNone(action["outcome"])

    def test_newer_user_after_stage_quarantines_without_erasing_evidence(self):
        original = bridge._stage_range
        saved = {}

        def after_stage(*args, **kwargs):
            r = original(*args, **kwargs)
            if r.get("status") == "ATOMIC_RANGE_DRAFT_STAGED_SHADOW":
                saved.update(r)
                saved["before"] = self.state(r)
                self.r.store.event(self.r.session, "newer USER after stage")
            return r

        with patch.object(bridge, "_stage_range", side_effect=after_stage):
            r = self.call()
        self.assertEqual(r["status"], "SOURCE_CHANGED_AFTER_DRAFT", r)
        self.assertTrue(r["quarantine_complete"])
        self.assertTrue(r["quarantine_message_interrupted"])
        self.assertTrue(r["quarantine_action_isolated"])
        msg, action = self.state(saved)
        self.assertEqual((msg["status"], action["status"]),
                         ("INTERRUPTED", "SHADOW_QUARANTINED"))
        self.assertEqual(msg["metadata"], saved["before"][0]["metadata"])
        self.assertEqual(msg["text"], saved["before"][0]["text"])
        self.assertEqual(action["expected"], saved["before"][1]["expected"])
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='FINAL'")["n"], 0)

    def test_c6_tampered_metadata_preserved_and_quarantined(self):
        original = bridge._c6_preflight
        saved = {}

        def tamper(*args, **kwargs):
            staged = args[-1]
            saved.update(staged)
            self.r.store.db.execute(
                "UPDATE messages SET metadata='{}' WHERE id=?",
                (staged["draft_message_id"],))
            self.r.store.db.commit()
            return original(*args, **kwargs)

        with patch.object(bridge, "_c6_preflight", side_effect=tamper):
            r = self.call()
        self.assertEqual(r["status"], "C6_DRAFT_PREFLIGHT_RED", r)
        self.assertTrue(r["quarantine_complete"])
        msg, action = self.state(saved)
        self.assertEqual(msg["metadata"], "{}")
        self.assertEqual((msg["status"], action["status"]),
                         ("INTERRUPTED", "SHADOW_QUARANTINED"))

    def test_newer_user_after_c6_quarantines(self):
        original = bridge._c6_preflight
        saved = {}

        def after_c6(*args, **kwargs):
            saved.update(args[-1])
            result = original(*args, **kwargs)
            if result.get("status") == "C6_DRAFT_INTEGRITY_SHADOW":
                self.r.store.event(self.r.session, "newer USER after C6")
            return result

        with patch.object(bridge, "_c6_preflight", side_effect=after_c6):
            r = self.call()
        self.assertEqual(r["status"], "SOURCE_CHANGED_AFTER_C6_PREFLIGHT", r)
        self.assertTrue(r["quarantine_complete"])
        msg, action = self.state(saved)
        self.assertEqual((msg["status"], action["status"]),
                         ("INTERRUPTED", "SHADOW_QUARANTINED"))

    def test_tampered_dispatched_action_is_not_falsely_quarantined(self):
        original = bridge._c6_preflight
        saved = {}

        def tamper(*args, **kwargs):
            saved.update(args[-1])
            self.r.store.db.execute(
                "UPDATE actions SET status='DISPATCHED' WHERE id=?",
                (saved["c5_action_id"],))
            self.r.store.db.commit()
            return original(*args, **kwargs)

        with patch.object(bridge, "_c6_preflight", side_effect=tamper):
            r = self.call()
        self.assertEqual(r["status"], "C6_DRAFT_PREFLIGHT_RED", r)
        self.assertFalse(r["quarantine_complete"])
        self.assertTrue(r["quarantine_message_interrupted"])
        self.assertFalse(r["quarantine_action_isolated"])
        msg, action = self.state(saved)
        self.assertEqual((msg["status"], action["status"]),
                         ("INTERRUPTED", "DISPATCHED"))

    def test_repeat_quarantine_idempotent_and_no_content_change(self):
        original = bridge._stage_range
        saved = {}

        def after_stage(*args, **kwargs):
            r = original(*args, **kwargs)
            if r.get("status") == "ATOMIC_RANGE_DRAFT_STAGED_SHADOW":
                saved.update(r)
                self.r.store.event(self.r.session, "newer USER")
            return r

        with patch.object(bridge, "_stage_range", side_effect=after_stage):
            r = self.call()
        self.assertTrue(r["quarantine_complete"])
        before = self.state(saved)
        again = bridge._quarantine_staged(self.r, self.event, saved)
        self.assertTrue(again["quarantine_complete"])
        self.assertEqual(self.state(saved), before)

    def test_foreign_event_never_quarantines_valid_draft(self):
        r = self.call()
        self.assertEqual(r["status"], bridge.STATUS)
        before = self.state(r)
        flags = bridge._quarantine_staged(
            self.r, {"event_id": "evt_foreign"}, r)
        self.assertFalse(flags["quarantine_complete"])
        self.assertEqual(self.state(r), before)


if __name__ == "__main__":
    unittest.main()
