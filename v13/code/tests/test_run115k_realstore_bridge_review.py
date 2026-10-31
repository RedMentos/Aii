"""Real SQLite/Context OS B1/B2 -> JEF -> C3 SHADOW integration review.

B1/B2 runners are deliberately synthetic and unreliable. They are NOT
native model, quote, learning, or semantic-utility evidence.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.b1b2_jef_c3_source_role_bridge_candidate import (
    build_b1b2_jef_c3_source_role_bridge,
)
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.common import dumps
from v13.context_os import controller
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime


class WrongQuoteBody:
    def __init__(self, role):
        self.role = role
        self.last_metrics = {"status": "FINAL"}

    def generate(self, messages, *args, **kwargs):
        return [json.dumps({
            "summary": "Option B is definitely eligible (synthetic wrong hypothesis)",
            "quotes": ["INVENTED_QUOTE_NOT_IN_USER_SOURCE"],
            "uncertainty": "high",
            "needs_reentry": True,
        })]


class WrongQuoteRuntime(FakeRuntime):
    def _body(self, role):
        return WrongQuoteBody(role)


class RealStoreBridgeReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = WrongQuoteRuntime(Path(self.tmp.name) / "home")
        self.r.cfg.update(OVERRIDES)
        self.consumer = TopicPartitionOfferConsumer(self.r)
        self.prior = self.r.store.event(
            self.r.session,
            "Project Kairo. Budget 200 euros. Deadline 5 days. "
            "Local-only requirement: true. These are the binding project rules.")
        for role in ("B1_DETAIL", "B2_GIST"):
            result = self.consumer.guarded_offer(
                role, self.prior, 0, time.monotonic() + 30,
                operator_opt_in=True)
            self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED", result)
        self.current = self.r.store.event(
            self.r.session,
            "Project Kairo. Apply the earlier project rules. "
            "Option A costs 190 euros, takes 4 days, and is local. "
            "Option B costs 170 euros, takes 7 days, and is local. "
            "Choose the cheapest eligible option and state its remaining budget.")
        self.ids = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            result = self.consumer.guarded_offer(
                role, self.current, 0, time.monotonic() + 30,
                operator_opt_in=True)
            self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED", result)
            self.ids[role] = result["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def build(self, *, opt=True):
        return build_b1b2_jef_c3_source_role_bridge(
            self.r, self.prior, self.current, self.ids,
            operator_opt_in=opt)

    def count(self, table, where="1=1"):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table + " WHERE " + where)["n"]

    def test_exact_two_sources_wrong_body_remains_hypothesis(self):
        actions_before = self.count("actions")
        assistants_before = self.count("messages", "role='assistant'")
        result = self.build()
        self.assertEqual(result["status"],
                         "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED", result)
        self.assertEqual(result["typed_jef_candidate"],
                         {"choice": "A", "remaining": 10})
        self.assertEqual(result["verified_quote_count"], 0)
        self.assertFalse(result["body_model_quote_verified"])
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["native_b1_calls"], 0)
        self.assertEqual(result["native_c3_calls"], 0)
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual([m["role"] for m in result["messages"]],
                         ["system", "user"])
        payload = json.loads(result["messages"][1]["content"])
        self.assertEqual([s["source_ref"] for s in payload["sources"]],
                         [self.prior["source_ref"], self.current["source_ref"]])
        self.assertEqual([s["text"] for s in payload["sources"]],
                         [self.r.store.read_source(self.prior["source_ref"]),
                          self.r.store.read_source(self.current["source_ref"])])
        self.assertEqual(payload["typed_jef_candidate"],
                         {"choice": "A", "remaining": 10})
        self.assertFalse(payload["body_hypotheses_are_facts"])
        for observation in payload["body_observations"]:
            self.assertEqual(observation["hypothesis_authority"],
                             "MODEL_HYPOTHESIS_NOT_FACT")
            self.assertIn("Option B", observation["hypothesis"]["summary"])
            self.assertEqual(observation["verified_quotes"], [])
        self.assertEqual(self.count("actions"), actions_before)
        self.assertEqual(self.count("messages", "role='assistant'"),
                         assistants_before)
        self.assertEqual(self.count("packets", "kind='ContextPlan'"), 1)

    def test_off_has_no_plan_or_output(self):
        before = self.count("packets", "kind='ContextPlan'")
        result = self.build(opt=False)
        self.assertEqual(result["status"], "OFF")
        self.assertNotIn("messages", result)
        self.assertEqual(self.count("packets", "kind='ContextPlan'"), before)

    def test_active_context_os_refuses_before_plan(self):
        controller(self.r).set_mode("ACTIVE", authority="EXPLICIT_HUMAN")
        result = self.build()
        self.assertEqual(result["status"], "CONTEXT_OS_NOT_SHADOW_RED")
        self.assertNotIn("messages", result)
        self.assertEqual(self.count("packets", "kind='ContextPlan'"), 0)

    def test_later_user_correction_refuses_before_plan(self):
        self.r.store.event(self.r.session, "Project Kairo. Cancel the choice.")
        result = self.build()
        self.assertNotEqual(result["status"],
                            "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED")
        self.assertNotIn("messages", result)
        self.assertEqual(self.count("packets", "kind='ContextPlan'"), 0)

    def test_tampered_persisted_offer_refuses(self):
        pid = self.ids["B1_DETAIL"]
        row = self.r.store.one("SELECT payload FROM packets WHERE id=?", (pid,))
        data = json.loads(row["payload"])
        data["offer"]["summary"] = "TAMPERED"
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       (dumps(data), pid))
        result = self.build()
        self.assertNotEqual(result["status"],
                            "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED")
        self.assertNotIn("messages", result)
        self.assertEqual(self.count("packets", "kind='ContextPlan'"), 0)

    def test_deleted_prior_source_refuses(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.prior["source_ref"]["source_id"],))
        result = self.build()
        self.assertNotEqual(result["status"],
                            "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED")
        self.assertNotIn("messages", result)
        self.assertEqual(self.count("packets", "kind='ContextPlan'"), 0)


if __name__ == "__main__":
    unittest.main()
