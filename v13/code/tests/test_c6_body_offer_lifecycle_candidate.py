"""Independent B1/B2 offer lifecycle counterexamples; real SQLite, synthetic body."""
from pathlib import Path
import json
import tempfile
import time
import unittest

from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer, _TopicStateView
from v13.b1b2_causal_context_candidate import _project_scope
from v13.c6_body_offer_lifecycle_candidate import stage_offer_lifecycle_c6_shadow
from v13.run58_crossorgan_c6_shadow_candidate import stage_crossorgan_c6_shadow
from scripts.run51_f1f5_second_attempt_native import load_fixture
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run58_crossorgan_c6_shadow_candidate import CypressRuntime


FIXTURE = (Path(__file__).resolve().parents[1]
           / "docs/fixtures/run51_f1f5_second_attempt_seed467.json")
GOOD = "Project Cypress budget is 64 Euro."


class C6BodyOfferLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = CypressRuntime(Path(self.temp.name))
        self.r.cfg.update(OVERRIDES)
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        correction = self.r.store.event(self.r.session, self.f["correction_event"])
        self.mid = self.r.memory.feedback(
            correction["event_id"], "fact", self.f["value"],
            permission="record", key=self.f["key"], scope="session")
        self.current = self.r.store.event(self.r.session, self.f["followup"])
        self.ids = {}
        consumer = TopicPartitionOfferConsumer(self.r)
        for role in ("B1_DETAIL", "B2_GIST"):
            for event in (correction, self.current):
                result = consumer.guarded_offer(
                    role, event, 0, time.monotonic() + 30, operator_opt_in=True)
                self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED")
                if event is self.current:
                    self.ids[role] = result["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def run_guarded(self, callback, **kw):
        return stage_offer_lifecycle_c6_shadow(
            self.r, self.current, self.ids, callback,
            operator_opt_in=True, callback_opt_in=True, **kw)

    def _counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("packets", "actions", "messages"))

    def _assert_no_authority(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertNotIn("candidate_text", result)
        self.assertNotIn("messages", result)

    def _tamper_packet(self, role):
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       ('{"tampered":true}', self.ids[role]))

    def test_valid_source_is_still_read_only_and_needs_real_tty(self):
        before = self._counts()
        result = self.run_guarded(lambda b, f: GOOD)
        self.assertEqual(result["status"],
                         "LIFECYCLE_C6_PREFLIGHT_ONLY_NEEDS_REAL_TTY")
        self.assertEqual(result["c6_status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assertEqual(len(result["body_envelope_sha256"]), 64)
        self.assertEqual(len(result["c6_fingerprint_sha256"]), 64)
        self.assertTrue(result["body_offer_lifecycle_rechecked"])
        self._assert_no_authority(result)
        self.assertEqual(tuple(b - a for a, b in zip(before, self._counts())),
                         (2, 1, 1))
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"], 0)

    def test_original_run58_can_miss_offer_tamper_after_envelope(self):
        def mutate(body, f1f5):
            self._tamper_packet("B1_DETAIL")
            return GOOD
        result = stage_crossorgan_c6_shadow(
            self.r, self.current, self.ids, mutate,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"],
                         "CROSSORGAN_C6_PREFLIGHT_ONLY_NEEDS_REAL_TTY")
        self.assertFalse(result["output_committed"])

    def test_packet_tamper_inside_callback_is_red_before_draft(self):
        def mutate(body, f1f5):
            self._tamper_packet("B1_DETAIL")
            return GOOD
        result = self.run_guarded(mutate)
        self.assertEqual(result["status"], "BODY_OFFER_LIFECYCLE_RED")
        self.assertTrue(result["callback_invoked"])
        self.assertEqual(result["underlying_status"], "TEMPORAL_DRAFT_RED")
        self._assert_no_authority(result)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='DRAFT'")["n"], 0)

    def test_retained_b2_state_tamper_inside_callback_is_red(self):
        topic = next(iter(_project_scope(self.f["followup"])))
        view = _TopicStateView(
            self.r.store, "B2_GIST", self.r.session,
            self.current["brain_generation_id"],
            self.r.models.revision("B2_GIST"), topic)
        def mutate(body, f1f5):
            with self.r.store.tx() as db:
                db.execute("UPDATE states SET payload=? WHERE key=?",
                           (json.dumps({"tampered": True}), view.partition_key))
            return GOOD
        result = self.run_guarded(mutate)
        self.assertEqual(result["status"], "BODY_OFFER_LIFECYCLE_RED")
        self._assert_no_authority(result)

    def test_newer_authoritative_user_during_callback_is_red(self):
        def mutate(body, f1f5):
            self.r.store.event(self.r.session, "Project Lark budget is 19 Euro.")
            return GOOD
        result = self.run_guarded(mutate)
        self.assertEqual(result["status"], "BODY_OFFER_LIFECYCLE_RED")
        self._assert_no_authority(result)

    def test_preexisting_offer_tamper_refuses_without_callback_or_writes(self):
        self._tamper_packet("B1_DETAIL")
        calls = []
        before = self._counts()
        result = self.run_guarded(lambda b, f: calls.append(True) or GOOD)
        self.assertEqual(result["status"], "BODY_OFFER_BEFORE_CALLBACK_RED")
        self.assertEqual(calls, [])
        self.assertEqual(self._counts(), before)
        self._assert_no_authority(result)

    def test_opt_in_and_forged_approval_refuse_without_callback(self):
        calls = []
        def callback(body, f1f5):
            calls.append(True)
            return GOOD
        for kwargs in (
            {"operator_opt_in": False, "callback_opt_in": True},
            {"operator_opt_in": 1, "callback_opt_in": True},
            {"operator_opt_in": True, "callback_opt_in": False},
            {"operator_opt_in": True, "callback_opt_in": True,
             "approval_receipt": {"approved": True}},
        ):
            with self.subTest(kwargs=kwargs):
                result = stage_offer_lifecycle_c6_shadow(
                    self.r, self.current, self.ids, callback, **kwargs)
                self.assertIn(result["status"],
                              ("OFF", "REAL_TTY_APPROVAL_UNSUPPORTED"))
                self._assert_no_authority(result)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
