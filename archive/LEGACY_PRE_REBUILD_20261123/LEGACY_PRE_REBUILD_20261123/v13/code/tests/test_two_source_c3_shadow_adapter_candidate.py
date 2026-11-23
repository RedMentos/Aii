"""Real Context OS + SQLite SHADOW source adapter tests, no native calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13 import context_os as ctxos
from v13.runtime import Runtime
from v13.two_source_c3_shadow_adapter_candidate import plan_c3_two_source


class TwoSourceC3ShadowAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name) / "home")
        self.prior = self.r.store.event(
            self.r.session, "Project Rowan. Budget 140 euros, deadline 5 days. Local-only yes.")
        self.current = self.r.store.event(
            self.r.session, "Project Rowan. Option A costs 130 euros and takes 4 days. Option B costs 120 euros and takes 6 days.")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def run_plan(self, **kw):
        return plan_c3_two_source(self.r, self.prior, self.current, **kw)

    def count_plans(self):
        return self.r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")["n"]

    def test_default_off_does_not_write_plan(self):
        before = self.r.store.db.total_changes
        result = self.run_plan()
        self.assertEqual(result["status"], "OFF")
        self.assertEqual(self.r.store.db.total_changes, before)
        self.assertEqual(self.count_plans(), 0)

    def test_exact_user_sources_reach_context_plan_without_model_quote_authority(self):
        result = self.run_plan(operator_opt_in=True)
        self.assertEqual(result["status"], "SHADOW_C3_SOURCE_PLAN_VERIFIED")
        self.assertFalse(result["applied"])
        self.assertFalse(result["body_model_quote_verified"])
        self.assertEqual(result["native_c3_calls"], 0)
        self.assertEqual(result["native_body_calls"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(self.count_plans(), 1)
        text = "\n".join(m["content"] for m in result["messages"])
        for e in (self.prior, self.current):
            self.assertIn(self.r.store.read_source(e["source_ref"]), text)
        self.assertEqual(result["source_refs"],
                         [self.prior["source_ref"], self.current["source_ref"]])
        self.assertEqual(
            self.r.store.one("SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"], 0)
        self.assertEqual(self.r.store.one("SELECT COUNT(*) AS n FROM actions")["n"], 0)

    def test_stale_correction_before_plan_refuses_without_plan(self):
        self.r.store.event(self.r.session, "Project Rowan. Cancel all options.")
        self.assertEqual(self.run_plan(operator_opt_in=True)["status"],
                         "SOURCE_POINTER_REFUSED_RED")
        self.assertEqual(self.count_plans(), 0)

    def test_deleted_prior_ref_refuses(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.prior["source_ref"]["source_id"],))
        self.assertEqual(self.run_plan(operator_opt_in=True)["status"],
                         "SOURCE_POINTER_REFUSED_RED")
        self.assertEqual(self.count_plans(), 0)

    def test_active_context_os_is_not_allowed(self):
        ctxos.controller(self.r).set_mode("ACTIVE", authority="EXPLICIT_HUMAN")
        self.assertEqual(self.run_plan(operator_opt_in=True)["status"],
                         "CONTEXT_OS_NOT_SHADOW_RED")
        self.assertEqual(self.count_plans(), 0)

    def test_new_correction_during_shadow_plan_refuses_output(self):
        original = ctxos.ContextOS.plan
        runtime = self.r

        def inject(self, *args, **kwargs):
            plan = original(self, *args, **kwargs)
            runtime.store.event(
                runtime.session, "Project Rowan. New binding correction: none eligible.")
            return plan

        with patch.object(ctxos.ContextOS, "plan", inject):
            result = self.run_plan(operator_opt_in=True)
        self.assertEqual(result["status"], "POST_PLAN_STALE_SOURCE_RED")
        self.assertIn("orphaned_shadow_plan_packet_id", result)
        self.assertEqual(self.count_plans(), 1)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)


if __name__ == "__main__":
    unittest.main()
