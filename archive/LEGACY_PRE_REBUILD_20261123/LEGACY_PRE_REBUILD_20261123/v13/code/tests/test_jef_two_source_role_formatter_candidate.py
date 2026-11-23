"""Run115J real Store typed JEF to C3 user-role formatter SHADOW tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.context_os import controller
from v13.runtime import Runtime
from v13.jef_two_source_role_formatter_candidate import (
    FORMATTER_SYSTEM, build_typed_jef_role_formatter,
)


class TypedJEFRoleFormatterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name) / "home")
        self.prior = self.r.store.event(
            self.r.session,
            "Project Kairo. Budget 200 euros. Deadline 5 days. "
            "Local-only requirement: true. These are the binding project rules.")
        self.current = self.r.store.event(
            self.r.session,
            "Project Kairo. Apply the earlier project rules. "
            "Option A costs 190 euros, takes 4 days, and is local. "
            "Option B costs 170 euros, takes 7 days, and is local. "
            "Choose the cheapest eligible option and state its remaining budget.")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def build(self, **kwargs):
        return build_typed_jef_role_formatter(
            self.r, self.prior, self.current, **kwargs)

    def plans(self):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")["n"]

    def test_off_has_no_context_plan_or_native_authority(self):
        before = self.r.store.db.total_changes
        result = self.build()
        self.assertEqual(result["status"], "OFF")
        self.assertEqual(self.plans(), 0)
        self.assertEqual(self.r.store.db.total_changes, before)
        self.assertNotIn("messages", result)

    def test_first_grammar_exact_sources_typed_candidate_in_user_role(self):
        result = self.build(operator_opt_in=True)
        self.assertEqual(result["status"], "SHADOW_TYPED_JEF_ROLE_FORMATTER_VERIFIED")
        self.assertEqual(result["typed_jef_candidate"],
                         {"choice": "A", "remaining": 10})
        self.assertEqual([m["role"] for m in result["messages"]],
                         ["system", "user"])
        self.assertEqual(result["messages"][0]["content"], FORMATTER_SYSTEM)
        payload = json.loads(result["messages"][1]["content"])
        self.assertEqual(payload["typed_jef_candidate"],
                         {"choice": "A", "remaining": 10})
        self.assertEqual(payload["typed_candidate_authority"], 0)
        self.assertEqual(payload["typed_candidate_origin"],
                         "DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL")
        self.assertEqual([s["source_ref"] for s in payload["sources"]],
                         [self.prior["source_ref"], self.current["source_ref"]])
        for source in payload["sources"]:
            self.assertNotIn(source["text"], FORMATTER_SYSTEM)
        self.assertEqual(self.plans(), 1)
        self.assertEqual(result["native_c3_calls"], 0)
        self.assertEqual(result["native_jef_calls"], 0)
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertFalse(result["output_committed"])

    def test_second_frozen_jef_grammar_works(self):
        self.prior = self.r.store.event(
            self.r.session,
            "Project Lythos. Spending limit: 310 euros. Finish within 8 days. "
            "Must remain local: no. This policy is binding.")
        self.current = self.r.store.event(
            self.r.session,
            "Project Lythos. Decide using the saved policy. "
            "Option A: cost 280 euros, duration 7 days, local true. "
            "Option B: cost 250 euros, duration 6 days, local true. "
            "Pick the cheapest eligible option and give remaining euros.")
        result = self.build(operator_opt_in=True)
        self.assertEqual(result["status"], "SHADOW_TYPED_JEF_ROLE_FORMATTER_VERIFIED")
        self.assertEqual(result["typed_jef_candidate"],
                         {"choice": "B", "remaining": 60})

    def test_invalid_jef_source_grammar_refuses_before_plan(self):
        self.current = self.r.store.event(
            self.r.session, "Project Kairo. Please pick any option.")
        self.assertEqual(self.build(operator_opt_in=True)["status"],
                         "TYPED_JEF_SOURCE_OR_SHAPE_RED")
        self.assertEqual(self.plans(), 0)

    def test_active_context_os_refuses_before_plan(self):
        controller(self.r).set_mode("ACTIVE", authority="EXPLICIT_HUMAN")
        self.assertEqual(self.build(operator_opt_in=True)["status"],
                         "CONTEXT_OS_NOT_SHADOW_RED")
        self.assertEqual(self.plans(), 0)

    def test_post_plan_user_correction_refuses_and_reports_orphan(self):
        from v13 import jef_two_source_role_formatter_candidate as module
        original = module.build_role_separated_c3_shadow
        runtime = self.r

        def inject(*args, **kwargs):
            result = original(*args, **kwargs)
            runtime.store.event(runtime.session, "Project Kairo. Cancel all.")
            return result

        with patch.object(module, "build_role_separated_c3_shadow", inject):
            result = self.build(operator_opt_in=True)
        self.assertEqual(result["status"], "POST_ASSEMBLY_SOURCE_OR_JEF_RED")
        self.assertIn("orphaned_shadow_plan_packet_id", result)
        self.assertNotIn("messages", result)
        self.assertEqual(self.plans(), 1)

    def test_tampered_typed_jef_candidate_refuses_before_plan(self):
        from v13 import jef_two_source_role_formatter_candidate as module
        from v13.agi.jef_eligibility_source_shadow_run46b import propose
        original = propose(self.r.store, self.prior["source_ref"],
                           self.current["source_ref"])
        forged = dict(original, candidate={"choice": "B", "remaining": 30})
        with patch.object(module, "propose", return_value=forged):
            result = self.build(operator_opt_in=True)
        self.assertEqual(result["status"], "TYPED_JEF_CANDIDATE_MISMATCH_RED")
        self.assertEqual(self.plans(), 0)


if __name__ == "__main__":
    unittest.main()
