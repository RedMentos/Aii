"""Run97: real F1/F5 source-exact answer, no model, no fabricated authority."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import source_exact
from scripts.ask_verified_budget import BudgetContext
from v13.runtime import Runtime


QUERY = "What is the budget for Project Elyra?"


class SourceExactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        runtime = Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            event = runtime.store.event(runtime.session, "Project Elyra budget")
            self.memory_id = runtime.memory.feedback(event["event_id"], "fact",
                                                     "615 Euro", key="Project Elyra budget",
                                                     permission="record")
            self.session = runtime.session
        finally:
            runtime.close()
        self.context = BudgetContext(self.home)

    def tearDown(self):
        self.context.close()
        self.tmp.cleanup()

    def test_real_source_exact_answer_without_model(self):
        with patch.object(self.context.pool, "get", side_effect=AssertionError("NATIVE_CALLED")):
            result = source_exact.query_exact(self.context, QUERY)
        self.assertEqual(result["status"], "FINAL")
        self.assertEqual(result["mode"], "SOURCE_EXACT")
        self.assertEqual(result["answer"], "Project Elyra budget: 615 Euro.")
        self.assertEqual(result["memory_id"], self.memory_id)
        self.assertFalse(result["model_called"])
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["learning_weight_commit"])

    def test_wrong_project_outside_scope_and_session_refuse(self):
        with patch.object(self.context.pool, "get", side_effect=AssertionError("NATIVE_CALLED")):
            wrong = source_exact.query_exact(
                self.context, "What is the budget for Project Dovan?")
            outside = source_exact.query_exact(self.context, "Who leads Project Elyra?")
            another = self.context.store.new_session()
            cross = source_exact.query_exact(self.context, QUERY, session=another)
        self.assertEqual(wrong["status"], "CLARIFY")
        self.assertEqual(outside["status"], "NOT_APPLICABLE")
        self.assertEqual(cross["status"], "CLARIFY")
        for result in (wrong, outside, cross):
            self.assertEqual(result["native_calls"], 0)
            self.assertFalse(result["model_called"])
            self.assertNotIn("615 Euro", result.get("answer", ""))

    def test_conflicting_verified_source_refuses(self):
        event = self.context.store.event(self.session, "Project Elyra budgets")
        self.context.memory.feedback(event["event_id"], "fact", "700 Euro",
                                     key="Project Elyra budgets", permission="record")
        result = source_exact.query_exact(self.context, QUERY)
        self.assertEqual(result["status"], "CLARIFY")
        self.assertNotIn("615 Euro", result.get("answer", ""))

    def test_revoked_and_corrupted_source_refuse(self):
        self.context.memory.forget(self.memory_id)
        revoked = source_exact.query_exact(self.context, QUERY)
        self.assertEqual(revoked["status"], "CLARIFY")
        self.assertNotIn("615 Euro", revoked.get("answer", ""))
        event = self.context.store.event(self.session, "Project Elyra budget")
        fresh = self.context.memory.feedback(event["event_id"], "fact", "615 Euro",
                                             key="Project Elyra budget", permission="record")
        row = self.context.memory.candidate(fresh, self.session)
        blob = self.home / "data/blobs" / row["source_ref"]["sha256"]
        blob.write_text("tampered", encoding="utf-8")
        corrupt = source_exact.query_exact(self.context, QUERY)
        self.assertEqual(corrupt["status"], "CLARIFY")
        self.assertNotIn("615 Euro", corrupt.get("answer", ""))

    def test_revoke_between_preflight_and_egress_never_returns_fact(self):
        original = source_exact._preflight
        calls = [0]

        def revalidate(*args):
            result = original(*args)
            calls[0] += 1
            if calls[0] == 1:
                self.context.memory.forget(self.memory_id)
            return result

        with patch.object(source_exact, "_preflight", side_effect=revalidate):
            result = source_exact.query_exact(self.context, QUERY)
        self.assertEqual(calls[0], 2)
        self.assertEqual(result["status"], "CLARIFY")
        self.assertEqual(result["reason"], "SOURCE_CHANGED_BEFORE_EGRESS")
        self.assertNotIn("answer", result)
        self.assertEqual(result["native_calls"], 0)

    def test_standalone_cli_uses_existing_home_and_refuses_missing(self):
        self.context.close()
        self.context = None
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = source_exact.main(["--home", str(self.home), "--query", QUERY])
        result = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "FINAL")
        self.assertEqual(result["answer"], "Project Elyra budget: 615 Euro.")
        missing = Path(self.tmp.name) / "missing"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = source_exact.main(["--home", str(missing), "--query", QUERY])
        self.assertEqual(code, 2)
        self.assertFalse(missing.exists())
        self.assertEqual(json.loads(out.getvalue())["reason"], "EXISTING_HOME_REQUIRED")

    def tearDown(self):
        if self.context is not None:
            self.context.close()
        self.tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
