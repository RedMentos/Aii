"""Real Cognition.offer synthetic consumer tests for causal/project source guard."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts import run52_b1b2_cross_turn_native as run52
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.b1b2_causal_offer_consumer_candidate import CausalOfferConsumer

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run52_b1b2_cross_turn_seed479.json"


class CausalOfferConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = FakeRuntime(self.home)
        self.r.cfg.update(run52.OVERRIDES)
        self.consumer = CausalOfferConsumer(self.r)
        self.fixtures = run52.load_fixture(FIXTURE)["fixtures"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def offer(self, role, event, opt=True):
        return self.consumer.guarded_offer(
            role, event, 0, time.monotonic()+30, operator_opt_in=opt)

    def packet(self, packet_id):
        return json.loads(self.r.store.one(
            "SELECT payload FROM packets WHERE id=?", (packet_id,))["payload"])

    def counts(self):
        return {kind: self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind=?", (kind,))["n"]
            for kind in ("QueryPacket", "OfferPacket")}

    def test_default_off_no_offer_or_query_state(self):
        event = self.r.store.event(self.r.session, self.fixtures[0]["prior"])
        before = self.counts()
        for opt in (False, None, 0, 1, "yes"):
            self.assertEqual(self.offer("B1_DETAIL", event, opt=opt)["status"], "OFF")
        self.assertEqual(self.counts(), before)

    def test_real_cognition_consumer_retains_earlier_source_for_both_roles(self):
        f = self.fixtures[0]
        prior = self.r.store.event(self.r.session, f["prior"])
        for role in run52.ROLES:
            self.assertEqual(self.offer(role, prior)["status"], "SHADOW_OFFER_PRODUCED")
        current = self.r.store.event(self.r.session, f["current"])
        for role in run52.ROLES:
            with self.subTest(role=role):
                r = self.offer(role, current)
                self.assertEqual(r["status"], "SHADOW_OFFER_PRODUCED")
                query = self.packet(r["query_packet_id"])
                self.assertEqual(query["context_source_refs"][0]["source_id"],
                                 prior["source_ref"]["source_id"])
                self.assertEqual(query["source_refs"][0]["source_id"],
                                 current["source_ref"]["source_id"])
                self.assertEqual(r["delivery_authority"], 0)
                self.assertFalse(r["native_proof"])

    def test_real_consumer_excludes_cross_project_pseudo_entity(self):
        harbor = self.fixtures[0]
        willow = self.fixtures[1]
        prior = self.r.store.event(self.r.session, harbor["prior"])
        for role in run52.ROLES:
            self.assertEqual(self.offer(role, prior)["status"], "SHADOW_OFFER_PRODUCED")
        current = self.r.store.event(self.r.session, willow["current"])
        for role in run52.ROLES:
            with self.subTest(role=role):
                before = self.counts()
                state_before = self.r.store.state(role+":"+self.r.session)
                r = self.offer(role, current)
                self.assertEqual(r["status"], "CROSS_TOPIC_RETAINED_STATE_RED")
                self.assertFalse(r["runner_called"])
                self.assertEqual(self.counts(), before)
                self.assertEqual(self.r.store.state(role+":"+self.r.session), state_before)

    def test_unguarded_cognition_injects_foreign_prior_hypothesis_even_with_filtered_context(self):
        harbor = self.fixtures[0]
        willow = self.fixtures[1]
        captured = []
        original_get = self.r.pool.get

        def capture_body(role):
            body = original_get(role)
            original_generate = body.generate
            def generate(messages, *args, **kwargs):
                query = json.loads(messages[1]["content"])
                captured.append(query)
                raw = original_generate(messages, *args, **kwargs)
                if "Project Harbor" in query.get("source_segments", [{}])[0].get("text", ""):
                    obj = json.loads(raw[0])
                    obj["summary"] = "HARBOR_ONLY_120_EUROS"
                    return [json.dumps(obj)]
                return raw
            body.generate = generate
            return body

        self.r.pool.get = capture_body
        prior = self.r.store.event(self.r.session, harbor["prior"])
        self.consumer.offer("B1_DETAIL", prior, 0, time.monotonic()+30)
        current = self.r.store.event(self.r.session, willow["current"])
        # Direct inherited Cognition.offer intentionally bypasses guarded_offer.
        # It still uses filtered source context but blindly injects prior summary.
        offer = self.consumer.offer("B1_DETAIL", current, 0, time.monotonic()+30)
        query_packet = self.packet(offer["query_packet_id"])
        self.assertEqual(query_packet["context_source_refs"], [])
        self.assertEqual(captured[-1]["prior_hypothesis"], "HARBOR_ONLY_120_EUROS")

    def test_older_replay_after_newer_retained_never_invokes_offer(self):
        f = self.fixtures[0]
        older = self.r.store.event(self.r.session, f["prior"])
        newer = self.r.store.event(self.r.session, f["current"])
        for role in run52.ROLES:
            self.assertEqual(self.offer(role, newer)["status"], "SHADOW_OFFER_PRODUCED")
            before = self.counts()
            state_before = self.r.store.state(role+":"+self.r.session)
            replay = self.offer(role, older)
            self.assertEqual(replay["status"], "STALE_REPLAY_NO_OFFER")
            self.assertFalse(replay["runner_called"])
            self.assertEqual(self.counts(), before)
            self.assertEqual(self.r.store.state(role+":"+self.r.session), state_before)

    def test_duplicate_same_event_replay_never_mutates_retained_state(self):
        f = self.fixtures[0]
        event = self.r.store.event(self.r.session, f["prior"])
        for role in run52.ROLES:
            self.assertEqual(self.offer(role, event)["status"], "SHADOW_OFFER_PRODUCED")
            before = self.counts()
            self.assertEqual(self.offer(role, event)["status"], "STALE_REPLAY_NO_OFFER")
            self.assertEqual(self.counts(), before)

    def test_deleted_source_and_foreign_session_fail_before_query(self):
        event = self.r.store.event(self.r.session, self.fixtures[0]["prior"])
        before = self.counts()
        other = self.r.store.new_session("foreign")
        old = self.r.session
        self.r.session = other
        self.assertEqual(self.offer("B1_DETAIL", event)["status"],
                         "EVENT_OR_RETAINED_STATE_RED")
        self.r.session = old
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (event["source_ref"]["source_id"],))
        self.assertEqual(self.offer("B1_DETAIL", event)["status"],
                         "EVENT_OR_RETAINED_STATE_RED")
        self.assertEqual(self.counts(), before)

    def test_restart_persisted_retained_offer_still_rejects_old_replay(self):
        f = self.fixtures[0]
        older = self.r.store.event(self.r.session, f["prior"])
        newer = self.r.store.event(self.r.session, f["current"])
        self.assertEqual(self.offer("B2_GIST", newer)["status"], "SHADOW_OFFER_PRODUCED")
        old_session = self.r.session
        self.r.close()
        self.r = FakeRuntime(self.home)
        self.r.cfg.update(run52.OVERRIDES)
        self.r.session = old_session
        self.consumer = CausalOfferConsumer(self.r)
        before = self.counts()
        self.assertEqual(self.offer("B2_GIST", older)["status"], "STALE_REPLAY_NO_OFFER")
        self.assertEqual(self.counts(), before)


if __name__ == "__main__":
    unittest.main()
