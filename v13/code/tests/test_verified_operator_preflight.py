"""Local TTY source-verification preflight only; no C3 native call."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.operator import HELP, Operator
from v13.runtime import Runtime


class VerifiedOperatorPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.question = "What is the budget for Project Elyra?"

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def add(self, key="Project Elyra budget", value="615 Euro"):
        e = self.r.store.event(self.r.session, key)
        mid = self.r.memory.feedback(e["event_id"], "fact", value,
                                     key=key, permission="record")
        return mid

    def run_preflight(self, question=None):
        line = ":verified " + (self.question if question is None else question)
        with patch.object(self.r.pool, "get", side_effect=AssertionError("native called")):
            return json.loads(self.op.run(line))

    def test_help_and_verified_source_ready_without_model_or_new_session(self):
        self.assertIn(":verified <Frage>", HELP)
        mid = self.add()
        before = self.r.store.rows("SELECT id FROM sessions ORDER BY id")
        result = self.run_preflight()
        after = self.r.store.rows("SELECT id FROM sessions ORDER BY id")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["memory_id"], mid)
        self.assertEqual(result["model_called"], False)
        self.assertEqual(result["native_calls"], 0)
        self.assertNotIn("answer", result)
        self.assertEqual(before, after)

    def test_missing_wrong_project_conflict_and_revocation_fail_closed(self):
        self.assertEqual(self.run_preflight()["status"], "CLARIFY")
        self.add(key="Project Dovan budget", value="700 Euro")
        self.assertEqual(self.run_preflight()["status"], "CLARIFY")
        first = self.add()
        self.assertEqual(self.run_preflight()["status"], "READY")
        self.add(key="Project Elyra budgets", value="700 Euro")
        self.assertEqual(self.run_preflight()["status"], "CLARIFY")
        self.r.memory.forget(first)
        self.assertEqual(self.run_preflight()["status"], "READY")

    def test_out_of_scope_is_not_applicable_and_never_generates(self):
        result = self.run_preflight("Hello, how are you?")
        self.assertEqual(result["status"], "NOT_APPLICABLE")
        self.assertEqual(result["native_calls"], 0)

    def test_native_request_is_rejected_even_with_valid_source(self):
        self.add()
        for line in (":verified native " + self.question,
                     ":verified " + self.question + " --native",
                     ":verified --native " + self.question,
                     ":verified"):
            with self.subTest(line=line):
                with patch.object(self.r.pool, "get", side_effect=AssertionError("native called")):
                    with self.assertRaisesRegex(ValueError, "Vorprüfung"):
                        self.op.run(line)

    def test_non_tty_nonidle_and_oversize_refused(self):
        self.add()
        with self.assertRaisesRegex(ValueError, "lokale Operator"):
            self.op.run(":verified " + self.question, origin="REMOTE")
        with patch.object(self.r, "idle", return_value=False):
            with self.assertRaises(ValueError):
                self.op.run(":verified " + self.question)
        original = self.r.cfg["input_bytes"]
        try:
            self.r.cfg["input_bytes"] = 12
            with self.assertRaisesRegex(ValueError, "zu lang"):
                self.op.run(":verified " + self.question)
        finally:
            self.r.cfg["input_bytes"] = original


if __name__ == "__main__":
    unittest.main()
