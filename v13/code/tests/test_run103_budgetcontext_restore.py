"""Run103: shared BudgetContext must recover pending restore before any Store open."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import ask_verified_budget, source_exact
from v13.runtime import Runtime


QUESTION = "What is the budget for Project Elyra?"


class SharedRestoreGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        runtime = Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            event = runtime.store.event(runtime.session, "Project Elyra budget")
            runtime.memory.feedback(event["event_id"], "fact", "615 Euro",
                                    key="Project Elyra budget", permission="record")
        finally:
            runtime.close()

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, entrypoint, home=None):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = entrypoint.main(["--home", str(home or self.home), "--query", QUESTION])
        return code, json.loads(stdout.getvalue())

    def pending(self, stage, old):
        journal = self.home / "restore_pending.json"
        journal.write_text(json.dumps({"stage": stage, "old": old,
                                       "safety_backup": "none"}), encoding="utf-8")
        return journal

    def db_hash(self):
        return hashlib.sha256(
            (self.home / "data/db/brain.sqlite3").read_bytes()).hexdigest()

    def test_normal_shared_budgetcontext_and_both_cli_routes(self):
        ctx = ask_verified_budget.BudgetContext(self.home)
        try:
            self.assertEqual(ask_verified_budget.query(ctx, QUESTION)["status"], "READY")
        finally:
            ctx.close()
        for cli, status in ((ask_verified_budget, "READY"),
                            (source_exact, "FINAL")):
            with self.subTest(cli=cli.__name__):
                code, value = self.cli(cli)
                self.assertEqual(code, 0)
                self.assertEqual(value["status"], status)
                self.assertEqual(value["native_calls"], 0)
                self.assertFalse(value["model_called"])
                if status == "FINAL":
                    self.assertEqual(value["answer"], "Project Elyra budget: 615 Euro.")

    def test_invalid_pending_restore_refuses_before_store_for_all_entrypoints(self):
        for entry in ("direct", "budget", "exact"):
            with self.subTest(entry=entry):
                before = self.db_hash()
                journal = self.pending("../outside", "../outside-old")
                with patch.object(ask_verified_budget, "Store",
                                  side_effect=AssertionError("STORE_OPENED")) as constructor:
                    if entry == "direct":
                        with self.assertRaises(ValueError):
                            ask_verified_budget.BudgetContext(self.home)
                    else:
                        cli = ask_verified_budget if entry == "budget" else source_exact
                        code, result = self.cli(cli)
                        self.assertEqual(code, 2)
                        self.assertEqual(result, {"status": "ERROR", "reason": "ValueError"})
                    self.assertEqual(constructor.call_count, 0)
                self.assertTrue(journal.is_file())
                self.assertEqual(self.db_hash(), before)
                journal.unlink()

    def test_valid_noop_pending_journal_reconciled_before_each_cli(self):
        for cli, expected in ((ask_verified_budget, "READY"),
                              (source_exact, "FINAL")):
            with self.subTest(cli=cli.__name__):
                journal = self.pending("tmp/stage-empty", "tmp/old-empty")
                code, result = self.cli(cli)
                self.assertEqual(code, 0)
                self.assertEqual(result["status"], expected)
                self.assertFalse(journal.exists())

    def test_active_coordinator_lock_with_pending_restore_refuses_all_cli(self):
        runtime = Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            journal = self.pending("tmp/stage-empty", "tmp/old-empty")
            for cli in (ask_verified_budget, source_exact):
                with self.subTest(cli=cli.__name__):
                    with patch.object(ask_verified_budget, "Store",
                                      side_effect=AssertionError("STORE_OPENED")) as constructor:
                        code, result = self.cli(cli)
                        self.assertEqual(code, 2)
                        self.assertEqual(result["status"], "ERROR")
                        self.assertIn(result["reason"], {"BlockingIOError", "OSError"})
                        self.assertEqual(constructor.call_count, 0)
                        self.assertTrue(journal.exists())
        finally:
            runtime.close()

    def test_missing_home_remains_missing(self):
        missing = Path(self.tmp.name) / "missing"
        for cli in (ask_verified_budget, source_exact):
            with self.subTest(cli=cli.__name__):
                code, result = self.cli(cli, missing)
                self.assertEqual(code, 2)
                self.assertEqual(result["reason"], "EXISTING_HOME_REQUIRED")
                self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
