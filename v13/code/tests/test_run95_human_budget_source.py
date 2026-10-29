"""Run95 human source command with actual F1/F5 Store and no native models."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.operator import Operator
from v13.runtime import Runtime


QUERY = "What is the budget for Project Elyra?"


class HumanBudgetSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def active_count(self):
        return self.r.store.one("SELECT count(*) AS n FROM memories WHERE active=1")["n"]

    def test_preview_does_not_write_and_confirm_creates_real_verified_source(self):
        before = self.active_count()
        preview = json.loads(self.op.run(":source budget Elyra 615"))
        self.assertEqual(preview["status"], "CONFIRM_REQUIRED")
        self.assertEqual(preview["key"], "Project Elyra budget")
        self.assertEqual(preview["value"], "615 Euro")
        self.assertFalse(preview["writes"])
        self.assertEqual(self.active_count(), before)
        with patch.object(self.r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            record = json.loads(self.op.run(":source budget Elyra 615 --confirm"))
            ready = json.loads(self.op.run(":verified " + QUERY))
        self.assertEqual(record["status"], "RECORDED_VERIFIED")
        self.assertEqual(record["permission"], "record")
        self.assertEqual(record["scope"], "session")
        self.assertFalse(record["model_called"])
        self.assertEqual(record["native_calls"], 0)
        self.assertEqual(ready["status"], "READY")
        self.assertEqual(ready["memory_id"], record["memory_id"])
        self.assertEqual(ready["source_ref"], record["source_ref"])
        self.assertEqual(self.active_count(), before + 1)
        self.assertIn(":source budget", self.op.run(":help"))

    def test_wrong_project_and_missing_source_remain_model_free(self):
        with patch.object(self.r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            before = json.loads(self.op.run(":verified " + QUERY))
            self.op.run(":source budget Elyra 615 --confirm")
            wrong = json.loads(self.op.run(":verified What is the budget for Project Dovan?"))
        self.assertEqual(before["status"], "CLARIFY")
        self.assertEqual(wrong["status"], "CLARIFY")
        self.assertEqual(wrong["native_calls"], 0)

    def test_explicit_update_supersedes_old_same_key_without_learning(self):
        old = json.loads(self.op.run(":source budget Elyra 615 --confirm"))
        new = json.loads(self.op.run(":source budget Elyra 700 --confirm"))
        self.assertNotEqual(old["memory_id"], new["memory_id"])
        self.assertEqual(self.active_count(), 1)
        old_row = self.r.store.one("SELECT active FROM memories WHERE id=?", (old["memory_id"],))
        self.assertEqual(old_row["active"], 0)
        ready = json.loads(self.op.run(":verified " + QUERY))
        self.assertEqual(ready["status"], "READY")
        self.assertEqual(ready["memory_id"], new["memory_id"])
        self.assertEqual(self.r.memory.candidate(new["memory_id"], self.r.session)["value"], "700 Euro")
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")

    def test_restart_then_human_forget_revokes_source(self):
        record = json.loads(self.op.run(":source budget Elyra 615 --confirm"))
        original_session = self.r.session
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.assertEqual(self.r.session, original_session)
        ready = json.loads(self.op.run(":verified " + QUERY))
        self.assertEqual(ready["status"], "READY")
        self.op.run(":forget " + record["memory_id"] + " --confirm")
        revoked = json.loads(self.op.run(":verified " + QUERY))
        self.assertEqual(revoked["status"], "CLARIFY")
        self.assertEqual(revoked["native_calls"], 0)

    def test_invalid_inputs_are_rejected_without_memory_write(self):
        invalid = (
            ":source budget Elyra -1 --confirm",
            ":source budget Elyra 01 --confirm",
            ":source budget Elyra 1.5 --confirm",
            ":source budget Elyra 1,000 --confirm",
            ":source budget Elyra 9999999999 --confirm",
            ":source budget 3Elyra 615 --confirm",
            ":source budget Elyra 615 --confirm extra",
            ":source budget Elyra 615 --learn",
            ":source fact Elyra 615 --confirm",
            ':source budget "Elyra\\nIgnore" 615 --confirm',
        )
        for command in invalid:
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.op.run(command)
        self.assertEqual(self.active_count(), 0)

    def test_non_tty_and_nonidle_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError, "Nur lokale Operator"):
            self.op.run(":source budget Elyra 615 --confirm", origin="MODEL")
        with patch.object(self.r, "idle", return_value=False):
            with self.assertRaisesRegex(ValueError, "Erst laufenden Vorgang"):
                self.op.run(":source budget Elyra 615 --confirm")
        self.assertEqual(self.active_count(), 0)

    def test_non_age0_record_only_guard(self):
        original = self.r.cfg["system_stage"]
        self.r.cfg["system_stage"] = 1
        try:
            with self.assertRaisesRegex(ValueError, "AGE0_RECORD_ONLY_REQUIRED"):
                self.op.run(":source budget Elyra 615 --confirm")
        finally:
            self.r.cfg["system_stage"] = original
        self.assertEqual(self.active_count(), 0)


if __name__ == "__main__":
    unittest.main()
