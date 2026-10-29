"""Run102: standalone SOURCE_EXACT must recover or refuse before Store opens."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import source_exact
from v13.runtime import Runtime


QUESTION = "What is the budget for Project Elyra?"


class SourceExactRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        r = Runtime(self.home)
        try:
            r.sleep.cycle.set_policy("enabled", "off")
            event = r.store.event(r.session, "Project Elyra budget")
            self.memory_id = r.memory.feedback(
                event["event_id"], "fact", "615 Euro",
                key="Project Elyra budget", permission="record")
        finally:
            r.close()

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, home=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = source_exact.main([
                "--home", str(home if home is not None else self.home),
                "--query", QUESTION])
        return code, json.loads(output.getvalue())

    def journal(self, stage, old):
        path = self.home / "restore_pending.json"
        path.write_text(json.dumps({
            "stage": stage, "old": old, "safety_backup": "none"
        }), encoding="utf-8")
        return path

    def db_hash(self):
        return hashlib.sha256(
            (self.home / "data/db/brain.sqlite3").read_bytes()).hexdigest()

    def test_normal_existing_home_returns_source_exact_without_model(self):
        with patch.object(source_exact, "BudgetContext",
                          wraps=source_exact.BudgetContext) as constructor:
            code, result = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "FINAL")
        self.assertEqual(result["answer"], "Project Elyra budget: 615 Euro.")
        self.assertEqual(result["memory_id"], self.memory_id)
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["model_called"])
        self.assertEqual(constructor.call_count, 1)

    def test_invalid_restore_journal_refuses_before_store_and_preserves_db(self):
        before = self.db_hash()
        pending = self.journal("../outside", "../outside-old")
        with patch.object(source_exact, "BudgetContext",
                          side_effect=AssertionError("STORE_OPENED")) as constructor:
            code, result = self.cli()
        self.assertEqual(code, 2)
        self.assertEqual(result, {"status": "ERROR", "reason": "ValueError"})
        self.assertEqual(constructor.call_count, 0)
        self.assertTrue(pending.is_file())
        self.assertEqual(self.db_hash(), before)

    def test_valid_noop_restore_journal_recovered_before_source_read(self):
        before = self.db_hash()
        pending = self.journal("tmp/stage-empty", "tmp/old-empty")
        code, result = self.cli()
        self.assertEqual(code, 0)
        self.assertFalse(pending.exists())
        self.assertEqual(result["status"], "FINAL")
        self.assertEqual(result["answer"], "Project Elyra budget: 615 Euro.")
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(self.db_hash(), before)

    def test_live_store_lock_with_pending_restore_refuses(self):
        r = Runtime(self.home)
        try:
            r.sleep.cycle.set_policy("enabled", "off")
            pending = self.journal("tmp/stage-empty", "tmp/old-empty")
            with patch.object(source_exact, "BudgetContext",
                              side_effect=AssertionError("STORE_OPENED")) as constructor:
                code, result = self.cli()
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "ERROR")
            self.assertIn(result["reason"], {"BlockingIOError", "OSError"})
            self.assertEqual(constructor.call_count, 0)
            self.assertTrue(pending.exists())
            self.assertNotIn("answer", result)
        finally:
            r.close()

    def test_missing_home_is_not_created(self):
        missing = Path(self.tmp.name) / "missing"
        code, result = self.cli(missing)
        self.assertEqual(code, 2)
        self.assertEqual(result["reason"], "EXISTING_HOME_REQUIRED")
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
