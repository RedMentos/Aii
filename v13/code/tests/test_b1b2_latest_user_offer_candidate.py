"""Run76 B1/B2 latest USER offer pre/post guards on real Store fake runners."""
from pathlib import Path
import tempfile
import time
import unittest

from scripts import run52_b1b2_cross_turn_native as run52
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_latest_user_offer_candidate import LatestUserOfferConsumer

FIXTURE = Path(__file__).resolve().parents[1] / (
    "docs/fixtures/run52_b1b2_cross_turn_seed479.json")


class LatestUserOffer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = FakeRuntime(Path(self.tmp.name))
        self.r.cfg.update(run52.OVERRIDES)
        self.f = {row["id"]: row for row in run52.load_fixture(FIXTURE)["fixtures"]}
        self.c = LatestUserOfferConsumer(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, project, phase):
        return self.r.store.event(self.r.session, self.f[project][phase])

    def offer(self, role, event, *, opt=True):
        return self.c.guarded_offer(
            role, event, 0, time.monotonic() + 30,
            operator_opt_in=opt)

    def count(self):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='OfferPacket'")["n"]

    def assert_safe(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["real_tty_approved"])
        self.assertFalse(result["native_proof"])
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["whole_system_complete"])

    def test_original_stale_no_retained_state_counterexample(self):
        old = self.event("Harbor", "prior")
        self.event("Willow", "prior")  # newest USER is now Willow
        before = self.count()
        legacy = TopicPartitionOfferConsumer(self.r).guarded_offer(
            "B1_DETAIL", old, 0, time.monotonic() + 30,
            operator_opt_in=True)
        self.assertEqual(legacy["status"], "SHADOW_OFFER_PRODUCED")
        self.assertEqual(self.count(), before + 1)
        blocked = self.offer("B2_GIST", old)
        self.assertEqual(blocked["status"],
                         "PRE_OFFER_STALE_USER_OR_SOURCE_RED")
        self.assertFalse(blocked["runner_called"])
        self.assertEqual(self.count(), before + 1)
        self.assert_safe(blocked)

    def test_latest_user_both_body_roles_produce_source_bound_shadow(self):
        current = self.event("Harbor", "prior")
        before = self.count()
        for role in run52.ROLES:
            result = self.offer(role, current)
            self.assertEqual(result["status"],
                             "SHADOW_LATEST_USER_OFFER_PRODUCED")
            self.assertTrue(result["runner_called"])
            self.assertTrue(result["topic_partitioned"])
            self.assertTrue(result["shadow_offer_may_exist"])
            self.assertIsInstance(result["offer_packet_id"], str)
            self.assert_safe(result)
        self.assertEqual(self.count(), before + 2)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM actions")["n"], 0)

    def test_new_user_arriving_inside_generate_returns_post_red(self):
        current = self.event("Harbor", "prior")
        original_get = self.r.pool.get
        injected = [False]

        def get(role):
            body = original_get(role)
            generate = body.generate
            def interrupt(messages, *args, **kwargs):
                if not injected[0]:
                    injected[0] = True
                    self.r.store.event(
                        self.r.session,
                        "Project Harbor. A newer authoritative user message.")
                return generate(messages, *args, **kwargs)
            body.generate = interrupt
            return body

        self.r.pool.get = get
        before = self.count()
        result = self.offer("B1_DETAIL", current)
        self.assertTrue(injected[0])
        self.assertEqual(result["status"],
                         "POST_OFFER_STALE_USER_OR_SOURCE_RED")
        self.assertTrue(result["runner_called"])
        self.assertTrue(result["shadow_offer_may_exist"])
        self.assertIsInstance(result["orphaned_shadow_offer_packet_id"], str)
        self.assertEqual(self.count(), before + 1)
        self.assert_safe(result)

    def test_default_off_nonboolean_optin_and_invalid_role(self):
        before = self.count()
        for opt in (False, 0, 1, None):
            result = self.offer("B1_DETAIL", None, opt=opt)
            self.assertEqual(result["status"], "OFF")
            self.assertFalse(result["runner_called"])
            self.assert_safe(result)
        result = self.offer("C3_LANGUAGE", {})
        self.assertEqual(result["status"], "INVALID_ROLE_OR_EVENT")
        self.assertEqual(self.count(), before)
        self.assert_safe(result)

    def test_revoked_current_source_denied_before_runner(self):
        current = self.event("Harbor", "prior")
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (current["source_ref"]["source_id"],))
        before = self.count()
        result = self.offer("B1_DETAIL", current)
        self.assertEqual(result["status"],
                         "PRE_OFFER_STALE_USER_OR_SOURCE_RED")
        self.assertFalse(result["runner_called"])
        self.assertEqual(self.count(), before)
        self.assert_safe(result)

    def test_foreign_session_and_same_topic_stale_replay_denied(self):
        old = self.event("Harbor", "prior")
        self.assertEqual(self.offer("B1_DETAIL", old)["status"],
                         "SHADOW_LATEST_USER_OFFER_PRODUCED")
        current = self.event("Harbor", "current")
        self.assertEqual(self.offer("B1_DETAIL", current)["status"],
                         "SHADOW_LATEST_USER_OFFER_PRODUCED")
        before = self.count()
        stale = self.offer("B1_DETAIL", old)
        self.assertEqual(stale["status"],
                         "PRE_OFFER_STALE_USER_OR_SOURCE_RED")
        self.assertEqual(self.count(), before)
        self.assert_safe(stale)
        self.r.session = self.r.store.new_session("foreign")
        foreign = self.offer("B2_GIST", current)
        self.assertEqual(foreign["status"],
                         "PRE_OFFER_STALE_USER_OR_SOURCE_RED")
        self.assertEqual(self.count(), before)
        self.assert_safe(foreign)


if __name__ == "__main__":
    unittest.main()
