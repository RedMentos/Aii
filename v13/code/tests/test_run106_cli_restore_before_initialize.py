"""Run106: source-answer must reconcile restore journal before initialize/Store."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.__main__ import main
from v13.runtime import Runtime


QUESTION = "What is the budget for Project Elyra?"


class SourceAnswerRestoreOrder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        r = Runtime(self.home)
        try:
            r.sleep.cycle.set_policy("enabled", "off")
            e = r.store.event(r.session, "Project Elyra budget")
            self.memory_id = r.memory.feedback(
                e["event_id"], "fact", "615 Euro",
                key="Project Elyra budget", permission="record")
        finally:
            r.close()

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, home=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--home", str(home or self.home), "source-answer", QUESTION])
        return code, json.loads(out.getvalue())

    def pending(self, stage, old):
        journal = self.home / "restore_pending.json"
        journal.write_text(json.dumps({
            "stage": stage, "old": old, "safety_backup": "none"
        }), encoding="utf-8")
        return journal

    def db_sha(self):
        return hashlib.sha256(
            (self.home / "data/db/brain.sqlite3").read_bytes()).hexdigest()

    def test_invalid_journal_fails_before_initialize_or_store(self):
        before = self.db_sha()
        journal = self.pending("../outside", "../outside-old")
        with patch("v13.__main__.initialize",
                   side_effect=AssertionError("INITIALIZE_BEFORE_RECOVERY")) as init:
            code, result = self.cli()
        self.assertEqual(code, 2)
        self.assertEqual(result, {"status": "ERROR", "reason": "ValueError"})
        self.assertEqual(init.call_count, 0)
        self.assertTrue(journal.exists())
        self.assertEqual(self.db_sha(), before)

    def test_live_coordinator_pending_journal_refuses_before_initialize(self):
        r = Runtime(self.home)
        try:
            r.sleep.cycle.set_policy("enabled", "off")
            journal = self.pending("tmp/stage-empty", "tmp/old-empty")
            with patch("v13.__main__.initialize",
                       side_effect=AssertionError("INITIALIZE_BEFORE_RECOVERY")) as init:
                code, result = self.cli()
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "ERROR")
            self.assertIn(result["reason"], {"BlockingIOError", "OSError"})
            self.assertEqual(init.call_count, 0)
            self.assertTrue(journal.exists())
        finally:
            r.close()

    def test_valid_noop_recovery_precedes_real_source_answer(self):
        journal = self.pending("tmp/stage-empty", "tmp/old-empty")
        code, result = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["memory_id"], self.memory_id)
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["model_called"])
        self.assertFalse(journal.exists())

    def test_missing_home_and_normal_route(self):
        missing = Path(self.tmp.name) / "missing"
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.cli(missing)
        self.assertFalse(missing.exists())
        code, result = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["native_calls"], 0)


if __name__ == "__main__":
    unittest.main()
