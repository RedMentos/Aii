"""Real SQLite / synthetic-only cross-organ C5/C6 DRAFT bridge tests."""
import json
import unittest
from unittest.mock import patch

from tests.test_run82_jef_b1b2_c3_dual_source import DualSourceEnvelopeTests
from v13 import jef_b1b2_c3_c5c6_draft_shadow as bridge


class DualSourceDraftTests(unittest.TestCase):
    setUp = DualSourceEnvelopeTests.setUp
    tearDown = DualSourceEnvelopeTests.tearDown

    @staticmethod
    def good(messages, schema):
        return json.dumps({"action": json.loads(messages[1]["content"])[
            "typed_jef_action"]}, separators=(",", ":"))

    def call(self, callback=None, **kwargs):
        if callback is None:
            callback = self.good
        return bridge.evaluate(
            self.r, self.event, self.offers, self.ids, callback,
            operator_opt_in=kwargs.pop("opt", True),
            callback_opt_in=kwargs.pop("cb_opt", True),
            approval_receipt=kwargs.pop("receipt", None), **kwargs)

    def count(self, table):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]

    def test_single_callback_stages_one_shadow_draft_and_readonly_c6(self):
        before = (self.count("messages"), self.count("actions"),
                  self.count("packets"))
        calls = []

        def callback(messages, schema):
            calls.append(1)
            return self.good(messages, schema)

        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MUST_NOT_RUN")):
            r = self.call(callback)
        self.assertEqual(r["status"], bridge.STATUS, r)
        self.assertEqual(len(calls), 1, "no second C3 invocation")
        self.assertTrue(r["c6_preflight_only"])
        self.assertTrue(r["c6_is_not_approval"])
        self.assertFalse(r["dual_source_receipt_persisted"])
        self.assertFalse(r["c3_output_receipt_persisted"])
        self.assertFalse(r["c3_receiver_success"])
        self.assertFalse(r["native_proof"])
        self.assertFalse(r["real_tty_approved"])
        self.assertFalse(r["output_committed"])
        self.assertEqual(r["tool_dispatches"], 0)
        self.assertEqual(r["learning_authority"], 0)
        self.assertEqual((self.count("messages"), self.count("actions"),
                          self.count("packets")),
                         (before[0]+1, before[1]+1, before[2]+2))
        row = self.r.store.one(
            "SELECT text,status,metadata FROM messages WHERE id=?",
            (r["draft_message_id"],))
        self.assertEqual((row["text"], row["status"]), ("A", "DRAFT"))
        meta = json.loads(row["metadata"])
        self.assertEqual(meta["origin"], "MODEL_EXACT_SHADOW")
        self.assertNotIn("dual_source_messages_sha256", meta)

    def test_off_receipt_and_noncallable_never_invoke(self):
        def forbidden(*args):
            self.fail("callback invoked")
        self.assertEqual(self.call(forbidden, opt=False)["status"], "OFF")
        self.assertEqual(self.call(forbidden, opt=1)["status"], "OFF")
        self.assertEqual(self.call(forbidden, cb_opt=False)["status"], "OFF")
        self.assertEqual(self.call(forbidden, receipt={"approved": True})[
            "status"], "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assertEqual(self.call(42)["status"], "INVALID_GENERATOR")
        self.assertEqual(self.count("messages"), 0)

    def test_malformed_duplicate_and_wrong_c3_never_stage(self):
        for raw in ('{"action":"B"}', '{"action":"A","action":"B"}',
                    '{"action":"A","extra":1}', "A", "", '{"action":NaN}'):
            with self.subTest(raw=raw):
                r = self.call(lambda _m, _s: raw)
                self.assertEqual(r["status"], "DUAL_SOURCE_C3_RED", r)
                self.assertEqual(self.count("messages"), 0)
                self.assertEqual(self.count("actions"), 0)

    def test_preexisting_new_user_never_calls_generator(self):
        self.r.store.event(self.r.session, "newer user request")
        r = self.call(lambda *_: self.fail("generator called"))
        self.assertEqual(r["status"], "DUAL_SOURCE_C3_RED")
        self.assertFalse(r["callback_invoked"])

    def test_revocation_during_callback_does_not_stage(self):
        def revoke(messages, schema):
            self.r.memory.forget(self.ids[0])
            return self.good(messages, schema)
        r = self.call(revoke)
        self.assertEqual(r["status"], "DUAL_SOURCE_C3_RED")
        self.assertEqual(self.count("messages"), 0)

    def test_idempotent_second_call_rejected_before_model(self):
        first = self.call()
        self.assertEqual(first["status"], bridge.STATUS)
        second = self.call(lambda *_: self.fail("duplicate model call"))
        self.assertEqual(second["status"], "EXISTING_DRAFT_OR_ACTION_RED")
        self.assertFalse(second["callback_invoked"])
        self.assertEqual(self.count("messages"), 1)

    def test_revocation_after_guard_before_stage_refuses(self):
        original = bridge._still_current
        count = [0]

        def changed(*args):
            count[0] += 1
            if count[0] == 1:
                self.r.memory.forget(self.ids[0])
            return original(*args)

        with patch.object(bridge, "_still_current", side_effect=changed):
            r = self.call()
        self.assertEqual(r["status"], "SOURCE_CHANGED_BEFORE_DRAFT", r)
        self.assertEqual(self.count("messages"), 0)

    def test_stage_rechecks_source_inside_transaction(self):
        original = bridge.draft.stage

        def revoke_before_stage(*args, **kwargs):
            self.r.memory.forget(self.ids[0])
            return original(*args, **kwargs)

        with patch.object(bridge.draft, "stage",
                          side_effect=revoke_before_stage):
            r = self.call()
        self.assertEqual(r["status"], "C5_DRAFT_STAGE_RED", r)
        self.assertEqual(self.count("messages"), 0)

    def test_poststage_new_user_reports_orphan_not_rollback(self):
        original = bridge.draft.stage

        def after_stage(*args, **kwargs):
            r = original(*args, **kwargs)
            if r.get("status") == bridge.draft.STAGED:
                self.r.store.event(self.r.session, "newer user after draft")
            return r

        with patch.object(bridge.draft, "stage", side_effect=after_stage):
            r = self.call()
        self.assertEqual(r["status"], "SOURCE_CHANGED_AFTER_DRAFT", r)
        self.assertTrue(r["shadow_draft_may_exist"])
        self.assertEqual(self.count("messages"), 1)

    def test_c6_tampered_draft_fails_closed_and_reports_orphan(self):
        original = bridge.draft.preflight

        def corrupt_before_c6(*args, **kwargs):
            self.r.store.db.execute(
                "UPDATE messages SET text='B' WHERE role='assistant'")
            self.r.store.db.commit()
            return original(*args, **kwargs)

        with patch.object(bridge.draft, "preflight",
                          side_effect=corrupt_before_c6):
            r = self.call()
        self.assertEqual(r["status"], "C6_DRAFT_PREFLIGHT_RED", r)
        self.assertTrue(r["shadow_draft_may_exist"])
        self.assertEqual(self.count("messages"), 1)

    def test_stage_claim_mismatch_cannot_pass(self):
        original = bridge.draft.stage

        def wrong(*args, **kwargs):
            r = dict(original(*args, **kwargs))
            r["source_action"] = "B"
            return r

        with patch.object(bridge.draft, "stage", side_effect=wrong):
            r = self.call()
        self.assertEqual(r["status"], "C5_DRAFT_BINDING_RED", r)
        self.assertTrue(r["shadow_draft_may_exist"])

    def test_source_changes_after_c6_are_red(self):
        original = bridge.draft.preflight

        def new_user(*args, **kwargs):
            r = original(*args, **kwargs)
            if r.get("status") == "NEEDS_REAL_TTY_APPROVAL":
                self.r.store.event(self.r.session, "newer user after C6")
            return r

        with patch.object(bridge.draft, "preflight", side_effect=new_user):
            r = self.call()
        self.assertEqual(r["status"], "SOURCE_CHANGED_AFTER_C6_PREFLIGHT",
                         r)
        self.assertTrue(r["shadow_draft_may_exist"])


if __name__ == "__main__":
    unittest.main()
