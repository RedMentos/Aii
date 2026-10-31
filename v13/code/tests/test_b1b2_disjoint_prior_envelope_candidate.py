"""B1/B2 distinct human prior sources through real Store offers into C3 SHADOW."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_disjoint_prior_envelope_candidate import stage_disjoint_prior_envelope
from v13.common import dumps

FINE = "Project Meridian. Fine detail: Option A requires 17 tokens."
GIST = "Project Meridian. Coarse gist: the budget ceiling is 24 tokens."
CURRENT = ("Project Meridian. Choose an eligible option using the "
           "earlier detail and gist.")


class B1B2DisjointPriorEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = FakeRuntime(Path(self.tmp.name))
        self.r.cfg.update(OVERRIDES)
        self.b1 = self.r.store.event(self.r.session, FINE)
        self.b2 = self.r.store.event(self.r.session, GIST)
        self.current = self.r.store.event(self.r.session, CURRENT)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def stage(self, **kwargs):
        return stage_disjoint_prior_envelope(
            self.r, self.b1, self.b2, self.current,
            operator_opt_in=True, **kwargs)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("packets", "actions", "messages"))

    def assert_no_authority(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])

    def test_four_real_role_separated_offers_and_c3_envelope(self):
        before = self.counts()
        result = self.stage()
        self.assertEqual(result["status"],
                         "DISJOINT_PRIOR_C3_ENVELOPE_SHADOW_NO_MODEL_CALL")
        self.assertEqual(result["body_offer_count"], 4)
        self.assertEqual(len(result["messages_sha256"]), 64)
        self.assertNotEqual(
            result["prior_source_ids"]["B1_DETAIL"],
            result["prior_source_ids"]["B2_GIST"])
        self.assertNotEqual(
            result["role_context_ref_sha256"]["B1_DETAIL"],
            result["role_context_ref_sha256"]["B2_GIST"])
        self.assertEqual(tuple(b-a for a,b in zip(before, self.counts())),
                         (8,0,0))
        self.assert_no_authority(result)
        self.assertEqual([m["role"] for m in result["messages"]],
                         ["system","user"])
        payload = json.loads(result["messages"][1]["content"])
        self.assertEqual(payload["current_source"]["text"], CURRENT)
        self.assertFalse(payload["body_hypotheses_are_facts"])
        self.assertEqual([o["role"] for o in payload["body_observations"]],
                         ["B1_DETAIL","B2_GIST"])
        for role, event in (("B1_DETAIL", self.b1), ("B2_GIST", self.b2)):
            offer_id = result["current_offer_packet_ids"][role]
            offer = json.loads(self.r.store.one(
                "SELECT payload FROM packets WHERE id=?", (offer_id,))["payload"])
            query = json.loads(self.r.store.one(
                "SELECT payload FROM packets WHERE id=?",
                (offer["query_packet_id"],))["payload"])
            refs = query["context_source_refs"]
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0]["source_id"], event["source_ref"]["source_id"])
            self.assertEqual(self.r.store.read_source(refs[0]),
                             FINE if role == "B1_DETAIL" else GIST)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"], 0)

    def test_default_off_integer_optin_and_forged_tty_never_call_runner(self):
        before = self.counts()
        for kwargs in (
            {"operator_opt_in":False},
            {"operator_opt_in":1},
            {"operator_opt_in":True, "approval_receipt":{"approved":True}},
        ):
            with self.subTest(kwargs=kwargs):
                result = stage_disjoint_prior_envelope(
                    self.r, self.b1, self.b2, self.current, **kwargs)
                self.assertIn(result["status"],
                              ("OFF","REAL_TTY_APPROVAL_UNSUPPORTED"))
                self.assertFalse(result["runner_called"])
                self.assert_no_authority(result)
        self.assertEqual(self.counts(), before)

    def test_wrong_topic_ambiguous_and_identical_sources_preflight_red(self):
        wrong = self.r.store.event(
            self.r.session, "Project Willow. Coarse gist: 24 tokens.")
        current_w = self.r.store.event(self.r.session, CURRENT)
        before = self.counts()
        result = stage_disjoint_prior_envelope(
            self.r, self.b1, wrong, current_w, operator_opt_in=True)
        self.assertEqual(result["status"], "TOPIC_SCOPE_RED")
        self.assertFalse(result["runner_called"])
        self.assertEqual(self.counts(), before)

        with tempfile.TemporaryDirectory() as d:
            r = FakeRuntime(Path(d))
            r.cfg.update(OVERRIDES)
            try:
                a = r.store.event(r.session, FINE)
                b = r.store.event(r.session, FINE)
                c = r.store.event(r.session, CURRENT)
                same = stage_disjoint_prior_envelope(
                    r, a, b, c, operator_opt_in=True)
                self.assertEqual(same["status"],
                                 "NOT_DISJOINT_PRIOR_SOURCES_RED")
            finally:
                r.close()

    def test_stale_user_and_reversed_order_fail_before_model(self):
        self.r.store.event(self.r.session, "Project Meridian. Later USER turn.")
        stale = self.stage()
        self.assertEqual(stale["status"], "TEMPORAL_OR_STALE_USER_RED")
        self.assertFalse(stale["runner_called"])
        reversed_prior = stage_disjoint_prior_envelope(
            self.r, self.b2, self.b1, self.current,
            operator_opt_in=True)
        self.assertEqual(reversed_prior["status"], "TEMPORAL_OR_STALE_USER_RED")

    def test_revoked_prior_fails_closed(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.b1["source_ref"]["source_id"],))
        result = self.stage()
        self.assertEqual(result["status"], "SOURCE_PREFLIGHT_INTEGRITY_RED")
        self.assertFalse(result["runner_called"])
        self.assert_no_authority(result)

    def test_second_stage_rejected_before_duplicate_offers(self):
        first = self.stage()
        self.assertEqual(first["status"],
                         "DISJOINT_PRIOR_C3_ENVELOPE_SHADOW_NO_MODEL_CALL")
        before = self.counts()
        second = self.stage()
        self.assertEqual(second["status"], "EXISTING_OFFER_RED")
        self.assertFalse(second["runner_called"])
        self.assertEqual(self.counts(), before)

    def test_cross_role_query_context_tamper_refused(self):
        original = TopicPartitionOfferConsumer.guarded_offer
        def tamper(consumer, role, event, version, deadline, **kwargs):
            result = original(consumer, role, event, version, deadline, **kwargs)
            if (role == "B2_GIST" and event["event_id"] == self.current["event_id"]
                    and result["status"] == "SHADOW_OFFER_PRODUCED"):
                qid = result["query_packet_id"]
                row = self.r.store.one(
                    "SELECT payload FROM packets WHERE id=?", (qid,))
                packet = json.loads(row["payload"])
                packet["context_source_refs"] = [self.b1["source_ref"]]
                with self.r.store.tx() as db:
                    db.execute("UPDATE packets SET payload=? WHERE id=?",
                               (dumps(packet), qid))
            return result
        with patch.object(TopicPartitionOfferConsumer, "guarded_offer",
                          autospec=True, side_effect=tamper):
            result = self.stage()
        self.assertEqual(result["status"], "ROLE_CONTEXT_SOURCE_RED")
        self.assertTrue(result["shadow_packets_may_exist"])
        self.assert_no_authority(result)


if __name__ == "__main__":
    unittest.main()
