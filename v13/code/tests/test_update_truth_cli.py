"""Regression: local V13 source check must match installed phone and update status.

No GitHub/phone/native weights are needed. The real GitHub CI workflow runs
these tests against the exact proposed source revision.
"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13 import pipeline_agent as p
from v13 import source_updater as u


class UpdateTruthCLITests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name)
        private = home / ".v13-private"
        private.mkdir(mode=0o700)
        (home / ".v13-runtime-source").mkdir()
        (home / ".v13-agent-source").mkdir()
        for obj, key, value in [
            (p.Path, "home", lambda: home),
            (p, "PRIVATE", private),
            (p, "STATE", private / "pipeline-status.json"),
            (p, "LOCK", private / "pipeline-status.lock"),
            (p, "ENABLED", private / "auto-source-update.enabled"),
            (p, "UI_REFRESH", private / "pipeline-ui-refresh"),
            (p, "BRIDGE_REFRESH", private / "pipeline-bridge-refresh"),
            (p, "AI_REFRESH", private / "pipeline-ai-refresh"),
        ]:
            patch = mock.patch.object(obj, key, value)
            patch.start()
            self.addCleanup(patch.stop)
        self.home = home

    def _cli(self, *argv):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = p.main(list(argv))
        return code, json.loads(stream.getvalue())

    def test_persisted_dashboard_failure_is_not_phone_up_to_date(self):
        p.STATE.write_text(json.dumps({
            "runtime": "UP_TO_DATE", "dashboard": "ERROR",
            "last_result": "UP_TO_DATE", "last_error": "NONE",
            "updated_commit": "a" * 40
        }))
        status = p.snapshot()
        self.assertEqual(status["dashboard"], "ERROR")
        self.assertEqual(status["last_result"], "PARTIAL")
        self.assertEqual(status["last_error"], "UPDATE")
        code, cli = self._cli("status")
        self.assertEqual(code, 2)
        self.assertEqual(cli["last_result"], "PARTIAL")

    def test_runtime_only_cycle_cannot_erase_dashboard_error(self):
        p.STATE.write_text(json.dumps({
            "runtime": "UP_TO_DATE", "dashboard": "ERROR",
            "last_result": "PARTIAL", "last_error": "NONE",
        }))
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={
                 "status": "UP_TO_DATE", "current": "a" * 40,
                 "available": "a" * 40, "changed_files": 0}), \
             mock.patch.object(p.runtime_deploy, "prepare_source",
                               return_value={"status": "READY"}), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", return_value=False):
            result = p.run_cycle(force=True, manual=True, target="runtime")
        self.assertEqual(result["runtime"], "UP_TO_DATE")
        self.assertEqual(result["dashboard"], "ERROR")
        self.assertEqual(result["last_result"], "PARTIAL")
        self.assertEqual(result["last_error"], "UPDATE")

    def test_cli_apply_runs_installed_two_target_pipeline(self):
        output = {"last_result": "UPDATED", "runtime": "UPDATED",
                  "dashboard": "UP_TO_DATE"}
        with mock.patch.object(p, "run_cycle", return_value=output) as cycle:
            code, result = self._cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["last_result"], "UPDATED")
        cycle.assert_called_once_with(force=True, manual=True, target="all")

    def test_cli_does_not_claim_success_on_partial_update(self):
        output = {"last_result": "PARTIAL", "runtime": "UP_TO_DATE",
                  "dashboard": "ERROR"}
        with mock.patch.object(p, "run_cycle", return_value=output):
            code, result = self._cli("apply")
        self.assertEqual(code, 2)
        self.assertEqual(result["dashboard"], "ERROR")

    def test_auto_off_is_respected_even_from_command_line(self):
        with mock.patch.object(p, "run_cycle") as cycle:
            code, result = self._cli("auto")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "AUTO_OFF")
        cycle.assert_not_called()

    def test_legacy_rollback_does_not_fake_launcher_rollback(self):
        code, result = self._cli("rollback")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "REFUSED")

    def test_check_error_has_nonzero_exit_status(self):
        with mock.patch.object(p, "pending_updates", return_value={
                "status": "ERROR", "runtime": "UP_TO_DATE", "dashboard": "ERROR",
                "verified_current": False}):
            code, report = self._cli("check")
        self.assertEqual(code, 2)
        self.assertEqual(report["dashboard"], "ERROR")

    def test_termux_command_uses_pipeline_not_legacy_source_updater(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "v13-update"
        data = script.read_text(encoding="utf-8")
        self.assertIn("python -m v13.pipeline_agent", data)
        self.assertNotIn("python -m v13.source_updater", data)


if __name__ == "__main__":
    unittest.main()
