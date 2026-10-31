"""Run61 B1/B2->C3->F1/F5->C6 v2 real Store SHADOW integration tests."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer, _TopicStateView
from v13.b1b2_causal_context_candidate import _project_scope
from v13.run61_crossorgan_c6_v2_shadow_candidate import stage_run61_crossorgan_c6_v2_shadow
from v13.run58_crossorgan_c6_shadow_candidate import stage_crossorgan_c6_shadow
from scripts.run51_f1f5_second_attempt_native import load_fixture
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run58_crossorgan_c6_shadow_candidate import CypressRuntime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/run51_f1f5_second_attempt_seed467.json")
GOOD_V2 = "The budget for Project Cypress is 64 euros."
GOOD_V1 = "Project Cypress budget is 64 Euro."


class Run61CrossOrganC6V2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = CypressRuntime(Path(self.tmp.name))
        self.r.cfg.update(OVERRIDES)
        self.fixture = load_fixture(FIXTURE)["fixtures"][0]
        correction = self.r.store.event(
            self.r.session, self.fixture["correction_event"])
        self.mid = self.r.memory.feedback(
            correction["event_id"], "fact", self.fixture["value"],
            permission="record", key=self.fixture["key"], scope="session")
        self.current = self.r.store.event(
            self.r.session, self.fixture["followup"])
        self.ids = {}
        consumer = TopicPartitionOfferConsumer(self.r)
        for role in ("B1_DETAIL", "B2_GIST"):
            for event in (correction, self.current):
                result = consumer.guarded_offer(
                    role, event, 0, time.monotonic() + 30,
                    operator_opt_in=True)
                self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED")
                if event is self.current:
                    self.ids[role] = result["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def stage(self, callback=None, **kwargs):
        return stage_run61_crossorgan_c6_v2_shadow(
            self.r, self.current, self.ids,
            callback or (lambda b, f: GOOD_V2),
            operator_opt_in=True, callback_opt_in=True, **kwargs)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("packets", "actions", "messages"))

    def discard(self, result):
        if "draft_message_id" not in result:
            return
        with self.r.store.tx() as db:
            db.execute("DELETE FROM messages WHERE id=?",
                       (result["draft_message_id"],))
            db.execute("DELETE FROM actions WHERE id=?",
                       (result["c5_action_id"],))
            db.execute("DELETE FROM packets WHERE event_id=? "
                       "AND kind IN ('ActionIntent','CorollaryCopy')",
                       (self.current["event_id"],))

    def assert_no_authority(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertNotIn("candidate_text", result)
        self.assertNotIn("messages", result)

    def test_source_bound_new_phrase_needs_real_tty_not_output(self):
        observed = {}
        def callback(body, f1f5):
            observed["body"] = body
            observed["f1f5"] = f1f5
            return GOOD_V2
        before = self.counts()
        result = self.stage(callback)
        self.assertEqual(result["status"],
                         "RUN61_C6_V2_PREFLIGHT_ONLY_NEEDS_REAL_TTY")
        self.assertEqual(result["c6_status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assertEqual(len(result["c6_fingerprint_sha256"]), 64)
        self.assertEqual(len(result["body_envelope_sha256"]), 64)
        self.assertEqual([m["role"] for m in observed["body"]],
                         ["system", "user"])
        self.assertIn("64 Euro", observed["f1f5"][0]["content"])
        self.assertEqual(tuple(b-a for a,b in zip(before, self.counts())),
                         (2,1,1))
        self.assert_no_authority(result)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"], 0)

    def test_original_run58_rejects_same_safe_phrase(self):
        old = stage_crossorgan_c6_shadow(
            self.r, self.current, self.ids, lambda b,f: GOOD_V2,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(old["status"], "CROSSORGAN_C6_GROUNDING_RED")
        self.assert_no_authority(old)
        self.discard(old)
        new = self.stage()
        self.assertEqual(new["status"],
                         "RUN61_C6_V2_PREFLIGHT_ONLY_NEEDS_REAL_TTY")

    def test_wrong_amount_negation_tool_claim_remain_red(self):
        for candidate in (
            "The budget for Project Cypress is 65 euros.",
            "Project Cypress budget is not 64 Euro.",
            "Project Cypress budget is 64 Euro. I will execute a tool.",
        ):
            with self.subTest(candidate=candidate):
                result = self.stage(lambda b,f: candidate)
                self.assertEqual(result["status"], "RUN61_C6_V2_GROUNDING_RED")
                self.assertIsNone(result["c6_fingerprint_sha256"])
                self.assert_no_authority(result)
                self.discard(result)

    def test_packet_tamper_inside_callback_refused_before_draft(self):
        def tamper(body, f1f5):
            with self.r.store.tx() as db:
                db.execute("UPDATE packets SET payload=? WHERE id=?",
                           ('{"tampered":true}', self.ids["B1_DETAIL"]))
            return GOOD_V2
        result = self.stage(tamper)
        self.assertEqual(result["status"], "RUN61_TEMPORAL_DRAFT_RED")
        self.assertTrue(result["callback_invoked"])
        self.assert_no_authority(result)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='DRAFT'")["n"], 0)

    def test_b2_retained_state_drift_inside_callback_refused(self):
        topic = next(iter(_project_scope(self.fixture["followup"])))
        view = _TopicStateView(
            self.r.store, "B2_GIST", self.r.session,
            self.current["brain_generation_id"],
            self.r.models.revision("B2_GIST"), topic)
        def tamper(body, f1f5):
            with self.r.store.tx() as db:
                db.execute("UPDATE states SET payload=? WHERE key=?",
                           (json.dumps({"tampered":True}), view.partition_key))
            return GOOD_V2
        result = self.stage(tamper)
        self.assertEqual(result["status"], "RUN61_TEMPORAL_DRAFT_RED")
        self.assert_no_authority(result)

    def test_newer_user_inside_callback_refused_before_draft(self):
        def mutate(body, f1f5):
            self.r.store.event(self.r.session,
                               "Project Birch budget is 43 Euro.")
            return GOOD_V2
        result = self.stage(mutate)
        self.assertEqual(result["status"], "RUN61_TEMPORAL_DRAFT_RED")
        self.assert_no_authority(result)

    def test_correction_revoked_during_callback_refused(self):
        def revoke(body, f1f5):
            self.r.memory.forget(self.mid)
            return GOOD_V2
        result = self.stage(revoke)
        self.assertEqual(result["status"], "RUN61_TEMPORAL_DRAFT_RED")
        self.assert_no_authority(result)

    def test_duplicate_output_refuses_before_second_generator(self):
        first = self.stage()
        self.assertEqual(first["status"],
                         "RUN61_C6_V2_PREFLIGHT_ONLY_NEEDS_REAL_TTY")
        before = self.counts()
        called = []
        second = self.stage(lambda b,f: called.append(True) or GOOD_V2)
        self.assertEqual(second["status"], "EXISTING_OUTPUT_OR_ACTION_RED")
        self.assertEqual(called, [])
        self.assertEqual(self.counts(), before)
        self.assert_no_authority(second)

    def test_invalid_offer_refuses_before_generator(self):
        bad = dict(self.ids, B2_GIST=self.ids["B1_DETAIL"])
        called = []
        result = stage_run61_crossorgan_c6_v2_shadow(
            self.r, self.current, bad,
            lambda b,f: called.append(True) or GOOD_V2,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "BODY_SOURCE_ENVELOPE_RED")
        self.assertEqual(called, [])
        self.assert_no_authority(result)

    def test_optin_and_forged_tty_refuse_without_generator(self):
        called = []
        callback = lambda b,f: called.append(True) or GOOD_V2
        for kwargs in (
            {"operator_opt_in":False, "callback_opt_in":True},
            {"operator_opt_in":1, "callback_opt_in":True},
            {"operator_opt_in":True, "callback_opt_in":False},
            {"operator_opt_in":True, "callback_opt_in":True,
             "approval_receipt":{"approved":True}},
        ):
            with self.subTest(kwargs=kwargs):
                result = stage_run61_crossorgan_c6_v2_shadow(
                    self.r, self.current, self.ids, callback, **kwargs)
                self.assertIn(result["status"],
                              ("OFF", "REAL_TTY_APPROVAL_UNSUPPORTED"))
                self.assert_no_authority(result)
        self.assertEqual(called, [])

    def test_offer_tamper_after_c6_preflight_downgrades(self):
        from v13 import run61_crossorgan_c6_v2_shadow_candidate as module
        original = module.preflight_budget_lexical_v2
        def tamper_after(*args, **kwargs):
            result = original(*args, **kwargs)
            self.assertEqual(result["status"], "NEEDS_REAL_TTY_APPROVAL")
            with self.r.store.tx() as db:
                db.execute("UPDATE packets SET payload=? WHERE id=?",
                           ('{"tampered":true}', self.ids["B1_DETAIL"]))
            return result
        with patch.object(module, "preflight_budget_lexical_v2",
                          side_effect=tamper_after):
            result = self.stage()
        self.assertEqual(result["status"], "RUN61_BODY_OFFER_LIFECYCLE_RED")
        self.assertTrue(result["shadow_draft_may_exist"])
        self.assertNotIn("c6_fingerprint_sha256", result)
        self.assert_no_authority(result)


if __name__ == "__main__":
    unittest.main()
