"""C6 strict positive assertion: real Store false-positive counterexamples."""
from pathlib import Path
import tempfile
import unittest

from v13.config import DEFAULTS, initialize
from v13.store import Store
from v13.memory import Memory
from v13.f1f5_temporal_atomic_draft_candidate import stage_temporal_atomic_draft
from v13.c6_temporal_draft_preflight_candidate import preflight_temporal_draft
from v13.c6_positive_assertion_candidate import (
    exact_positive_budget_assertion, preflight_positive_budget_assertion)
from scripts.run51_f1f5_second_attempt_native import load_fixture

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class C6PositiveAssertionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, DEFAULTS)
        f = load_fixture(FIXTURE)["fixtures"][0]
        correction = self.store.event(self.session, f["correction_event"])
        self.mid = self.memory.feedback(
            correction["event_id"], "fact", f["value"],
            permission="record", key=f["key"], scope="session")
        self.current = self.store.event(self.session, f["followup"])

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def stage(self, candidate):
        result = stage_temporal_atomic_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            lambda _: candidate, operator_opt_in=True)
        self.assertEqual(result["status"],
                         "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT")
        return result

    def base(self, staged):
        return preflight_temporal_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            staged, operator_opt_in=True)

    def strict(self, staged, **kwargs):
        return preflight_positive_budget_assertion(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            staged, **kwargs)

    def counts(self):
        return tuple(self.store.one("SELECT COUNT(*) AS n FROM "+table)["n"]
                     for table in ("packets", "actions", "messages"))

    def discard_staged(self, staged):
        with self.store.tx() as db:
            db.execute("DELETE FROM messages WHERE id=?", (staged["draft_message_id"],))
            db.execute("DELETE FROM actions WHERE id=?", (staged["c5_action_id"],))
            db.execute("DELETE FROM packets WHERE event_id=? "
                       "AND kind IN ('ActionIntent','CorollaryCopy')",
                       (self.current["event_id"],))

    def test_original_preflight_false_positives_are_strictly_refused(self):
        candidates = (
            "Project Cypress budget is not 64 Euro.",
            "Project Lark budget is 64 Euro. Project Cypress is unrelated.",
            "Project Cypress budget is 64 Euro. Project Lark is unrelated.",
            "Project Cypress budget is 64 Euro, but that is unverified.",
            "Project Cypress budget is 64 Euro. I will execute a tool.",
            "Project Cypress budget is 64 Euro?",
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                staged = self.stage(candidate)
                before = self.counts()
                self.assertEqual(self.base(staged)["status"], "NEEDS_REAL_TTY_APPROVAL")
                result = self.strict(staged, operator_opt_in=True)
                self.assertEqual(result["status"], "POSITIVE_ASSERTION_RED")
                self.assertEqual(result["delivery_authority"], 0)
                self.assertNotIn("candidate_text", result)
                self.assertEqual(self.counts(), before)
                self.discard_staged(staged)

    def test_positive_english_variants_still_need_real_approval(self):
        for candidate in ("Project Cypress budget is 64 Euro.",
                          "The budget for Project Cypress is 64 EUR.",
                          "Projekt Cypress Budget beträgt 64 Euro."):
            with self.subTest(candidate=candidate):
                staged = self.stage(candidate)
                before = self.counts()
                result = self.strict(staged, operator_opt_in=True)
                self.assertEqual(result["status"], "NEEDS_REAL_TTY_APPROVAL")
                self.assertTrue(result["strict_positive_lexical_only"])
                self.assertEqual(result["delivery_authority"], 0)
                self.assertFalse(result["output_committed"])
                self.assertEqual(result["tool_dispatches"], 0)
                self.assertEqual(result["learning_authority"], 0)
                self.assertNotIn("candidate_text", result)
                self.assertEqual(self.counts(), before)
                self.discard_staged(staged)

    def test_source_amount_mismatch_and_extra_number_fail(self):
        for candidate in ("Project Cypress budget is 65 Euro.",
                          "Project Cypress budget is 64 Euro, not 65."):
            with self.subTest(candidate=candidate):
                staged = self.stage(candidate)
                before = self.counts()
                self.assertNotEqual(self.strict(staged, operator_opt_in=True)["status"],
                                    "NEEDS_REAL_TTY_APPROVAL")
                self.assertEqual(self.counts(), before)
                self.discard_staged(staged)

    def test_off_and_forged_approval_never_deliver(self):
        staged = self.stage("Project Cypress budget is 64 Euro.")
        before = self.counts()
        self.assertEqual(self.strict(staged)["status"], "OFF")
        self.assertEqual(self.strict(staged, operator_opt_in=1)["status"], "OFF")
        self.assertEqual(self.strict(staged, operator_opt_in=True,
                                     approval_receipt={"approved": True})["status"],
                         "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assertEqual(self.counts(), before)

    def test_revoked_source_and_tampered_draft_refused(self):
        staged = self.stage("Project Cypress budget is 64 Euro.")
        with self.store.tx() as db:
            db.execute("UPDATE messages SET text=? WHERE id=?",
                       ("Project Cypress budget is 65 Euro.", staged["draft_message_id"]))
        self.assertNotEqual(self.strict(staged, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")
        self.discard_staged(staged)
        staged = self.stage("Project Cypress budget is 64 Euro.")
        self.memory.forget(self.mid)
        self.assertNotEqual(self.strict(staged, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")

    def test_competing_draft_refused(self):
        staged = self.stage("Project Cypress budget is 64 Euro.")
        self.store.message(self.session, self.current["event_id"],
                           "assistant", "other", "DRAFT")
        self.assertNotEqual(self.strict(staged, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")

    def test_pure_grammar_is_bounded_not_semantic(self):
        source = {"topic": "Project Cypress budget", "value": "64 Euro"}
        self.assertTrue(exact_positive_budget_assertion(
            "Project Cypress budget is 64 Euro.", source))
        self.assertFalse(exact_positive_budget_assertion(
            "Project Cypress budget is not 64 Euro.", source))
        self.assertFalse(exact_positive_budget_assertion(
            "Project Cypress budget is 64 Euro. Project Lark is unrelated.", source))
        self.assertFalse(exact_positive_budget_assertion(
            "Project Cypress budget is 64 Euro.", {"topic":"Project Lark budget","value":"64 Euro"}))
        self.assertFalse(exact_positive_budget_assertion(
            "Project Cypress budget is 64 Euro.", {"topic":"Project Cypress budget","value":"65 Euro"}))


if __name__ == "__main__":
    unittest.main()
