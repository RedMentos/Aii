"""Run82 dual JEF/B1B2 C3 source prompt real SQLite synthetic tests."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from tests.test_jef_range_policy_shadow import TABLE, texts
from v13 import jef_b1b2_c3_dual_source_shadow as bridge
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.common import dumps


class DualSourceEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = FakeRuntime(Path(self.tmp.name))
        self.r.cfg.update(OVERRIDES)
        # A new synthetic cross-organ test case; do not change Run73/75 cohorts.
        self.row = ("Harbor",) + TABLE[0][1:]
        current, policy, sheet = texts(self.row)
        self.ids = []
        for key, value in (
            ("Project Harbor archived harbor drones policy", policy),
            ("Project Harbor latest harbor drones option sheet", sheet),
        ):
            e = self.r.store.event(self.r.session, "Record: " + key)
            mid = self.r.memory.feedback(
                e["event_id"], "fact", value, permission="record",
                key=key, scope="session")
            self.r.memory.candidate(mid, self.r.session)
            self.ids.append(mid)
        self.event = self.r.store.event(self.r.session, current)
        consumer = TopicPartitionOfferConsumer(self.r)
        self.offers = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            result = consumer.guarded_offer(
                role, self.event, 0, time.monotonic() + 30,
                operator_opt_in=True)
            self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED")
            self.offers[role] = result["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def build(self, *, event=None, ids=None, offers=None, opt=True, receipt=None):
        return bridge.build(
            self.r, self.event if event is None else event,
            self.offers if offers is None else offers,
            self.ids if ids is None else ids,
            operator_opt_in=opt, approval_receipt=receipt)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("packets", "actions", "messages"))

    def test_real_store_two_organ_prompt_no_model_no_output(self):
        before = self.counts()
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            a = self.build()
            b = self.build()
        self.assertEqual(a["status"], bridge.STATUS, a)
        self.assertEqual(a["typed_jef_action"], "A")
        self.assertEqual(a["messages_sha256"], b["messages_sha256"])
        self.assertEqual(self.counts(), before)
        self.assertEqual(a["delivery_authority"], 0)
        self.assertEqual(a["learning_authority"], 0)
        self.assertEqual(a["tool_dispatches"], 0)
        self.assertFalse(a["model_called"])
        self.assertFalse(a["output_committed"])
        self.assertFalse(a["real_tty_approved"])
        self.assertFalse(a["independent_reasoning_proven"])
        self.assertTrue(a["formatter_only"])
        payload = json.loads(a["messages"][1]["content"])
        self.assertEqual(payload["typed_jef_action"], "A")
        self.assertFalse(payload["body_hypotheses_are_facts"])
        self.assertEqual(
            [x["role"] for x in payload["body_observations"]],
            ["B1_DETAIL", "B2_GIST"])
        self.assertTrue(all(x["hypothesis_authority"]
                            == "MODEL_HYPOTHESIS_NOT_FACT"
                            for x in payload["body_observations"]))

    def test_off_and_fake_tty_receipt_fail_before_source(self):
        self.assertEqual(self.build(opt=False)["status"], "OFF")
        self.assertEqual(self.build(opt=1)["status"], "OFF")
        self.assertEqual(self.build(receipt={"approved": True})["status"],
                         "REAL_TTY_APPROVAL_UNSUPPORTED")

    def test_stale_user_fails_closed(self):
        self.r.store.event(self.r.session, "Project Harbor newer user correction")
        self.assertEqual(self.build()["status"], "B1B2_SOURCE_ENVELOPE_RED")

    def test_revoked_human_source_fails_closed(self):
        self.r.memory.forget(self.ids[0])
        self.assertEqual(self.build()["status"], "JEF_HUMAN_SOURCE_ADMISSION_RED")

    def test_wrong_memory_and_offer_id_fail_closed(self):
        self.assertEqual(self.build(ids=[self.ids[0], self.ids[0]])["status"],
                         "JEF_HUMAN_SOURCE_ADMISSION_RED")
        wrong = dict(self.offers, B2_GIST="pkt_missing")
        self.assertEqual(self.build(offers=wrong)["status"],
                         "B1B2_SOURCE_ENVELOPE_RED")

    def test_between_envelope_mutation_detected(self):
        original = bridge.build_jef_typed
        called = [0]

        def injected(*args, **kwargs):
            result = original(*args, **kwargs)
            called[0] += 1
            if called[0] == 1:
                self.r.memory.forget(self.ids[0])
            return result

        before = self.r.store.one(
            "SELECT COUNT(*) AS n FROM actions")["n"]
        with patch.object(bridge, "build_jef_typed", side_effect=injected):
            result = self.build()
        self.assertEqual(result["status"],
                         "SOURCE_CHANGED_DURING_DUAL_COMPOSITION")
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM actions")["n"], before)


if __name__ == "__main__":
    unittest.main()
