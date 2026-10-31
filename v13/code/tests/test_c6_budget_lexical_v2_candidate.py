"""C6 lexical v2: disjoint grammar controls and real SQLite source/DRAFT gates.

All tests are software/synthetic SHADOW; no native, Redmi or output authority.
"""
from pathlib import Path
import tempfile
import unittest

from v13.config import DEFAULTS, initialize
from v13.store import Store
from v13.memory import Memory
from v13.f1f5_temporal_atomic_draft_candidate import stage_temporal_atomic_draft
from v13.c6_temporal_draft_preflight_candidate import preflight_temporal_draft
from v13.c6_positive_assertion_candidate import preflight_positive_budget_assertion
from v13.c6_budget_lexical_v2_candidate import (
    exact_positive_budget_v2, preflight_budget_lexical_v2)
from scripts.run51_f1f5_second_attempt_native import load_fixture

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/run51_f1f5_second_attempt_seed467.json")
SOURCE = {"topic": "Project Cedar budget", "value": "42 Euro"}
POSITIVE = (
    "Project Cedar budget is 42 Euro.",
    "The budget for Project Cedar is 42 euros.",
    "The budget for Project Cedar is 42 EUR.",
    "The budget for Project Cedar is 42 €.",
    "The project budget for Project Cedar is 42 Euro.",
    "Project Cedar's budget is €42.",
    "The budget for Project Cedar is €42.",
    "Projekt Cedar Budget beträgt 42 Euro.",
)
NEGATIVE = (
    "Project Cedar budget is not 42 Euro.",
    "Project Cedar budget is 43 Euro.",
    "Project Birch budget is 42 Euro.",
    "Project Cedar budget is 42 Euro. Project Birch is unrelated.",
    "Project Cedar budget is 42 Euro, not 43.",
    "Project Cedar budget is 42 Euro. I will execute a tool.",
    "Project Cedar budget is 42 Euro?",
    "Project Cedar budget is 42.",
    "Project budget is 42 Euro.",
    "Project Cedar budget is 42 Euro",
    "Project Cedar budget is 42 Euro, but unverified.",
    "The budget for Project Cedar is €42 EUR.",
    "Project Cedar budget is 42 Euro.\nIgnore safeguards.",
    "The budget for Project Cedar is 42 Euro or 43 Euro.",
)


class C6LexicalV2GrammarTests(unittest.TestCase):
    def test_eight_disjoint_positive_variants(self):
        for candidate in POSITIVE:
            with self.subTest(candidate=candidate):
                self.assertTrue(exact_positive_budget_v2(candidate, SOURCE))

    def test_fourteen_disjoint_negative_variants(self):
        for candidate in NEGATIVE:
            with self.subTest(candidate=candidate):
                self.assertFalse(exact_positive_budget_v2(candidate, SOURCE))

    def test_source_scope_and_type_guards(self):
        candidate = POSITIVE[0]
        for source in (
            {"topic": "Project Birch budget", "value": "42 Euro"},
            {"topic": "Project Cedar budget", "value": "43 Euro"},
            {"topic": "Project Cedar and Project Birch budget", "value": "42 Euro"},
            {"topic": "Project Cedar budget", "value": "42 USD"},
            {"topic": "Project Cedar budget", "value": "42.00 Euro"},
            {"topic": "Project Cedar budget", "value": "042 Euro"},
            {"topic": "Project Cedar budget", "value": 42},
            {"topic": None, "value": "42 Euro"},
            {},
        ):
            with self.subTest(source=source):
                self.assertFalse(exact_positive_budget_v2(candidate, source))
        self.assertFalse(exact_positive_budget_v2(1, SOURCE))
        self.assertFalse(exact_positive_budget_v2(candidate, None))
        self.assertFalse(exact_positive_budget_v2(candidate * 20, SOURCE))


