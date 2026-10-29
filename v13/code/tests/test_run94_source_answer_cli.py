"""Run94 source-answer CLI: real persisted preflight, explicit mocked native opt-in."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.__main__ import main
from v13.runtime import Runtime
from v13.runners import RunnerPool


QUESTION = "What is the budget for Project Elyra?"


class SourceAnswerCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "home"
        r = Runtime(self.home)
        try:
            r.sleep.cycle.set_policy("enabled", "off")
            e = r.store.event(r.session, "Project Elyra budget")
            self.memory_id = r.memory.feedback(e["event_id"], "fact", "615 Euro",
                                               key="Project Elyra budget", permission="record")
            self.session = r.session
        finally:
            r.close()

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--home", str(self.home), "source-answer", *args])
        return code, json.loads(out.getvalue().strip())

    def test_existing_source_preflight_is_real_persisted_and_model_free(self):
        with patch.object(RunnerPool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            code, result = self.cli(QUESTION)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["memory_id"], self.memory_id)
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["model_called"])
        self.assertNotIn("answer", result)

        r = Runtime(self.home)
        try:
            self.assertEqual(r.session, self.session)
            self.assertEqual(r.store.queue_stats()["count"], 0)
        finally:
            r.close()

    def test_wrong_project_and_out_of_scope_refuse_without_native(self):
        with patch.object(RunnerPool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            wrong_code, wrong = self.cli("What is the budget for Project Dovan?", "--native")
            outside_code, outside = self.cli("Who leads Project Elyra?", "--native")
        self.assertEqual((wrong_code, wrong["status"], wrong["native_calls"]), (0, "CLARIFY", 0))
        self.assertEqual((outside_code, outside["status"], outside["native_calls"]),
                         (0, "NOT_APPLICABLE", 0))
        self.assertNotIn("615 Euro", wrong.get("answer", ""))
        self.assertNotIn("answer", outside)

    def test_native_is_explicit_and_bounds_forwarded_without_substitution(self):
        fake = {"status": "FINAL", "answer": "Project Elyra has 615 Euro.",
                "native_calls": 1, "model_called": True}
        with patch("scripts.ask_verified_budget.query", return_value=fake) as source_query:
            code, result = self.cli(QUESTION, "--native", "--session", self.session,
                                    "--timeout", "31", "--max-tokens", "17")
        self.assertEqual(code, 0)
        self.assertEqual(result, fake)
        self.assertEqual(source_query.call_count, 1)
        args, kwargs = source_query.call_args
        self.assertEqual(args[1], QUESTION)
        self.assertEqual(args[2], self.session)
        self.assertEqual(kwargs, {"native": True, "timeout_s": 31., "max_tokens": 17})

        with patch("scripts.ask_verified_budget.query", return_value={"status": "READY"}) as source_query:
            code, _ = self.cli(QUESTION)
        self.assertEqual(code, 0)
        self.assertIs(source_query.call_args.kwargs["native"], False)

    def test_invalid_native_result_is_nonzero_and_never_faked_final(self):
        with patch("scripts.ask_verified_budget.query",
                   return_value={"status": "UNVERIFIED_NATIVE_ANSWER", "native_calls": 1}):
            code, result = self.cli(QUESTION, "--native")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "UNVERIFIED_NATIVE_ANSWER")
        self.assertNotIn("answer", result)

    def test_concurrent_runtime_lock_denies_offline_source_answer(self):
        live = Runtime(self.home)
        try:
            with patch.object(RunnerPool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                code, result = self.cli(QUESTION, "--native")
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "ERROR")
            self.assertNotIn("answer", result)
        finally:
            live.close()

    def test_missing_home_does_not_initialize_or_create_session(self):
        missing = Path(self.temp.name) / "absent"
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["--home", str(missing), "source-answer", QUESTION])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(missing.exists())

    def test_existing_operator_verified_remains_native_forbidden(self):
        r = Runtime(self.home)
        try:
            from v13.operator import Operator
            op = Operator(r)
            with self.assertRaisesRegex(ValueError, "nur F1/F5"):
                op.run(":verified native " + QUESTION)
        finally:
            r.close()


if __name__ == "__main__":
    unittest.main()
