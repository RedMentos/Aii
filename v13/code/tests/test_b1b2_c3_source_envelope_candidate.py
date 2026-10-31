"""B1/B2 -> C3 exact-source envelope real Store software adversarial tests."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.common import dumps
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from scripts.run52_b1b2_cross_turn_native import load_fixture, OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run52_b1b2_cross_turn_seed479.json"


class C3SourceEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = FakeRuntime(self.home)
        self.r.cfg.update(OVERRIDES)
        self.consumer = TopicPartitionOfferConsumer(self.r)
        self.f = {x["id"]: x for x in load_fixture(FIXTURE)["fixtures"]}
        self.event = self.r.store.event(self.r.session, self.f["Harbor"]["prior"])
        self.ids = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            result = self.consumer.guarded_offer(
                role, self.event, 0, time.monotonic()+30, operator_opt_in=True)
            self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED")
            self.ids[role] = result["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def build(self, ids=None, event=None, opt=True):
        return build_c3_source_envelope(
            self.r, self.event if event is None else event,
            self.ids if ids is None else ids, operator_opt_in=opt)

    def counts(self):
        return tuple(self.r.store.one("SELECT COUNT(*) AS n FROM "+table)["n"]
                     for table in ("packets","actions","messages"))

    def mutate_packet(self, packet_id, mutate):
        row = self.r.store.one("SELECT payload FROM packets WHERE id=?", (packet_id,))
        payload = json.loads(row["payload"])
        mutate(payload)
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       (dumps(payload), packet_id))

    def test_two_real_stored_offers_create_deterministic_c3_source_prompt(self):
        before = self.counts()
        a = self.build()
        b = self.build()
        self.assertEqual(a["status"], "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL")
        self.assertEqual(a["messages_sha256"], b["messages_sha256"])
        self.assertEqual(a["delivery_authority"], 0)
        self.assertFalse(a["output_committed"])
        self.assertEqual(a["tool_dispatches"], 0)
        self.assertEqual(a["learning_authority"], 0)
        self.assertFalse(a["native_proof"])
        self.assertTrue(a["prompt_only"])
        self.assertEqual(self.counts(), before)
        self.assertEqual([m["role"] for m in a["messages"]], ["system","user"])
        payload = json.loads(a["messages"][1]["content"])
        self.assertEqual(payload["current_source"]["text"], self.f["Harbor"]["prior"])
        self.assertEqual(payload["evidence_policy"],
                         "CURRENT_USER_SOURCE_AND_EXACT_QUOTES_ONLY")
        self.assertFalse(payload["body_hypotheses_are_facts"])
        self.assertEqual([o["role"] for o in payload["body_observations"]],
                         ["B1_DETAIL","B2_GIST"])
        for o in payload["body_observations"]:
            self.assertEqual(o["hypothesis_authority"], "MODEL_HYPOTHESIS_NOT_FACT")
            for q in o["verified_quotes"]:
                self.assertFalse(q["semantic_truth_authority"])

    def test_default_off_and_int_one_not_opt_in(self):
        before = self.counts()
        self.assertEqual(self.build(opt=False)["status"], "OFF")
        self.assertEqual(self.build(opt=1)["status"], "OFF")
        self.assertEqual(self.counts(), before)

    def test_missing_duplicate_or_extra_roles_fail_before_read(self):
        for ids in (
            {}, {"B1_DETAIL":self.ids["B1_DETAIL"]},
            {"B1_DETAIL":self.ids["B1_DETAIL"],
             "B2_GIST":self.ids["B1_DETAIL"]},
            dict(self.ids, C3_LANGUAGE="pkt_fake"),
        ):
            with self.subTest(ids=ids):
                self.assertEqual(self.build(ids=ids)["status"],
                                 "INVALID_EVENT_OR_OFFER_IDS")

    def test_swapped_roles_and_missing_packet_fail(self):
        swapped = {"B1_DETAIL":self.ids["B2_GIST"],
                   "B2_GIST":self.ids["B1_DETAIL"]}
        self.assertEqual(self.build(ids=swapped)["status"],
                         "OFFER_ROLE_OR_REVISION_RED")
        missing = dict(self.ids, B1_DETAIL="pkt_missing")
        self.assertEqual(self.build(ids=missing)["status"],
                         "OFFER_PACKET_NOT_CURRENT")

    def test_foreign_session_and_wrong_generation_fail(self):
        self.r.session = "foreign"
        self.assertNotEqual(self.build()["status"],
                            "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL")
        self.r.session = self.r.store.one(
            "SELECT session_id FROM events WHERE id=?",
            (self.event["event_id"],))["session_id"]
        wrong = dict(self.event, brain_generation_id="gen_forged")
        self.assertEqual(self.build(event=wrong)["status"], "CURRENT_USER_SOURCE_RED")

    def test_later_user_event_invalidates_old_event_envelope(self):
        self.r.store.event(self.r.session, self.f["Willow"]["prior"])
        self.assertEqual(self.build()["status"], "STALE_USER_EVENT_RED")

    def test_tampered_offer_summary_cannot_override_retained_packet(self):
        self.mutate_packet(self.ids["B1_DETAIL"],
                           lambda p: p["offer"].update(summary="FORGED_HYPOTHESIS"))
        self.assertEqual(self.build()["status"], "RETAINED_OFFER_BINDING_RED")

    def test_tampered_query_source_or_missing_query_fails(self):
        offer = self.r.store.one("SELECT payload FROM packets WHERE id=?",
                                 (self.ids["B2_GIST"],))
        qid = json.loads(offer["payload"])["query_packet_id"]
        self.mutate_packet(qid, lambda p: p.update(source_refs=[]))
        self.assertEqual(self.build()["status"], "SOURCE_OR_OFFER_INTEGRITY_RED")

    def test_deleted_current_source_fails_closed(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.event["source_ref"]["source_id"],))
        self.assertNotEqual(self.build()["status"],
                            "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL")

    def test_expired_offer_fails_closed(self):
        self.mutate_packet(self.ids["B1_DETAIL"],
                           lambda p: p.update(deadline_monotonic_ns=0))
        self.assertNotEqual(self.build()["status"],
                            "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL")

    def test_forged_quote_source_outside_scope_fails_closed(self):
        foreign = self.r.store.event(self.r.session, self.f["Willow"]["prior"])
        self.mutate_packet(self.ids["B1_DETAIL"],
                           lambda p: p.update(evidence_refs=[foreign["source_ref"]]))
        self.assertNotEqual(self.build()["status"],
                            "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL")


if __name__ == "__main__":
    unittest.main()
