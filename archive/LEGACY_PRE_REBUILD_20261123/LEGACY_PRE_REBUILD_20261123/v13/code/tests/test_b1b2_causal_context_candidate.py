"""Real Store/Cognition B1/B2 future-event context-leak diagnostic and guard."""
from pathlib import Path
import tempfile
import time
import unittest

from scripts import run52_b1b2_cross_turn_native as run52
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.b1b2_causal_context_candidate import causal_body_context, _project_scope

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run52_b1b2_cross_turn_seed479.json"


class CausalBodyContextAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = FakeRuntime(Path(self.temp.name))
        self.r.cfg.update(run52.OVERRIDES)
        self.f = run52.load_fixture(FIXTURE)["fixtures"][0]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def offer(self, role, event):
        return self.r.cognition.offer(role, event, 0, time.monotonic()+30)

    def test_future_source_reaches_frozen_legacy_context_but_candidate_filters(self):
        older = self.r.store.event(self.r.session, self.f["prior"])
        newer = self.r.store.event(self.r.session, self.f["current"])
        for role in run52.ROLES:
            with self.subTest(role=role):
                self.offer(role, newer)
                legacy = self.r.cognition.body_context(role, older)
                self.assertTrue(legacy, "temporal counterexample must actually reproduce")
                self.assertEqual(legacy[0]["source_ref"]["source_id"],
                                 newer["source_ref"]["source_id"])
                guarded = causal_body_context(self.r, role, older, operator_opt_in=True)
                self.assertEqual(guarded["status"], "SHADOW_CONTEXT_FILTERED")
                self.assertEqual(guarded["context"], [])
                self.assertGreaterEqual(guarded["filtered_count"], 1)
                self.assertEqual(guarded["delivery_authority"], 0)
                self.assertEqual(guarded["native_calls"], 0)

    def test_earlier_same_project_source_survives_for_both_roles(self):
        prior = self.r.store.event(self.r.session, self.f["prior"])
        for role in run52.ROLES:
            self.offer(role, prior)
        current = self.r.store.event(self.r.session, self.f["current"])
        for role in run52.ROLES:
            with self.subTest(role=role):
                guarded = causal_body_context(self.r, role, current, operator_opt_in=True)
                self.assertEqual(guarded["status"], "SHADOW_CONTEXT_FILTERED")
                self.assertTrue(guarded["context"])
                self.assertEqual(guarded["context"][0]["source_ref"]["source_id"],
                                 prior["source_ref"]["source_id"])
                self.assertEqual(guarded["filtered_count"], 0)

    def test_unrelated_project_is_not_imported(self):
        prior = self.r.store.event(self.r.session, self.f["prior"])
        for role in run52.ROLES:
            self.offer(role, prior)
        other = run52.load_fixture(FIXTURE)["fixtures"][1]
        current = self.r.store.event(self.r.session, other["current"])
        for role in run52.ROLES:
            with self.subTest(role=role):
                legacy = self.r.cognition.body_context(role, current)
                self.assertTrue(legacy, "preserve observed generic project-rules false match")
                self.assertEqual(legacy[0]["source_ref"]["source_id"],
                                 prior["source_ref"]["source_id"])
                guarded = causal_body_context(self.r, role, current, operator_opt_in=True)
                self.assertEqual(guarded["status"], "SHADOW_CONTEXT_FILTERED")
                self.assertEqual(guarded["context"], [])

    def test_generic_project_rules_is_not_proper_project_identity(self):
        self.assertEqual(_project_scope(self.f["prior"]), {"harbor"})
        self.assertEqual(_project_scope("Use the earlier project rules."), set())
        self.assertEqual(_project_scope("Project Harbor and Project Willow."), set())

    def test_deleted_prior_source_is_not_imported(self):
        prior = self.r.store.event(self.r.session, self.f["prior"])
        for role in run52.ROLES:
            self.offer(role, prior)
        current = self.r.store.event(self.r.session, self.f["current"])
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (prior["source_ref"]["source_id"],))
        for role in run52.ROLES:
            self.assertEqual(causal_body_context(
                self.r, role, current, operator_opt_in=True)["context"], [])

    def test_missing_user_message_binding_fails_shut(self):
        prior = self.r.store.event(self.r.session, self.f["prior"])
        for role in run52.ROLES:
            self.offer(role, prior)
        current = self.r.store.event(self.r.session, self.f["current"])
        with self.r.store.tx() as db:
            db.execute("UPDATE messages SET status='INTERRUPTED' "
                       "WHERE event_id=? AND role='user'", (prior["event_id"],))
        for role in run52.ROLES:
            guarded = causal_body_context(self.r, role, current, operator_opt_in=True)
            self.assertEqual(guarded["status"], "SHADOW_CONTEXT_FILTERED")
            self.assertEqual(guarded["context"], [])

    def test_current_event_tamper_foreign_session_and_default_off(self):
        current = self.r.store.event(self.r.session, self.f["current"])
        self.assertEqual(causal_body_context(
            self.r, "B2_GIST", current)["status"], "OFF")
        other = self.r.store.new_session("foreign")
        old = self.r.session
        self.r.session = other
        self.assertEqual(causal_body_context(
            self.r, "B2_GIST", current, operator_opt_in=True)["status"],
            "EVENT_OR_CONTEXT_RED")
        self.r.session = old
        with self.r.store.tx() as db:
            db.execute("UPDATE events SET packet='{}' WHERE id=?", (current["event_id"],))
        self.assertEqual(causal_body_context(
            self.r, "B2_GIST", current, operator_opt_in=True)["status"],
            "EVENT_OR_CONTEXT_RED")


if __name__ == "__main__":
    unittest.main()
