"""Run98: human interactive SOURCE_EXACT factual answer from real F1/F5 source."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.operator import Operator
from v13.runtime import Runtime


QUERY = "What is the budget for Project Elyra?"


class LiveSourceExactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def source_answer(self, question=QUERY):
        return json.loads(self.op.run(":source answer " + question))

    def test_no_source_then_record_exact_answer_restart_and_forget(self):
        with patch.object(self.r.pool, "get", side_effect=AssertionError("NATIVE_CALLED")):
            missing = self.source_answer()
            self.assertEqual(missing["status"], "CLARIFY")
            self.assertNotIn("615 Euro", missing.get("answer", ""))
            preview = json.loads(self.op.run(":source budget Elyra 615"))
            self.assertEqual(preview["status"], "CONFIRM_REQUIRED")
            self.assertFalse(preview["writes"])
            recorded = json.loads(self.op.run(":source budget Elyra 615 --confirm"))
            self.assertEqual(recorded["status"], "RECORDED_VERIFIED")
            result = self.source_answer()
            self.assertEqual(result["status"], "FINAL")
            self.assertEqual(result["mode"], "SOURCE_EXACT")
            self.assertEqual(result["answer"], "Project Elyra budget: 615 Euro.")
            self.assertEqual(result["memory_id"], recorded["memory_id"])
            self.assertEqual(result["source_ref"], recorded["source_ref"])
            self.assertFalse(result["model_called"])
            self.assertEqual(result["native_calls"], 0)
            self.assertEqual(json.loads(self.op.run(":verified " + QUERY))["status"], "READY")
            wrong = self.source_answer("What is the budget for Project Dovan?")
            outside = self.source_answer("Who leads Project Elyra?")
            self.assertEqual(wrong["status"], "CLARIFY")
            self.assertEqual(outside["status"], "NOT_APPLICABLE")
            self.assertFalse(wrong.get("answer"))
            self.assertFalse(outside.get("answer"))
        self.assertIn(":source answer", self.op.run(":help"))

        first_session = self.r.session
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.assertEqual(self.r.session, first_session)
        self.assertEqual(self.source_answer()["answer"], "Project Elyra budget: 615 Euro.")
        self.op.run(":forget " + recorded["memory_id"] + " --confirm")
        after = self.source_answer()
        self.assertEqual(after["status"], "CLARIFY")
        self.assertEqual(after["native_calls"], 0)
        self.assertNotIn("615 Euro", after.get("answer", ""))

    def test_empty_oversize_non_tty_and_nonidle_rejected(self):
        with self.assertRaises(ValueError):
            self.op.run(":source answer")
        with self.assertRaises(ValueError):
            self.op.run(":source answer " + "x" * (self.r.cfg["input_bytes"] + 1))
        with self.assertRaisesRegex(ValueError, "Nur lokale Operator"):
            self.op.run(":source answer " + QUERY, origin="MODEL")
        with patch.object(self.r, "idle", return_value=False):
            with self.assertRaisesRegex(ValueError, "RUNTIME_NOT_IDLE"):
                self.source_answer()


if __name__ == "__main__":
    unittest.main()
