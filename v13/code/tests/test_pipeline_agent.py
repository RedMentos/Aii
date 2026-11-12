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
        runtime_source = mock.patch.object(p.runtime_deploy, "prepare_source", return_value={"status":"READY"})
        dashboard_source = mock.patch.object(u, "ensure_sparse_phone_modules", return_value={"status":"ALREADY_PRESENT"})
        for helper in (runtime_needs,runtime_act,runtime_source,dashboard_source):
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

    def test_pending_13_from_old_checkout_does_not_reappear_after_real_update(self):
        # Regression: dashboard 'Änderungen prüfen' formerly read ~/V13-Phone
        # instead of the two actual CI-gated update roots.
        expected = {".v13-runtime-source", ".v13-agent-source"}
        seen = []
        def source_state(root, *, fetch=True):
            seen.append(root.name)
            self.assertIn(root.name, expected, "old ~/V13-Phone path must not be read")
            return {"status": "UP_TO_DATE", "available": "a"*40,
                    "current": "a"*40, "changed_files": 0}
        with mock.patch.object(u, "status", side_effect=source_state):
            r = p.pending_updates(fetch=True)
        self.assertTrue(r["verified_current"])
        self.assertEqual(r["pending_files"], 0)
        self.assertEqual(set(seen), expected)
        self.assertEqual(r["status"], "UP_TO_DATE")

    def test_pending_updates_counts_real_files_and_rechecks_after_apply(self):
        roots = {".v13-runtime-source", ".v13-agent-source"}
        state = {"outdated": True}
        def source_state(root, *, fetch=True):
            self.assertIn(root.name, roots)
            if state["outdated"] and root.name == ".v13-runtime-source":
                return {"status": "UPDATE_AVAILABLE", "current": "0"*40,
                        "available": "a"*40, "changed_files": 13}
            return {"status": "UP_TO_DATE", "current": "a"*40,
                    "available": "a"*40, "changed_files": 0}
        with mock.patch.object(u, "status", side_effect=source_state):
            first = p.pending_updates(fetch=True)
            self.assertEqual(first["pending_files"], 13)
            self.assertFalse(first["verified_current"])
            state["outdated"] = False
            after = p.pending_updates(fetch=True)
        self.assertEqual(after["pending_files"], 0)
        self.assertTrue(after["verified_current"])

    def test_zero_git_changes_but_old_launcher_is_not_falsely_current(self):
        with mock.patch.object(u, "status", return_value={
                "status": "UP_TO_DATE", "available": "a"*40,
                "current": "a"*40, "changed_files": 0}), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", return_value=True):
            pending = p.pending_updates(fetch=True)
        self.assertEqual(pending["pending_files"], 0)
        self.assertTrue(pending["runtime_activation_pending"])
        self.assertEqual(pending["runtime"], "ACTIVATION_PENDING")
        self.assertFalse(pending["verified_current"])

    def test_missing_runtime_root_never_reports_fake_zero_verified(self):
        home = p.Path.home()
        (home/".v13-runtime-source").rmdir()
        with mock.patch.object(u, "status", return_value={
                "status": "UP_TO_DATE", "changed_files": 0,
                "current": "a"*40, "available": "a"*40}):
            check = p.pending_updates(fetch=True)
        self.assertEqual(check["runtime"], "NOT_INSTALLED")
        self.assertFalse(check["verified_current"])

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

    def test_dashboard_only_check_preserves_last_runtime_result(self):
        p.STATE.write_text(json.dumps({"runtime":"UPDATED", "dashboard":"CI_WAIT"}))
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={"status":"UP_TO_DATE"}):
            report = p.run_cycle(force=True, manual=True, target="dashboard")
        self.assertEqual(report["runtime"], "UPDATED")
        self.assertEqual(report["dashboard"], "UP_TO_DATE")
        self.assertFalse(report["auto_enabled"], "manual update must preserve explicit auto OFF")

    def test_current_dashboard_checkout_still_repairs_sparse_dependencies(self):
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={"status":"UP_TO_DATE"}), \
             mock.patch.object(u, "ensure_sparse_phone_modules") as migrate:
            report = p.run_cycle(force=True, manual=True, target="dashboard")
        migrate.assert_called_once_with(p.Path.home() / ".v13-agent-source")
        self.assertEqual(report["dashboard"], "UP_TO_DATE")

    def test_runtime_bootstrap_failure_does_not_block_dashboard_repair(self):
        with mock.patch.object(p.runtime_deploy, "prepare_source",
                               side_effect=p.runtime_deploy.RuntimeDeployError("offline")), \
             mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"b"*40}), \
             mock.patch.object(u, "ci_passed", return_value=True), \
             mock.patch.object(u, "apply_dashboard", return_value={"status":"UPDATED"}) as update:
            report = p.run_cycle(force=True, manual=True)
        update.assert_called_once()
        self.assertEqual(report["runtime"], "ERROR")
        self.assertEqual(report["dashboard"], "UPDATED")
        self.assertEqual(report["last_result"], "PARTIAL")
        self.assertTrue(p.refresh_requested("bridge"))

    def test_deploy_failure_is_terminal_and_restores_stopped_chat(self):
        with mock.patch.object(u, "_runtime_active", side_effect=[True, False]), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"b"*40}), \
             mock.patch.object(u, "ci_passed", return_value=True), \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True), \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(u, "apply", return_value={"status":"UPDATED"}), \
             mock.patch.object(p.runtime_deploy, "deploy",
                               side_effect=p.runtime_deploy.RuntimeDeployError("selftest failed")):
            report = p.run_cycle(force=True, manual=True, target="runtime")
        self.assertEqual(report["runtime"], "ERROR")
        self.assertEqual(report["last_result"], "ERROR")
        resume.assert_called_once_with(reason="RESTORE")

    def test_incomplete_running_runtime_does_not_strand_checking(self):
        with mock.patch.object(u, "_runtime_active", return_value=True), \
             mock.patch.object(u, "status", return_value={
                 "status":"UP_TO_DATE", "available":"c"*40}), \
             mock.patch.object(p.runtime_deploy, "needs_deploy",
                               side_effect=p.runtime_deploy.RuntimeDeployError("missing Canon")), \
             mock.patch.object(p.lifecycle, "request_stop") as stop:
            report = p.run_cycle(force=True, manual=True)
        self.assertEqual(report["runtime"], "ERROR")
        self.assertEqual(report["dashboard"], "UP_TO_DATE")
        self.assertEqual(report["last_result"], "PARTIAL")
        stop.assert_not_called()

    def test_unexpected_error_is_recorded_before_propagation(self):
        with mock.patch.object(u, "_runtime_active", side_effect=ImportError("private import path")):
            with self.assertRaises(ImportError):
                p.run_cycle(force=True, manual=True)
        report = p.snapshot()
        self.assertEqual(report["last_result"], "ERROR")
        self.assertEqual(report["last_error"], "UPDATE")
        self.assertNotIn("private import path", str(report))

    def test_one_ci_lookup_failure_does_not_block_independent_dashboard(self):
        def ci(commit, *, scope):
            if scope == "runtime":
                raise u.UpdateDenied("temporary GitHub error")
            return True
        with mock.patch.object(u, "_runtime_active", side_effect=[True, False]), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"b"*40}), \
             mock.patch.object(u, "ci_passed", side_effect=ci), \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True), \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(u, "apply") as runtime, \
             mock.patch.object(u, "apply_dashboard", return_value={"status":"UPDATED"}) as dashboard:
            report = p.run_cycle(force=True, manual=True)
        runtime.assert_not_called()
        dashboard.assert_called_once()
        resume.assert_called_once_with(reason="UPDATED")
        self.assertEqual(report["runtime"], "ERROR")
        self.assertEqual(report["dashboard"], "UPDATED")
        self.assertEqual(report["last_result"], "PARTIAL")

    def test_dashboard_success_does_not_claim_complete_runtime_ci_wait(self):
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={
                 "status":"UPDATE_AVAILABLE", "available":"b"*40}), \
             mock.patch.object(u, "ci_passed", side_effect=lambda sha, scope: scope == "dashboard"), \
             mock.patch.object(u, "apply") as runtime, \
             mock.patch.object(u, "apply_dashboard", return_value={"status":"UPDATED"}):
            report = p.run_cycle(force=True, manual=True)
        runtime.assert_not_called()
        self.assertEqual(report["runtime"], "CI_WAIT")
        self.assertEqual(report["dashboard"], "UPDATED")
        self.assertEqual(report["last_result"], "PARTIAL")


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
