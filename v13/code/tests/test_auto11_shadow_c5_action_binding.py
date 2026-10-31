"""Real SQLite strict SHADOW_DRAFT C5/F3 binding tests; no native calls."""
import json
import unittest
from unittest.mock import patch

from tests.test_run82_jef_b1b2_c3_dual_source import DualSourceEnvelopeTests
from v13 import jef_b1b2_c3_c5c6_draft_shadow as bridge
from v13.c5_shadow_action_binding import _c5_shadow
from v13.jef_c3_c5_c6_fallback_draft_candidate import _c5 as legacy_c5
from v13.common import dumps, uid, now


class ShadowC5ActionTests(unittest.TestCase):
    setUp = DualSourceEnvelopeTests.setUp
    tearDown = DualSourceEnvelopeTests.tearDown

    def stage(self):
        def callback(messages, schema):
            action = json.loads(messages[1]["content"])["typed_jef_action"]
            return dumps({"action": action})
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            result = bridge.evaluate(
                self.r, self.event, self.offers, self.ids, callback,
                operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], bridge.STATUS, result)
        return result

    def verify(self, result):
        return _c5_shadow(self.r.store, result["c5_action_id"],
                          self.event["event_id"], self.r.session)

    def test_shadow_status_never_dispatched_and_no_final(self):
        r = self.stage()
        row = self.r.store.one("SELECT status FROM actions WHERE id=?",
                               (r["c5_action_id"],))
        self.assertEqual(row["status"], "SHADOW_DRAFT")
        self.assertEqual(r["shadow_action_status"], "SHADOW_DRAFT")
        self.assertIsNotNone(self.verify(r))
        self.assertIsNone(legacy_c5(self.r.store, r["c5_action_id"],
                                    self.event["event_id"], self.r.session))
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='FINAL'")["n"], 0)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM actions WHERE status='DISPATCHED'")[
            "n"], 0)

    def test_dispatched_tamper_rejected(self):
        r = self.stage()
        self.r.store.db.execute(
            "UPDATE actions SET status='DISPATCHED' WHERE id=?",
            (r["c5_action_id"],))
        self.r.store.db.commit()
        self.assertIsNone(self.verify(r))

    def test_wrong_expected_rejected(self):
        r = self.stage()
        self.r.store.db.execute(
            "UPDATE actions SET expected='{}' WHERE id=?",
            (r["c5_action_id"],))
        self.r.store.db.commit()
        self.assertIsNone(self.verify(r))

    def test_corollary_payload_tamper_rejected(self):
        r = self.stage()
        self.r.store.db.execute(
            "UPDATE packets SET payload='{}' WHERE kind='CorollaryCopy' "
            "AND event_id=?", (self.event["event_id"],))
        self.r.store.db.commit()
        self.assertIsNone(self.verify(r))

    def test_intent_payload_tamper_rejected(self):
        r = self.stage()
        self.r.store.db.execute(
            "UPDATE packets SET payload='{}' WHERE kind='ActionIntent' "
            "AND event_id=?", (self.event["event_id"],))
        self.r.store.db.commit()
        self.assertIsNone(self.verify(r))

    def test_duplicate_action_intent_rejected(self):
        r = self.stage()
        row = self.r.store.one(
            "SELECT event_id,generation_id,payload FROM packets "
            "WHERE kind='ActionIntent' AND event_id=?",
            (self.event["event_id"],))
        self.r.store.db.execute(
            "INSERT INTO packets VALUES (?,?,?,?,?,?)",
            (uid("pkt"), "ActionIntent", row["event_id"],
             row["generation_id"], row["payload"], now()))
        self.r.store.db.commit()
        self.assertIsNone(self.verify(r))

    def test_wrong_session_rejected(self):
        r = self.stage()
        self.assertIsNone(_c5_shadow(self.r.store, r["c5_action_id"],
                                     self.event["event_id"], "foreign_session"))

    def test_corollary_generation_mismatch_rejected(self):
        r = self.stage()
        self.r.store.db.execute(
            "UPDATE packets SET generation_id='foreign_gen' "
            "WHERE kind='CorollaryCopy' AND event_id=?",
            (self.event["event_id"],))
        self.r.store.db.commit()
        self.assertIsNone(self.verify(r))

    def test_c6_rejects_action_promoted_to_dispatched(self):
        original = bridge._c6_preflight

        def promote(*args, **kwargs):
            self.r.store.db.execute(
                "UPDATE actions SET status='DISPATCHED' WHERE kind='TEXT_REPORT'")
            self.r.store.db.commit()
            return original(*args, **kwargs)

        with patch.object(bridge, "_c6_preflight", side_effect=promote):
            result = bridge.evaluate(
                self.r, self.event, self.offers, self.ids,
                lambda m, s: dumps({"action": json.loads(m[1]["content"])[
                    "typed_jef_action"]}),
                operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "C6_DRAFT_PREFLIGHT_RED", result)
        self.assertEqual(result["component_status"], "C6_C5_F3_BINDING_RED")
        self.assertTrue(result["shadow_draft_may_exist"])


if __name__ == "__main__":
    unittest.main()