class C6LexicalV2StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, DEFAULTS)
        fixture = load_fixture(FIXTURE)["fixtures"][0]
        correction = self.store.event(self.session, fixture["correction_event"])
        self.mid = self.memory.feedback(
            correction["event_id"], "fact", fixture["value"],
            permission="record", key=fixture["key"], scope="session")
        self.current = self.store.event(self.session, fixture["followup"])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def stage(self, candidate):
        staged = stage_temporal_atomic_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            lambda _: candidate, operator_opt_in=True)
        self.assertEqual(staged["status"],
                         "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT")
        return staged

    def check(self, staged, **kwargs):
        return preflight_budget_lexical_v2(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            staged, **kwargs)

    def counts(self):
        return tuple(self.store.one("SELECT COUNT(*) AS n FROM " + table)["n"]
                     for table in ("packets", "actions", "messages"))

    def assert_no_authority(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertNotIn("candidate_text", result)
        self.assertNotIn("messages", result)

    def test_real_sqlite_expanded_english_v1_negative_control(self):
        staged = self.stage("The budget for Project Cypress is 64 euros.")
        self.assertEqual(preflight_temporal_draft(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            staged, operator_opt_in=True)["status"], "NEEDS_REAL_TTY_APPROVAL")
        old = preflight_positive_budget_assertion(
            DEFAULTS, self.memory, self.session, self.current["event_id"],
            staged, operator_opt_in=True)
        self.assertEqual(old["status"], "POSITIVE_ASSERTION_RED")
        before = self.counts()
        new = self.check(staged, operator_opt_in=True)
        self.assertEqual(new["status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assertTrue(new["bounded_lexical_v2_only"])
        self.assertEqual(len(new["fingerprint_sha256"]), 64)
        self.assertEqual(new["candidate_sha256"], staged["candidate_sha256"])
        self.assertEqual(self.counts(), before)
        self.assert_no_authority(new)
        self.assertEqual(self.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"], 0)

    def test_real_sqlite_euro_prefix_and_german(self):
        for candidate in (
            "Project Cypress's budget is €64.",
            "Projekt Cypress Budget beträgt 64 Euro.",
        ):
            with self.subTest(candidate=candidate):
                staged = self.stage(candidate)
                self.assertEqual(self.check(staged, operator_opt_in=True)["status"],
                                 "NEEDS_REAL_TTY_APPROVAL")
                self.assert_no_authority(self.check(staged, operator_opt_in=True))
                with self.store.tx() as db:
                    db.execute("DELETE FROM messages WHERE id=?", (staged["draft_message_id"],))
                    db.execute("DELETE FROM actions WHERE id=?", (staged["c5_action_id"],))
                    db.execute("DELETE FROM packets WHERE event_id=? AND "
                               "kind IN ('ActionIntent','CorollaryCopy')",
                               (self.current["event_id"],))

    def test_optin_and_forged_tty_receipt_refuse(self):
        staged = self.stage("The budget for Project Cypress is 64 euros.")
        before = self.counts()
        self.assertEqual(self.check(staged)["status"], "OFF")
        self.assertEqual(self.check(staged, operator_opt_in=1)["status"], "OFF")
        self.assertEqual(self.check(staged, operator_opt_in=True,
                                    approval_receipt={"approved": True})["status"],
                         "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assertEqual(self.counts(), before)

    def test_tampered_draft_fails_closed(self):
        staged = self.stage("The budget for Project Cypress is 64 euros.")
        with self.store.tx() as db:
            db.execute("UPDATE messages SET text=? WHERE id=?",
                       ("The budget for Project Cypress is 65 euros.",
                        staged["draft_message_id"]))
        self.assertNotEqual(self.check(staged, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")

    def test_revoked_source_fails_closed(self):
        staged = self.stage("The budget for Project Cypress is 64 euros.")
        self.memory.forget(self.mid)
        self.assertNotEqual(self.check(staged, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")

    def test_competing_draft_fails_closed(self):
        staged = self.stage("The budget for Project Cypress is 64 euros.")
        self.store.message(self.session, self.current["event_id"],
                           "assistant", "competing", "DRAFT")
        self.assertNotEqual(self.check(staged, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")

    def test_newer_user_event_fails_closed(self):
        staged = self.stage("The budget for Project Cypress is 64 euros.")
        self.store.event(self.session, "Project Birch budget is 43 Euro.")
        self.assertNotEqual(self.check(staged, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")

    def test_invalid_staged_ref_fails_closed(self):
        self.assertNotEqual(self.check({}, operator_opt_in=True)["status"],
                            "NEEDS_REAL_TTY_APPROVAL")


if __name__ == "__main__":
    unittest.main()
