"""Real Store/SQLite F1/F5 -> C5/C6 atomic DRAFT SHADOW candidate tests."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.config import DEFAULTS, initialize
from v13.memory import Memory
from v13.store import Store
from v13 import f1f5_c5c6_atomic_draft_candidate as draft
from scripts.run51_f1f5_second_attempt_native import load_fixture

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class F1F5C5C6AtomicDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, DEFAULTS)
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        self.current = self.store.event(self.session, self.f["followup"])
        self.calls = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def correction(self, value=None, key=None):
        e = self.store.event(self.session, self.f["correction_event"])
        return self.memory.feedback(e["event_id"], "fact", value or self.f["value"],
                                    permission="record", key=key or self.f["key"],
                                    scope="session")

    def callback(self, messages):
        self.calls += 1
        return "Project Cypress budget is 64 Euro."

    def stage(self, callback=None, opt=True, session=None):
        return draft.stage_draft(
            DEFAULTS, self.memory, session or self.session,
            self.current["event_id"], callback or self.callback,
            operator_opt_in=opt)

    def counts(self):
        # Human :forget may legitimately delete its own provenance packets;
        # count only the four C5/C6 staging objects for rollback assertions.
        return {
            "packets": self.store.one(
                "SELECT COUNT(*) AS n FROM packets WHERE kind IN ('ActionIntent','CorollaryCopy')")["n"],
            "actions": self.store.one("SELECT COUNT(*) AS n FROM actions")["n"],
            "messages": self.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"],
        }

    def test_default_off_and_missing_correction_have_no_c5_writes(self):
        before = self.counts()
        for opt in (False, None, 0, 1, "yes"):
            self.assertEqual(self.stage(opt=opt)["status"], "OFF")
        self.assertEqual(self.stage()["status"], "CLARIFY")
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.counts(), before)

    def test_exact_atomic_four_objects_no_final_or_tool_or_learning(self):
        self.correction()
        before = self.counts()
        r = self.stage()
        self.assertEqual(r["status"], "DRAFT_STAGED_SHADOW_NO_COMMIT")
        self.assertEqual(self.calls, 1)
        after = self.counts()
        self.assertEqual(after["packets"] - before["packets"], 2)
        self.assertEqual(after["actions"] - before["actions"], 1)
        self.assertEqual(after["messages"] - before["messages"], 1)
        self.assertEqual(r["candidate_sha256"], hashlib.sha256(
            b"Project Cypress budget is 64 Euro.").hexdigest())
        self.assertNotIn("candidate_text", r)
        self.assertEqual(r["delivery_authority"], 0)
        self.assertFalse(r["output_committed"])
        self.assertEqual(r["tool_dispatches"], 0)
        self.assertEqual(r["learning_authority"], 0)
        row = self.store.one("SELECT role,status,text FROM messages WHERE id=?",
                             (r["draft_message_id"],))
        self.assertEqual(row["role"], "assistant")
        self.assertEqual(row["status"], "DRAFT")
        self.assertEqual(row["text"], "Project Cypress budget is 64 Euro.")
        self.assertEqual(draft.check_staged_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"], r)["status"],
            "DRAFT_BOUND_SHADOW_NO_COMMIT")

    def test_semantic_key_logging_outside_tx_but_lexical_inside(self):
        self.correction()
        class SyntheticSemanticKeys:
            def __init__(self):
                self.calls = 0
                self.last_query = None
                self.last = {"status": "SYNTHETIC"}

            def mode(self):
                return "on"

            def similarities(self, query, rows, cancel, deadline, cap=None):
                self.calls += 1
                self.last = {"status": "SYNTHETIC"}
                return {row["id"]: .99 for row in rows}

        keys = SyntheticSemanticKeys()
        self.memory.semantic_keys = keys
        r = self.stage()
        self.assertEqual(r["status"], "DRAFT_STAGED_SHADOW_NO_COMMIT")
        self.assertGreaterEqual(keys.calls, 1)
        # The synthetic semantic scorer was used outside BEGIN IMMEDIATE;
        # inside it the new lexical-only Memory view must not call it.
        calls_before = keys.calls
        checked = draft.check_staged_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"], r)
        self.assertEqual(checked["status"], "DRAFT_BOUND_SHADOW_NO_COMMIT")
        self.assertEqual(keys.calls, calls_before)
        self.assertEqual(self.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE status='FINAL' AND role='assistant'")["n"], 0)

    def test_foreign_session_and_tampered_current_source_no_stage(self):
        self.correction()
        before = self.counts()
        other = self.store.new_session("foreign")
        self.assertEqual(self.stage(session=other)["status"], "EVENT_OR_SOURCE_RED")
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.current["source_ref"]["source_id"],))
        self.assertEqual(self.stage()["status"], "EVENT_OR_SOURCE_RED")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.calls, 0)

    def test_revoked_during_callback_no_stage(self):
        mid = self.correction()
        before = self.counts()
        def revoke(messages):
            self.calls += 1
            self.memory.forget(mid)
            return "Project Cypress budget is 64 Euro."
        r = self.stage(callback=revoke)
        self.assertEqual(r["status"], "SOURCE_CHANGED_BEFORE_DRAFT")
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.counts(), before)

    def test_revoked_between_second_and_transaction_check_no_stage(self):
        mid = self.correction()
        before = self.counts()
        original = draft._verified
        count = [0]
        def revoke_after_second(*args):
            out = original(*args)
            count[0] += 1
            if count[0] == 2:
                self.memory.forget(mid)
            return out
        with patch.object(draft, "_verified", side_effect=revoke_after_second):
            r = self.stage()
        self.assertEqual(count[0], 3)
        self.assertEqual(r["status"], "SOURCE_CHANGED_BEFORE_DRAFT")
        self.assertEqual(self.counts(), before)

    def test_conflicting_active_correction_abstains(self):
        self.correction()
        self.correction("73 Euro", "Project Cypress budgets")
        before = self.counts()
        self.assertEqual(self.stage()["status"], "CLARIFY")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.calls, 0)

    def test_injected_second_packet_serialization_failure_rolls_back_all(self):
        self.correction()
        before = self.counts()
        original = draft.dumps
        count = [0]
        def fail_second(value):
            count[0] += 1
            if count[0] == 2:
                raise RuntimeError("synthetic SQL staging failure")
            return original(value)
        with patch.object(draft, "dumps", side_effect=fail_second):
            r = self.stage()
        self.assertEqual(r["status"], "STORE_OR_BINDING_RED")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.calls, 1)

    def test_post_stage_source_revoke_fails_read_only_check(self):
        mid = self.correction()
        r = self.stage()
        self.assertEqual(r["status"], "DRAFT_STAGED_SHADOW_NO_COMMIT")
        self.memory.forget(mid)
        checked = draft.check_staged_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"], r)
        self.assertNotEqual(checked["status"], "DRAFT_BOUND_SHADOW_NO_COMMIT")
        self.assertEqual(checked["delivery_authority"], 0)

    def test_draft_metadata_and_c5_packet_tamper_refused(self):
        self.correction()
        r = self.stage()
        with self.store.tx() as db:
            db.execute("UPDATE messages SET metadata=? WHERE id=?",
                       ('{"output_authority":"APPROVED"}', r["draft_message_id"]))
        self.assertEqual(draft.check_staged_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"], r)["status"],
            "DRAFT_TAMPERED")
        r = self.stage()
        corollary = self.store.one(
            "SELECT corollary_id FROM actions WHERE id=?", (r["c5_action_id"],))
        with self.store.tx() as db:
            db.execute("UPDATE packets SET payload='{}' WHERE id=?",
                       (corollary["corollary_id"],))
        self.assertEqual(draft.check_staged_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"], r)["status"],
            "C5_BINDING_RED")

    def test_restart_interrupts_uncommitted_draft(self):
        self.correction()
        r = self.stage()
        self.store.close()
        self.store = Store(self.home)
        self.memory = Memory(self.store, DEFAULTS)
        row = self.store.one("SELECT status FROM messages WHERE id=?",
                             (r["draft_message_id"],))
        self.assertEqual(row["status"], "INTERRUPTED")
        self.assertEqual(draft.check_staged_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"], r)["status"],
            "DRAFT_TAMPERED")

    def test_invalid_output_and_callback_error_do_not_stage(self):
        self.correction()
        before = self.counts()
        for bad in (None, "", 42, "x" * 513, "a\x00b", "\ud800"):
            with self.subTest(bad=repr(bad)[:10]):
                r = self.stage(callback=lambda messages, v=bad: v)
                self.assertEqual(r["status"], "INVALID_CANDIDATE")
        def broken(messages):
            raise RuntimeError("synthetic callback error")
        self.assertEqual(self.stage(callback=broken)["status"], "GENERATION_ERROR")
        self.assertEqual(self.counts(), before)


if __name__ == "__main__":
    unittest.main()
