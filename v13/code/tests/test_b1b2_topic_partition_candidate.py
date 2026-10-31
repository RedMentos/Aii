"""Topic-partitioned real Store/Cognition software consumer adversarial tests."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts import run52_b1b2_cross_turn_native as run52
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run52_b1b2_cross_turn_seed479.json"


class TopicPartitionOfferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = FakeRuntime(self.home)
        self.r.cfg.update(run52.OVERRIDES)
        self.consumer = TopicPartitionOfferConsumer(self.r)
        self.f = {f["id"]: f for f in run52.load_fixture(FIXTURE)["fixtures"]}

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def event(self, project, phase):
        return self.r.store.event(self.r.session, self.f[project][phase])

    def offer(self, role, event, opt=True):
        return self.consumer.guarded_offer(
            role, event, 0, time.monotonic() + 30, operator_opt_in=opt)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind=?", (k,))["n"]
            for k in ("QueryPacket", "OfferPacket"))

    def query(self, result):
        return json.loads(self.r.store.one(
            "SELECT payload FROM packets WHERE id=?",
            (result["query_packet_id"],))["payload"])

    def capture_prompts(self):
        captured = []
        original = self.r.pool.get
        def get(role):
            body = original(role)
            generate = body.generate
            def spy(messages, *args, **kwargs):
                query = json.loads(messages[1]["content"])
                captured.append((role, query))
                raw = generate(messages, *args, **kwargs)
                source = " ".join(s["text"] for s in query.get("source_segments", []))
                if "Project Harbor" in source and "Option A" not in source:
                    payload = json.loads(raw[0])
                    payload["summary"] = "HARBOR_ONLY_120_EUROS"
                    return [json.dumps(payload)]
                return raw
            body.generate = spy
            return body
        self.r.pool.get = get
        return captured

    def test_cross_topic_switch_and_return_preserve_separate_sources(self):
        prompts = self.capture_prompts()
        harbor_prior = self.event("Harbor", "prior")
        willow_prior = self.event("Willow", "prior")
        harbor_current = self.event("Harbor", "current")
        willow_current = self.event("Willow", "current")
        for role in run52.ROLES:
            with self.subTest(role=role):
                legacy = {"legacy_state": "DO_NOT_TOUCH"}
                key = role + ":" + self.r.session
                self.r.store.set_state(key, legacy)
                a = self.offer(role, harbor_prior)
                self.assertEqual(a["status"], "SHADOW_OFFER_PRODUCED")
                self.assertTrue(a["topic_partitioned"])
                b = self.offer(role, willow_prior)
                self.assertEqual(b["status"], "SHADOW_OFFER_PRODUCED")
                self.assertNotEqual(a["partition_key_sha256"], b["partition_key_sha256"])
                self.assertEqual(self.query(b)["context_source_refs"], [])
                willow_first = prompts[-1][1]
                if role == "B1_DETAIL":
                    self.assertEqual(willow_first["prior_hypothesis"], "")
                else:
                    self.assertEqual(willow_first["earlier_context"], [])
                c = self.offer(role, harbor_current)
                self.assertEqual(c["status"], "SHADOW_OFFER_PRODUCED")
                self.assertEqual(c["partition_key_sha256"], a["partition_key_sha256"])
                self.assertEqual(
                    [x["source_id"] for x in self.query(c)["context_source_refs"]],
                    [harbor_prior["source_ref"]["source_id"]])
                harbor_second = prompts[-1][1]
                if role == "B1_DETAIL":
                    self.assertEqual(harbor_second["prior_hypothesis"],
                                     "HARBOR_ONLY_120_EUROS")
                else:
                    self.assertEqual(
                        harbor_second["earlier_context"][0]["exact_source_excerpt"][:14],
                        "Project Harbor.")
                d = self.offer(role, willow_current)
                self.assertEqual(d["status"], "SHADOW_OFFER_PRODUCED")
                self.assertEqual(
                    [x["source_id"] for x in self.query(d)["context_source_refs"]],
                    [willow_prior["source_ref"]["source_id"]])
                self.assertEqual(self.r.store.state(key)[0], legacy)
                self.assertNotIn("HARBOR_ONLY_120_EUROS",
                                 json.dumps(prompts[-1][1]))
                self.assertEqual(d["delivery_authority"], 0)
                self.assertEqual(d["learning_authority"], 0)
                self.assertFalse(d["native_proof"])

    def test_same_topic_replay_rejected_after_switch(self):
        old = self.event("Harbor", "prior")
        other = self.event("Willow", "prior")
        new = self.event("Harbor", "current")
        for role in run52.ROLES:
            self.assertEqual(self.offer(role, old)["status"], "SHADOW_OFFER_PRODUCED")
            self.assertEqual(self.offer(role, other)["status"], "SHADOW_OFFER_PRODUCED")
            self.assertEqual(self.offer(role, new)["status"], "SHADOW_OFFER_PRODUCED")
            before = self.counts()
            for event in (old, new):
                self.assertEqual(self.offer(role, event)["status"], "STALE_REPLAY_NO_OFFER")
                self.assertEqual(self.counts(), before)

    def test_restart_keeps_each_partition_and_no_cross_topic_context(self):
        harbor = self.event("Harbor", "prior")
        willow = self.event("Willow", "prior")
        for role in run52.ROLES:
            self.assertEqual(self.offer(role, harbor)["status"], "SHADOW_OFFER_PRODUCED")
            self.assertEqual(self.offer(role, willow)["status"], "SHADOW_OFFER_PRODUCED")
        old_session = self.r.session
        self.r.close()
        self.r = FakeRuntime(self.home)
        self.r.cfg.update(run52.OVERRIDES)
        self.r.session = old_session
        self.consumer = TopicPartitionOfferConsumer(self.r)
        later_h = self.event("Harbor", "current")
        later_w = self.event("Willow", "current")
        for role in run52.ROLES:
            a = self.offer(role, later_h)
            b = self.offer(role, later_w)
            self.assertEqual(a["status"], "SHADOW_OFFER_PRODUCED")
            self.assertEqual(b["status"], "SHADOW_OFFER_PRODUCED")
            self.assertEqual(self.query(a)["context_source_refs"][0]["source_id"],
                             harbor["source_ref"]["source_id"])
            self.assertEqual(self.query(b)["context_source_refs"][0]["source_id"],
                             willow["source_ref"]["source_id"])

    def test_ambiguous_unscoped_or_invalid_input_never_writes(self):
        ambiguous = self.r.store.event(
            self.r.session, "Project Harbor and Project Willow are different.")
        generic = self.r.store.event(
            self.r.session, "Please review the project rules.")
        before = self.counts()
        for event in (ambiguous, generic):
            for role in run52.ROLES:
                result = self.offer(role, event)
                self.assertEqual(result["status"], "TOPIC_SCOPE_RED")
                self.assertFalse(result["runner_called"])
        self.assertEqual(self.offer("B1_DETAIL", ambiguous, opt=1)["status"], "OFF")
        self.assertEqual(self.offer("INVALID", ambiguous)["status"], "INVALID_ROLE_OR_EVENT")
        self.assertEqual(self.counts(), before)

    def test_revoked_prior_and_foreign_session_fail_without_state_mutation(self):
        prior = self.event("Harbor", "prior")
        self.assertEqual(self.offer("B1_DETAIL", prior)["status"], "SHADOW_OFFER_PRODUCED")
        current = self.event("Harbor", "current")
        before = self.counts()
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (prior["source_ref"]["source_id"],))
        r = self.offer("B1_DETAIL", current)
        self.assertEqual(r["status"], "EVENT_OR_RETAINED_STATE_RED")
        self.assertFalse(r["runner_called"])
        self.assertEqual(self.counts(), before)
        foreign = self.r.store.new_session("foreign")
        self.r.session = foreign
        r = self.offer("B1_DETAIL", current)
        self.assertEqual(r["status"], "EVENT_OR_TOPIC_RED")
        self.assertEqual(self.counts(), before)


if __name__ == "__main__":
    unittest.main()
