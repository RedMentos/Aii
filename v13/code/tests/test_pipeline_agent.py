"""Offline CI-gated pipeline tests; no external GitHub calls or phone writes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from v13 import pipeline_agent as p
from v13 import source_updater as u


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name) / "private"
        base.mkdir(mode=0o700)
        self.base = base
        home = base.parent
        (home / "V13-Phone").mkdir()
        (home / ".v13-agent-source").mkdir()
        home_patch = mock.patch.object(p.Path, "home", return_value=home)
        home_patch.start()
        self.addCleanup(home_patch.stop)
        for key, value in (
            ("PRIVATE", base),
            ("ENABLED", base / "auto-source-update.enabled"),
            ("STATE", base / "pipeline-status.json"),
            ("LOCK", base / "pipeline-status.lock"),
            ("UI_REFRESH", base / "pipeline-ui-refresh"),
            ("BRIDGE_REFRESH", base / "pipeline-bridge-refresh"),
        ):
            patch = mock.patch.object(p, key, value)
            patch.start()
            self.addCleanup(patch.stop)

    def turn_on(self):
        p.ENABLED.write_text("yes\n")
        p.ENABLED.chmod(0o600)

    def test_off_by_default_and_no_git_calls(self):
        with mock.patch.object(u, "status") as status:
            s = p.run_cycle(force=True)
        self.assertFalse(s["auto_enabled"])
        self.assertEqual(s["last_result"], "NOT_YET_RUN")
        status.assert_not_called()

    def test_signed_ci_success_required_for_both_checkouts(self):
        self.turn_on()
        commit = "a" * 40
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={
                 "status": "UPDATE_AVAILABLE", "available": commit, "current": "0"*40,
                 "changed_files": 4}), \
             mock.patch.object(u, "ci_passed", return_value=True) as ci, \
             mock.patch.object(u, "apply", return_value={"status":"UPDATED"}) as apply, \
             mock.patch.object(u, "apply_dashboard", return_value={"status":"UPDATED"}) as dash:
            result = p.run_cycle(force=True, now=2000000000)
        self.assertEqual(result["last_result"], "UPDATED")
        self.assertEqual(result["runtime"], "UPDATED")
        self.assertEqual(result["dashboard"], "UPDATED")
        self.assertEqual(result["updated_commit"], commit)
        self.assertTrue(p.refresh_requested("ui"))
        self.assertTrue(p.refresh_requested("bridge"))
        self.assertEqual(ci.call_count, 1, "one exact commit must be checked once")
        self.assertEqual(apply.call_args.kwargs["expected_tip"], commit)
        self.assertEqual(dash.call_args.kwargs["expected_tip"], commit)
        self.assertTrue(p.acknowledge_refresh("ui"))
        self.assertFalse(p.refresh_requested("ui"))

    def test_ci_not_green_blocks_both_and_writes_status(self):
        self.turn_on()
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"a"*40}), \
             mock.patch.object(u, "ci_passed", return_value=False), \
             mock.patch.object(u, "apply") as apply, \
             mock.patch.object(u, "apply_dashboard") as dashboard:
            status = p.run_cycle(force=True,now=2000000000)
        self.assertEqual(status["last_result"], "CI_WAIT")
        apply.assert_not_called()
        dashboard.assert_not_called()
        self.assertFalse(p.refresh_requested("ui"))
        self.assertEqual(p.STATE.stat().st_mode & 0o777, 0o600)

    def test_running_model_blocks_all_changes(self):
        self.turn_on()
        with mock.patch.object(u, "_runtime_active", return_value=True), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"b"*40}), \
             mock.patch.object(u, "ci_passed") as ci, \
             mock.patch.object(u, "apply") as apply:
            status = p.run_cycle(force=True,now=2000000000)
        self.assertEqual(status["last_result"], "BLOCKED_RUNNING")
        self.assertEqual(status["runtime"], "BLOCKED_RUNNING")
        self.assertEqual(status["dashboard"], "BLOCKED_RUNNING")
        ci.assert_not_called()
        apply.assert_not_called()

    def test_15_minute_interval_and_forced_manual_check(self):
        self.turn_on()
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={"status":"UP_TO_DATE"}) as status:
            self.assertEqual(p.run_cycle(now=2000000000)["last_result"], "UP_TO_DATE")
            self.assertEqual(p.run_cycle(now=2000000010)["last_result"], "UP_TO_DATE")
            self.assertEqual(status.call_count, 2)
            self.assertEqual(p.run_cycle(force=True,now=2000000011)["last_result"], "UP_TO_DATE")
            self.assertEqual(status.call_count, 4)

    def test_missing_runtime_does_not_block_ui(self):
        self.turn_on()
        def fake_status(root):
            if root.name == "V13-Phone":
                raise u.UpdateDenied("missing Git checkout")
            return {"status":"UP_TO_DATE"}
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", side_effect=fake_status):
            result=p.run_cycle(force=True)
        self.assertIn(result["runtime"], ("NOT_INSTALLED", "ERROR"))
        self.assertEqual(result["dashboard"], "UP_TO_DATE")

    def test_snapshot_ignores_freeform_secrets(self):
        self.turn_on()
        p.STATE.write_text(json.dumps({"last_result":"token github_pat_PRIVATE","runtime":"SHELL",
                                       "last_error":"/data/data/private","updated_commit":"zzzz"}))
        report=p.snapshot()
        self.assertNotIn("github_pat_",str(report))
        self.assertNotIn("/data/",str(report))
        self.assertEqual(report["last_result"],"ERROR")


class GitHubCIProofTests(unittest.TestCase):
    @staticmethod
    def workflow(commit, **changes):
        result={"head_sha":commit, "name":u.CI_WORKFLOW, "path":u.CI_WORKFLOW_PATH+"@refs/heads/gpt6/v13-private-remote-bridge-20261111",
                "status":"completed", "conclusion":"success",
                "head_repository":{"full_name":"RedMentos/Aii"}}
        result.update(changes)
        return result

    def test_workflow_must_be_exact_commit_name_path_and_success(self):
        commit="b"*40
        variants=[
            self.workflow(commit),
            self.workflow("c"*40),
            self.workflow(commit,conclusion="failure"),
            self.workflow(commit,path=".github/workflows/fake.yml"),
            self.workflow(commit,name="Other workflow"),
            self.workflow(commit,head_repository={"full_name":"attacker/fork"}),
            self.workflow(commit,status="in_progress")
        ]
        for i,row in enumerate(variants):
            proc=mock.Mock(returncode=0,stdout=json.dumps({"workflow_runs":[row]}))
            with self.subTest(i=i), mock.patch.object(u.subprocess,"run",return_value=proc):
                self.assertEqual(u.ci_passed(commit),i==0)

    def test_no_CI_run_never_allows_auto(self):
        with mock.patch.object(u.subprocess,"run",return_value=mock.Mock(returncode=0,stdout='{"workflow_runs": []}')):
            self.assertFalse(u.ci_passed("a"*40))


if __name__=="__main__":
    unittest.main()
