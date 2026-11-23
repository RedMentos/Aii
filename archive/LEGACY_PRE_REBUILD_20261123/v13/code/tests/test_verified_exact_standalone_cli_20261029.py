"""Preregistered existing-home F1/F5 standalone exact-source CLI tests (software only)."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import ask_verified_budget as cli
from v13.runtime import Runtime
from v13.runners import RunnerPool


class VerifiedExactStandaloneCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.runtime = Runtime(self.home)
        self.runtime.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        if self.runtime is not None:
            self.runtime.close()
        self.temp.cleanup()

    def source(self):
        event = self.runtime.store.event(self.runtime.session, "Project Elyra budget")
        mid = self.runtime.memory.feedback(
            event["event_id"], "fact", "615 Euro",
            key="Project Elyra budget", permission="record")
        return self.runtime.memory.candidate(mid, self.runtime.session)

    def invoke(self, *flags):
        if self.runtime is not None:
            self.runtime.close()
            self.runtime = None
        out = io.StringIO()
        args = ["--home", str(self.home),
                "--query", "What is the budget for Project Elyra?", *flags]
        with patch.object(RunnerPool, "get", side_effect=AssertionError("NATIVE_C3_CALLED")), \
             contextlib.redirect_stdout(out):
            code = cli.main(args)
        return code, json.loads(out.getvalue())

    def test_exact_source_is_executable_without_native_or_learning(self):
        self.source()
        code, got = self.invoke("--exact")
        self.assertEqual(code, 0, got)
        self.assertEqual(got["status"], "FINAL_SOURCE_EXACT")
        self.assertEqual(got["answer"], "Project Elyra: 615 Euro.")
        self.assertEqual(got["authority"], "EXACT_SOURCE")
        self.assertEqual(got["native_calls"], 0)
        self.assertFalse(got["model_called"])
        self.assertFalse(got["learned"])
        self.assertFalse(got["semantic_encoder_may_run"])

    def test_missing_source_refuses_exact_answer(self):
        code, got = self.invoke("--exact")
        self.assertEqual(code, 0)
        self.assertEqual(got["status"], "CLARIFY")
        self.assertNotIn("615 Euro", got.get("answer", ""))

    def test_revoked_source_refuses_exact_answer(self):
        row = self.source()
        self.runtime.memory.forget(row["id"])
        code, got = self.invoke("--exact")
        self.assertEqual(code, 0)
        self.assertEqual(got["status"], "CLARIFY")
        self.assertNotIn("615 Euro", got.get("answer", ""))

    def test_existing_default_is_preflight_only(self):
        self.source()
        code, got = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(got["status"], "READY")
        self.assertNotIn("answer", got)
        self.assertEqual(got["native_calls"], 0)

    def test_native_and_exact_modes_are_mutually_exclusive(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            cli.main(["--home", str(self.home), "--query", "budget",
                      "--native", "--exact"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("not allowed with argument", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
