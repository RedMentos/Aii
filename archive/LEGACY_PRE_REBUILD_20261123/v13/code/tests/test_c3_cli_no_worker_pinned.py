"""No-worker existing-home C3 CLI and canonical model provenance tests."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from v13.runtime import Runtime
from scripts.ask_verified_budget import BudgetContext, _pinned_c3, main, query


class C3CliNoWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.session = self.r.session
        e = self.r.store.event(self.session, "Project Elyra budget")
        self.r.memory.feedback(e["event_id"], "fact", "615 Euro",
                               key="Project Elyra budget", permission="record")
        self.r.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_home_context_has_no_worker_or_sleep_mutation(self):
        settings = (self.home / "config/settings.json").read_bytes()
        with open(self.home / "data/db/brain.sqlite3", "rb") as f:
            self.assertTrue(f.read(16).startswith(b"SQLite format 3"))
        ctx = BudgetContext(self.home)
        try:
            self.assertFalse(hasattr(ctx, "worker"))
            self.assertFalse(hasattr(ctx, "sleep"))
            self.assertEqual(ctx.session, self.session)
            self.assertTrue(ctx.idle())
            result = query(ctx, "What is the budget for Project Elyra?")
            self.assertEqual(result["status"], "READY")
            self.assertEqual(result["native_calls"], 0)
        finally:
            ctx.close()
        self.assertEqual((self.home / "config/settings.json").read_bytes(), settings)

    def test_existing_home_wrong_session_does_not_create_session(self):
        ctx = BudgetContext(self.home)
        try:
            before = ctx.store.one("SELECT COUNT(*) AS n FROM sessions")["n"]
            result = query(ctx, "What is the budget for Project Elyra?",
                           session="chat_nonexistent")
            after = ctx.store.one("SELECT COUNT(*) AS n FROM sessions")["n"]
            self.assertEqual(result["reason"], "SESSION_NOT_FOUND")
            self.assertEqual(before, after)
        finally:
            ctx.close()

    def test_imported_self_hashed_model_is_not_canonical_pin(self):
        ctx = BudgetContext(self.home)
        try:
            spec = ctx.models.specs["models"]["language"]
            file = next(f for f in spec["files"] if f["local_name"] == spec["main_file"])
            installed = {"model_id": spec["model_id"],
                         "exact_revision": spec["revision"],
                         "main_file": spec["main_file"],
                         "license_id": spec["license_id"],
                         "quant_format": spec["quant_format"],
                         "files": {spec["main_file"]: {
                             "sha256": file["sha256"], "size": file["size"],
                             "path": "models/language/fake.gguf"}}}
            ctx.models.installed["language"] = installed
            self.assertTrue(_pinned_c3(ctx.models))
            ctx.models.installed["language"] = dict(installed, model_id="operator-import")
            self.assertFalse(_pinned_c3(ctx.models))
            ctx.models.installed["language"] = dict(installed, files={
                spec["main_file"]: {"sha256": "0"*64, "size": file["size"]}})
            self.assertFalse(_pinned_c3(ctx.models))
            ctx.models.installed["language"] = installed
            self.assertEqual(query(ctx, "What is the budget for Project Elyra?",
                                   native=True)["status"], "C3_MODEL_NOT_VERIFIED")
        finally:
            ctx.close()

    def test_main_refuses_missing_home_without_creating_it(self):
        missing = self.home / "not-existing"
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--home", str(missing),
                         "--query", "What is the budget for Project Elyra?"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())["reason"], "EXISTING_HOME_REQUIRED")
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
