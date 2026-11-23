"""C6 read-only temporal DRAFT preflight with real Store/Memory."""
from pathlib import Path
import tempfile
import unittest

from v13.config import DEFAULTS, initialize
from v13.store import Store
from v13.memory import Memory
from v13.f1f5_temporal_atomic_draft_candidate import stage_temporal_atomic_draft
from v13.c6_temporal_draft_preflight_candidate import preflight_temporal_draft
from scripts.run51_f1f5_second_attempt_native import load_fixture

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class C6TemporalDraftPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, DEFAULTS)
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        correction = self.store.event(self.session, self.f["correction_event"])
        self.mid = self.memory.feedback(
            correction["event_id"], "fact", self.f["value"],
            permission="record", key=self.f["key"], scope="session")
        self.current = self.store.event(self.session, self.f["followup"])

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def stage(self, answer="Project Cypress budget is 64 Euro."):
        result = stage_temporal_atomic_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            lambda messages: answer, operator_opt_in=True)
        self.assertEqual(result["status"],
                         "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT")
        return result

    def preflight(self, staged, opt=True, receipt=None):
        return preflight_temporal_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            staged, operator_opt_in=opt, approval_receipt=receipt)

    def counts(self):
        return (
            self.store.one("SELECT COUNT(*) AS n FROM packets")["n"],
            self.store.one("SELECT COUNT(*) AS n FROM actions")["n"],
            self.store.one("SELECT COUNT(*) AS n FROM messages")["n"])

    def test_valid_draft_needs_real_tty_approval_and_is_read_only(self):
        staged = self.stage()
        before = self.counts()
        a = self.preflight(staged)
        b = self.preflight(staged)
        self.assertEqual(a["status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assertEqual(a["fingerprint_sha256"], b["fingerprint_sha256"])
        self.assertTrue(a["preflight_only"])
        self.assertNotIn("candidate_text", a)
        self.assertEqual(a["delivery_authority"], 0)
        self.assertFalse(a["output_committed"])
        self.assertEqual(a["tool_dispatches"], 0)
        self.assertEqual(a["learning_authority"], 0)
        self.assertEqual(self.counts(), before)

    def test_forged_approval_and_no_optin_never_commit(self):
        staged = self.stage()
        before = self.counts()
        self.assertEqual(self.preflight(staged,opt=False)["status"], "OFF")
        self.assertEqual(self.preflight(staged,receipt=True)["status"],
                         "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assertEqual(self.preflight(staged,receipt={"approved":True})["status"],
                         "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assertEqual(self.counts(), before)

    def test_wrong_amount_extra_number_and_wrong_project_refused(self):
        for text, expected in [
            ("Project Cypress budget is 73 Euro.", "NUMERIC_GROUNDING_RED"),
            ("Project Cypress budget is 64 Euro, not 73.", "NUMERIC_GROUNDING_RED"),
            ("Project Lark budget is 64 Euro.", "PROJECT_GROUNDING_RED")]:
            with self.subTest(text=text):
                staged = self.stage(text)
                before = self.counts()
                self.assertEqual(self.preflight(staged)["status"], expected)
                self.assertEqual(self.counts(), before)
                with self.store.tx() as db:
                    db.execute("DELETE FROM messages WHERE id=?",
                               (staged["draft_message_id"],))
                    db.execute("DELETE FROM actions WHERE id=?",
                               (staged["c5_action_id"],))
                    db.execute("DELETE FROM packets WHERE event_id=? "
                               "AND kind IN ('ActionIntent','CorollaryCopy')",
                               (self.current["event_id"],))

    def test_revoked_source_refuses_preflight(self):
        staged = self.stage()
        self.memory.forget(self.mid)
        self.assertNotEqual(self.preflight(staged)["status"], "NEEDS_REAL_TTY_APPROVAL")

    def test_tampered_draft_hash_refuses(self):
        staged = self.stage()
        with self.store.tx() as db:
            db.execute("UPDATE messages SET text=? WHERE id=?",
                       ("Project Cypress budget is 73 Euro.", staged["draft_message_id"]))
        self.assertNotEqual(self.preflight(staged)["status"], "NEEDS_REAL_TTY_APPROVAL")

    def test_competing_draft_or_final_refuses(self):
        staged = self.stage()
        self.store.message(self.session,self.current["event_id"],
                           "assistant","another answer","DRAFT")
        self.assertEqual(self.preflight(staged)["status"],
                         "COMPETING_OR_COMMITTED_OUTPUT_RED")
        with self.store.tx() as db:
            db.execute("UPDATE messages SET status='FINAL' WHERE role='assistant' "
                       "AND id!=?", (staged["draft_message_id"],))
        self.assertEqual(self.preflight(staged)["status"],
                         "COMPETING_OR_COMMITTED_OUTPUT_RED")

    def test_c5_action_tamper_refuses(self):
        staged = self.stage()
        with self.store.tx() as db:
            db.execute("UPDATE actions SET status='FAILED' WHERE id=?",
                       (staged["c5_action_id"],))
        self.assertNotEqual(self.preflight(staged)["status"], "NEEDS_REAL_TTY_APPROVAL")

    def test_restart_interrupts_draft_and_refuses(self):
        staged = self.stage()
        self.store.close()
        self.store = Store(self.home)
        self.memory = Memory(self.store, DEFAULTS)
        self.assertEqual(self.store.one(
            "SELECT status FROM messages WHERE id=?",
            (staged["draft_message_id"],))["status"], "INTERRUPTED")
        self.assertNotEqual(self.preflight(staged)["status"], "NEEDS_REAL_TTY_APPROVAL")


if __name__ == "__main__":
    unittest.main()
