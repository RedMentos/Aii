"""Run101 acceptance guards; software only, never native or model mocks as evidence."""
import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from scripts.ask_verified_budget import BudgetContext, query as ask
from v13.operator import Operator
from v13.runtime import Runtime

from scripts.run101_two_project_c3_native import _native_ok, _preflight_ok, REVISION


REF = {"source_id": "src_test", "sha256": "a" * 64,
       "modality": "text", "char_start": 0, "char_end": 8}


class Run101GateTests(unittest.TestCase):
    def test_native_accepts_only_exact_project_amount_and_teardown(self):
        good = {"status": "FINAL", "native_calls": 1,
                "model_called": True, "process_reaped": True,
                "model_revision": REVISION, "source_ref": REF,
                "answer": "The budget for Project Dovan is 731 Euros."}
        self.assertTrue(_native_ok(good, "Dovan", "731 Euro", REF))
        for changes in (
            {"status": "UNVERIFIED_NATIVE_ANSWER"},
            {"native_calls": 0},
            {"process_reaped": False},
            {"model_revision": "other"},
            {"source_ref": {"sha256": "wrong"}},
            {"answer": "Project Mira has 731 Euros."},
            {"answer": "Project Dovan has 942 Euros."},
            {"answer": "Project Dovan has 731 Euros and 942 Euros."},
            {"answer": "Project Dovan has 731.000 Euros."},
            {"answer": "Project Dovan has 731 Euros but Project Mira has 942 Euros."},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(_native_ok(dict(good, **changes), "Dovan", "731 Euro", REF))

    def test_missing_source_and_out_of_scope_never_leak_numbers(self):
        for status in ("CLARIFY", "NOT_APPLICABLE"):
            self.assertTrue(_preflight_ok({
                "status": status, "native_calls": 0,
                "model_called": False, "answer": "No verified budget."
            }, status))
            self.assertFalse(_preflight_ok({
                "status": status, "native_calls": 0,
                "model_called": False, "answer": "731 Euro"
            }, status))
            self.assertFalse(_preflight_ok({
                "status": status, "native_calls": 1,
                "model_called": True, "answer": ""
            }, status))

    def test_real_two_source_restart_conflict_and_independent_forget(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            runtime = Runtime(home)
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                ids = {}
                for project, amount in (("Dovan", "731 Euro"), ("Mira", "942 Euro")):
                    key = "Project " + project + " budget"
                    event = runtime.store.event(runtime.session, key)
                    ids[project] = runtime.memory.feedback(
                        event["event_id"], "fact", amount, key=key, permission="record")
                session = runtime.session
                op = Operator(runtime)
                for project in ids:
                    ready = json.loads(op.run(
                        ":verified What is the budget for Project " + project + "?"))
                    self.assertEqual(ready["status"], "READY")
                    self.assertEqual(ready["memory_id"], ids[project])
            finally:
                runtime.close()

            context = BudgetContext(home)
            try:
                self.assertEqual(context.session, session)
                with patch.object(context.pool, "get",
                                  side_effect=AssertionError("NATIVE_CALLED")):
                    for project in ids:
                        self.assertEqual(ask(
                            context, "What is the budget for Project " + project + "?",
                            native=False)["status"], "READY")
                    self.assertEqual(ask(context,
                        "What is the budget for Project Elyra?", native=True)["status"],
                        "CLARIFY")
            finally:
                context.close()

            runtime = Runtime(home)
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                event = runtime.store.event(runtime.session, "Project Dovan budgets")
                conflict_id = runtime.memory.feedback(
                    event["event_id"], "fact", "809 Euro",
                    key="Project Dovan budgets", permission="record")
                op = Operator(runtime)
                self.assertEqual(json.loads(op.run(
                    ":verified What is the budget for Project Dovan?"))["status"],
                    "CLARIFY")
                self.assertEqual(json.loads(op.run(
                    ":verified What is the budget for Project Mira?"))["status"],
                    "READY")
                for memory_id in (ids["Dovan"], conflict_id):
                    op.run(":forget " + memory_id + " --confirm")
                self.assertEqual(json.loads(op.run(
                    ":verified What is the budget for Project Dovan?"))["status"],
                    "CLARIFY")
                self.assertEqual(json.loads(op.run(
                    ":verified What is the budget for Project Mira?"))["status"],
                    "READY")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
