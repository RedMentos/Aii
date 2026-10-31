"""Adversarial real-SQLite software tests for isolated F1/F5 finalizer."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.config import DEFAULTS, initialize
from v13.memory import Memory
from v13.store import Store
from v13.source_consumer import render_messages, verified_recall_messages
from v13 import f1f5_event_finalizer_candidate as finalizer
from scripts.run51_f1f5_second_attempt_native import load_fixture

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class EventFinalizerCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, DEFAULTS)
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        self.current = self.store.event(self.session, self.f["followup"])
        self.calls = []

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def correction(self, value=None, key=None):
        event = self.store.event(self.session, self.f["correction_event"])
        return self.memory.feedback(event["event_id"], "fact", value or self.f["value"],
                                    permission="record", key=key or self.f["key"],
                                    scope="session")

    def callback(self, messages):
        self.calls.append(messages)
        return "Project Cypress budget is 64 Euro."

    def call(self, opt=True, callback=None, event=None, session=None):
        return finalizer.shadow_candidate(
            DEFAULTS, self.memory, session or self.session,
            event or self.current["event_id"],
            callback or self.callback, operator_opt_in=opt)

    def test_default_off_nonbool_and_no_source_never_invoke(self):
        for opt in (False, None, 0, 1, "yes", {}, []):
            with self.subTest(opt=opt):
                self.assertEqual(self.call(opt=opt)["status"], "OFF")
        self.assertEqual(self.call()["status"], "CLARIFY")
        self.assertEqual(self.calls, [])

    def test_explicit_held_digest_only_and_no_assistant_output(self):
        self.correction()
        before = self.store.one("SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"]
        r = self.call()
        self.assertEqual(r["status"], "SHADOW_HELD")
        self.assertTrue(r["callback_invoked"])
        self.assertEqual(r["candidate_sha256"], hashlib.sha256(
            b"Project Cypress budget is 64 Euro.").hexdigest())
        self.assertEqual(r["candidate_bytes"], 34)
        self.assertEqual(r["delivery_authority"], 0)
        self.assertFalse(r["output_committed"])
        self.assertEqual(r["tool_dispatches"], 0)
        self.assertEqual(r["learning_authority"], 0)
        self.assertNotIn("candidate_text", r)
        self.assertNotIn("messages", r)
        self.assertEqual(self.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"], before)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("Verified user correction", self.calls[0][0]["content"])

    def test_restart_and_wrong_session(self):
        self.correction()
        self.store.close()
        self.store = Store(self.home)
        self.memory = Memory(self.store, DEFAULTS)
        self.assertEqual(self.call()["status"], "SHADOW_HELD")
        other = self.store.new_session("foreign")
        self.assertEqual(self.call(session=other)["status"], "EVENT_OR_SOURCE_RED")

    def test_deleted_current_event_source_denied(self):
        self.correction()
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.current["source_ref"]["source_id"],))
        self.assertEqual(self.call()["status"], "EVENT_OR_SOURCE_RED")
        self.assertEqual(self.calls, [])

    def test_tampered_event_envelope_denied(self):
        self.correction()
        with self.store.tx() as db:
            db.execute("UPDATE events SET packet='{}' WHERE id=?",
                       (self.current["event_id"],))
        self.assertEqual(self.call()["status"], "EVENT_OR_SOURCE_RED")
        self.assertEqual(self.calls, [])

    def test_revoke_before_second_check_never_invokes_callback(self):
        mid = self.correction()
        original = finalizer.verified_recall_messages
        seen = [0]

        def revoke_after_first(*args):
            result = original(*args)
            seen[0] += 1
            if seen[0] == 1:
                self.memory.forget(mid)
            return result

        with patch.object(finalizer, "verified_recall_messages",
                          side_effect=revoke_after_first):
            r = self.call()
        self.assertEqual(seen[0], 2)
        self.assertEqual(r["status"], "STALE_BEFORE_DISPATCH")
        self.assertFalse(r["callback_invoked"])
        self.assertEqual(self.calls, [])

    def test_revoke_during_callback_discards_answer(self):
        mid = self.correction()

        def revoke(messages):
            self.calls.append(messages)
            self.memory.forget(mid)
            return "Project Cypress budget is 64 Euro."

        r = self.call(callback=revoke)
        self.assertEqual(r["status"], "HELD_REVOKED_OR_CHANGED")
        self.assertTrue(r["callback_invoked"])
        self.assertNotIn("candidate_sha256", r)

    def test_conflicting_active_alias_abstains(self):
        self.correction()
        self.correction("73 Euro", "Project Cypress budgets")
        self.assertEqual(self.call()["status"], "CLARIFY")
        self.assertEqual(self.calls, [])

    def test_callback_errors_nontext_oversize_control_char(self):
        self.correction()
        for bad in (None, 7, "", "x" * 513, "value\x00"):
            with self.subTest(bad=repr(bad)[:15]):
                r = self.call(callback=lambda messages, value=bad: value)
                self.assertEqual(r["status"], "INVALID_CANDIDATE")
                self.assertNotIn("candidate_sha256", r)
        def broken(messages):
            raise RuntimeError("synthetic failure")
        self.assertEqual(self.call(callback=broken)["status"], "GENERATION_ERROR")

    def test_legacy_signed_renderer_without_live_recheck_is_not_a_dispatch_gate(self):
        mid = self.correction()
        decision = verified_recall_messages(
            DEFAULTS, self.f["followup"], self.session, self.memory)["decision"]
        self.assertEqual(decision["status"], "ADMITTED")
        self.memory.forget(mid)
        # Documents existing legacy bypass without changing frozen source code.
        old = render_messages(DEFAULTS, self.f["followup"], decision)
        self.assertIn("64 Euro", old[0]["content"])
        with self.assertRaises(ValueError):
            render_messages(DEFAULTS, self.f["followup"], decision,
                            memory=self.memory, session=self.session)
        self.assertEqual(self.call()["status"], "CLARIFY")


if __name__ == "__main__":
    unittest.main()
