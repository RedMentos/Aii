"""Run58 cross-organ real Store B1/B2 C3 F1/F5 C5 C6 SHADOW tests."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.config import DEFAULTS
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.run58_crossorgan_c6_shadow_candidate import stage_crossorgan_c6_shadow
from scripts.run51_f1f5_second_attempt_native import load_fixture
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from scripts.run52_b1b2_cross_turn_native import OVERRIDES

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class Run58CrossOrganC6Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = FakeRuntime(Path(self.temp.name))
        self.r.cfg.update(OVERRIDES)
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        self.correction = self.r.store.event(self.r.session, self.f["correction_event"])
        self.mid = self.r.memory.feedback(
            self.correction["event_id"], "fact", self.f["value"],
            permission="record", key=self.f["key"], scope="session")
        self.current = self.r.store.event(self.r.session, self.f["followup"])
        self.consumer = TopicPartitionOfferConsumer(self.r)
        self.ids = {}
        for role in ("B1_DETAIL","B2_GIST"):
            for event in (self.correction, self.current):
                result = self.consumer.guarded_offer(
                    role, event, 0, time.monotonic()+30, operator_opt_in=True)
                self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED")
                if event is self.current:
                    self.ids[role] = result["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def stage(self, candidate="Project Cypress budget is 64 Euro.", **kwargs):
        return stage_crossorgan_c6_shadow(
            self.r, self.current, self.ids, lambda b, f: candidate,
            operator_opt_in=True, callback_opt_in=True, **kwargs)

    def counts(self):
        return tuple(self.r.store.one("SELECT COUNT(*) AS n FROM "+table)["n"]
                     for table in ("packets","actions","messages"))

    def discard(self, result):
        if "draft_message_id" not in result:
            return
        with self.r.store.tx() as db:
            db.execute("DELETE FROM messages WHERE id=?", (result["draft_message_id"],))
            db.execute("DELETE FROM actions WHERE id=?", (result["c5_action_id"],))
            db.execute("DELETE FROM packets WHERE event_id=? "
                       "AND kind IN ('ActionIntent','CorollaryCopy')",
                       (self.current["event_id"],))

    def test_positive_crossorgan_c6_is_only_read_only_tty_challenge(self):
        observed = {}
        def callback(body, f1f5):
            observed["body"] = body
            observed["f1f5"] = f1f5
            return "Project Cypress budget is 64 Euro."
        before = self.counts()
        result = stage_crossorgan_c6_shadow(
            self.r, self.current, self.ids, callback,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"],
                         "CROSSORGAN_C6_PREFLIGHT_ONLY_NEEDS_REAL_TTY")
        self.assertEqual(result["c6_status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assertEqual(len(result["c6_fingerprint_sha256"]), 64)
        self.assertTrue(result["preflight_only"])
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertNotIn("candidate_text", result)
        self.assertEqual([x["role"] for x in observed["body"]], ["system","user"])
        self.assertEqual([x["role"] for x in observed["f1f5"]], ["system","user"])
        self.assertIn("64 Euro", observed["f1f5"][0]["content"])
        payload = json.loads(observed["body"][1]["content"])
        self.assertEqual(payload["current_source"]["text"], self.f["followup"])
        self.assertFalse(payload["body_hypotheses_are_facts"])
        self.assertEqual(tuple(b-a for a,b in zip(before,self.counts())), (2,1,1))
        draft = self.r.store.one("SELECT status FROM messages WHERE id=?",
                                 (result["draft_message_id"],))
        self.assertEqual(draft["status"], "DRAFT")
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"], 0)

    def test_wrong_amount_negation_cross_project_refused_without_commit(self):
        for candidate in (
            "Project Cypress budget is not 64 Euro.",
            "Project Lark budget is 64 Euro. Project Cypress is unrelated.",
            "Project Cypress budget is 65 Euro.",
        ):
            with self.subTest(candidate=candidate):
                result = self.stage(candidate)
                self.assertEqual(result["status"], "CROSSORGAN_C6_GROUNDING_RED")
                self.assertEqual(result["delivery_authority"], 0)
                self.assertFalse(result["output_committed"])
                self.assertIsNone(result["c6_fingerprint_sha256"])
                self.discard(result)

    def test_default_off_and_forged_approval_never_invoke_callback(self):
        calls = []
        def callback(*args):
            calls.append(True)
            return "Project Cypress budget is 64 Euro."
        for kw in (
            {"operator_opt_in":False,"callback_opt_in":True},
            {"operator_opt_in":1,"callback_opt_in":True},
            {"operator_opt_in":True,"callback_opt_in":False},
            {"operator_opt_in":True,"callback_opt_in":True,
             "approval_receipt":{"approved":True}},
        ):
            result = stage_crossorgan_c6_shadow(
                self.r,self.current,self.ids,callback,**kw)
            self.assertIn(result["status"], ("OFF","REAL_TTY_APPROVAL_UNSUPPORTED"))
        self.assertEqual(calls, [])

    def test_duplicate_role_wrong_event_and_stale_user_refused(self):
        bad = dict(self.ids, B2_GIST=self.ids["B1_DETAIL"])
        calls = []
        result = stage_crossorgan_c6_shadow(
            self.r,self.current,bad,lambda *a:calls.append(True),
            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result["status"], "BODY_SOURCE_ENVELOPE_RED")
        self.assertEqual(calls, [])
        wrong = dict(self.current, brain_generation_id="gen_wrong")
        result = stage_crossorgan_c6_shadow(
            self.r,wrong,self.ids,lambda *a:calls.append(True),
            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result["status"], "BODY_SOURCE_ENVELOPE_RED")
        self.r.store.event(self.r.session, "Project Lark budget changed.")
        result = self.stage()
        self.assertEqual(result["status"], "BODY_SOURCE_ENVELOPE_RED")
        self.assertEqual(calls, [])

    def test_revocation_during_callback_aborts_temporal_draft(self):
        def revoke(body, f1f5):
            self.r.memory.forget(self.mid)
            return "Project Cypress budget is 64 Euro."
        result = stage_crossorgan_c6_shadow(
            self.r,self.current,self.ids,revoke,
            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result["status"], "TEMPORAL_DRAFT_RED")
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='DRAFT'")["n"], 0)

    def test_competing_draft_blocks_c6_preflight(self):
        def compete(body, f1f5):
            self.r.store.message(self.r.session,self.current["event_id"],
                                 "assistant","competing","DRAFT")
            return "Project Cypress budget is 64 Euro."
        result = stage_crossorgan_c6_shadow(
            self.r,self.current,self.ids,compete,
            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result["status"], "CROSSORGAN_C6_GROUNDING_RED")
        self.assertEqual(result["delivery_authority"], 0)
        self.assertIsNone(result["c6_fingerprint_sha256"])


if __name__ == "__main__":
    unittest.main()
