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
        (home / ".v13-runtime-source").mkdir()
        (home / ".v13-agent-source").mkdir()
        home_patch = mock.patch.object(p.Path, "home", return_value=home)
        runtime_needs = mock.patch.object(p.runtime_deploy, "needs_deploy", return_value=False)
        runtime_act = mock.patch.object(p.runtime_deploy, "deploy", return_value={"status":"DEPLOYED"})
        for helper in (runtime_needs,runtime_act):
            helper.start()
            self.addCleanup(helper.stop)
        home_patch.start()
        self.addCleanup(home_patch.stop)
        for key, value in (
            ("PRIVATE", base),
            ("ENABLED", base / "auto-source-update.enabled"),
            ("STATE", base / "pipeline-status.json"),
            ("LOCK", base / "pipeline-status.lock"),
            ("UI_REFRESH", base / "pipeline-ui-refresh"),
            ("BRIDGE_REFRESH", base / "pipeline-bridge-refresh"),
            ("AI_REFRESH", base / "pipeline-ai-refresh"),
            ("UPDATE_REQUEST", base / "pipeline-manual-request.json"),
        ):
            patch = mock.patch.object(p, key, value)
            patch.start()
            self.addCleanup(patch.stop)

    def turn_on(self):
        p.ENABLED.write_text("yes\n")
        p.ENABLED.chmod(0o600)

    def test_private_owner_update_request_is_queued_once_not_arbitrary_shell(self):
        from v13 import pipeline_agent as pa
        request="f"*32
        self.assertEqual(pa.schedule_update(request)["status"],"QUEUED")
        self.assertTrue(pa.UPDATE_REQUEST.is_file())
        self.assertEqual(pa.schedule_update("e"*32)["status"],"ALREADY_QUEUED")
        self.assertTrue(pa.claim_scheduled_update())
        self.assertFalse(pa.claim_scheduled_update())
        with self.assertRaises(ValueError):
            pa.schedule_update("../arbitrary;rm -rf")
        self.assertFalse(pa.UPDATE_REQUEST.exists())

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
        self.assertTrue(p.refresh_requested("ai"))
        self.assertEqual(ci.call_count, 2, "UI and runtime use different CI gates")
        self.assertEqual({c.kwargs["scope"] for c in ci.call_args_list},
                         {"runtime","dashboard"})
        self.assertEqual(apply.call_args.kwargs["expected_tip"], commit)
        self.assertEqual(dash.call_args.kwargs["expected_tip"], commit)
        self.assertTrue(p.acknowledge_refresh("ui"))
        self.assertFalse(p.refresh_requested("ui"))

    def test_source_up_to_date_but_old_v13_launcher_triggers_real_activation(self):
        self.turn_on()
        revision="e"*40
        with mock.patch.object(p.runtime_deploy,"needs_deploy", return_value=True), \
             mock.patch.object(u,"_runtime_active",return_value=False), \
             mock.patch.object(u,"status",return_value={
                 "status":"UP_TO_DATE","available":revision,"current":revision,
                 "changed_files":0}), \
             mock.patch.object(u,"ci_passed",return_value=True) as ci, \
             mock.patch.object(u,"apply") as apply, \
             mock.patch.object(u,"apply_dashboard") as dash, \
             mock.patch.object(p.runtime_deploy,"deploy",return_value={"status":"DEPLOYED"}) as deploy:
            result=p.run_cycle(force=True,now=2000000000)
        self.assertEqual(result["runtime"],"UPDATED")
        self.assertEqual(result["dashboard"],"UP_TO_DATE")
        self.assertTrue(p.refresh_requested("ai"))
        deploy.assert_called_once()
        apply.assert_not_called()
        dash.assert_not_called()
        ci.assert_called_once_with(revision,scope="runtime")

    def test_each_refresh_acknowledges_only_its_own_target(self):
        # Regression: AI previously acknowledged BRIDGE, re-execed forever.
        for marker in (p.UI_REFRESH, p.BRIDGE_REFRESH, p.AI_REFRESH):
            marker.write_text("test")
        self.assertTrue(p.acknowledge_refresh("ai"))
        self.assertFalse(p.refresh_requested("ai"))
        self.assertTrue(p.refresh_requested("bridge"))
        self.assertTrue(p.refresh_requested("ui"))
        self.assertTrue(p.acknowledge_refresh("bridge"))
        self.assertTrue(p.refresh_requested("ui"))
        self.assertFalse(p.refresh_requested("bridge"))
        self.assertTrue(p.acknowledge_refresh("ui"))
        self.assertFalse(p.refresh_requested("ui"))
        with self.assertRaises(ValueError):
            p.acknowledge_refresh("unknown")

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

    def test_running_managed_model_is_stopped_then_restarted(self):
        self.turn_on()
        commit="b"*40
        with mock.patch.object(u, "_runtime_active", side_effect=[True, False, False]) as running, \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":commit}), \
             mock.patch.object(u, "ci_passed", return_value=True), \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True) as stop, \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(u, "apply", return_value={"status":"UPDATED"}) as apply, \
             mock.patch.object(u, "apply_dashboard", return_value={"status":"UPDATED"}) as dash:
            status=p.run_cycle(force=True,now=2000000000)
        self.assertEqual(status["last_result"],"UPDATED")
        stop.assert_called_once()
        resume.assert_called_once_with(reason="UPDATED")
        apply.assert_called_once()
        dash.assert_called_once()

    def test_ci_failure_does_not_interrupt_running_model(self):
        self.turn_on()
        with mock.patch.object(u, "_runtime_active", return_value=True), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"b"*40}), \
             mock.patch.object(u, "ci_passed", return_value=False), \
             mock.patch.object(p.lifecycle, "request_stop") as stop, \
             mock.patch.object(u, "apply") as apply:
            status=p.run_cycle(force=True,now=2000000000)
        self.assertEqual(status["last_result"],"CI_WAIT")
        stop.assert_not_called()
        apply.assert_not_called()

    def test_unmanaged_process_refuses_stop_and_update(self):
        self.turn_on()
        with mock.patch.object(u, "_runtime_active", return_value=True), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"b"*40}), \
             mock.patch.object(u, "ci_passed", return_value=True), \
             mock.patch.object(p.lifecycle, "request_stop",
                               side_effect=p.lifecycle.LifecycleError("unmanaged")), \
             mock.patch.object(u, "apply") as apply:
            status=p.run_cycle(force=True,now=2000000000)
        self.assertEqual(status["last_result"],"BLOCKED_RUNNING")
        self.assertEqual(status["last_error"],"RUNNING")
        apply.assert_not_called()

    def test_failure_after_stop_still_resumes_previous_chat(self):
        self.turn_on()
        commit="c"*40
        with mock.patch.object(u, "_runtime_active", side_effect=[True,False]), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":commit}), \
             mock.patch.object(u, "ci_passed", return_value=True), \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True), \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(u, "apply", side_effect=u.UpdateDenied("no fast-forward")):
            status=p.run_cycle(force=True,now=2000000000,target="runtime")
        self.assertEqual(status["last_result"],"ERROR")
        resume.assert_called_once_with(reason="RESTORE")

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
            if root.name == ".v13-runtime-source":
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
    def workflow(commit, name=u.CI_WORKFLOW, **changes):
        result = {"head_sha": commit, "name": name,
                  "path": u.CI_WORKFLOW_PATH+"@refs/heads/gpt6/v13-private-remote-bridge-20261111" if name==u.CI_WORKFLOW else ".github/workflows/test.yml",
                  "status": "completed", "conclusion": "success",
                  "head_repository": {"full_name": "RedMentos/Aii"}}
        result.update(changes)
        return result

    def fake_api(self, rows):
        return mock.patch.object(u.subprocess, "run", return_value=mock.Mock(
            returncode=0, stdout=json.dumps({"workflow_runs":rows})))

    def test_scoped_ci_all_required_workflows(self):
        commit = "b" * 40
        full = [self.workflow(commit, name) for name in u.REQUIRED_CI["runtime"]]
        with self.fake_api(full):
            self.assertTrue(u.ci_passed(commit,scope="dashboard"))
            self.assertTrue(u.ci_passed(commit,scope="runtime"))
        with self.fake_api(full[:-1]):
            self.assertTrue(u.ci_passed(commit,scope="dashboard"))
            self.assertFalse(u.ci_passed(commit,scope="runtime"))
        with self.fake_api(full[:1]):
            self.assertFalse(u.ci_passed(commit,scope="dashboard"))
            self.assertFalse(u.ci_passed(commit,scope="runtime"))

    def test_workflow_must_have_correct_commit_path_name_repo_and_success(self):
        commit = "b"*40
        full = [self.workflow(commit, name) for name in u.REQUIRED_CI["runtime"]]
        variants = [
            self.workflow(commit, u.CI_WORKFLOW),
            self.workflow("c"*40, u.CI_WORKFLOW),
            self.workflow(commit,u.CI_WORKFLOW,conclusion="failure"),
            self.workflow(commit,u.CI_WORKFLOW,path=".github/workflows/fake.yml"),
            self.workflow(commit,u.CI_WORKFLOW,head_repository={"full_name":"attacker/fork"}),
            self.workflow(commit,u.CI_WORKFLOW,status="in_progress"),
        ]
        for i,row in enumerate(variants):
            with self.subTest(i=i), self.fake_api([row, *full[1:]]):
                self.assertEqual(u.ci_passed(commit,scope="dashboard"), i==0)

    def test_no_ci_run_never_allows_auto(self):
        with self.fake_api([]):
            self.assertFalse(u.ci_passed("a"*40))
            self.assertFalse(u.ci_passed("a"*40, scope="dashboard"))


if __name__ == "__main__":
    unittest.main()
