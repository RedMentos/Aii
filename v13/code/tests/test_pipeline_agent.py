"""Offline CI-gated pipeline tests; no external GitHub calls or phone writes."""
import json
import os
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
        p.set_enabled(True)

    def test_auto_consent_is_idempotent_owner_only_and_shared_with_webview(self):
        from v13 import mobile_dashboard as dashboard
        self.assertFalse(p.enabled())
        for _ in range(3):
            self.assertTrue(p.set_enabled(True))
            self.assertTrue(p.enabled())
            self.assertTrue(dashboard.automatic_updates_enabled())
            self.assertEqual(p.ENABLED.read_text(), "yes\n")
            self.assertEqual(p.ENABLED.stat().st_mode & 0o077,0)
        self.assertFalse(p.set_enabled(False))
        self.assertFalse(p.ENABLED.exists())
        self.assertFalse(dashboard.automatic_updates_enabled())
        with self.assertRaises(ValueError):
            p.set_enabled("yes")
        p.ENABLED.symlink_to(self.base/"unsafe")
        with self.assertRaises(RuntimeError):
            p.set_enabled(True)

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
        scopes = [c.kwargs["scope"] for c in ci.call_args_list]
        self.assertEqual(scopes.count("runtime"), 2,
                         "runtime CI is checked before source update and before activation")
        self.assertEqual(scopes.count("dashboard"), 1)
        self.assertEqual(set(scopes), {"runtime", "dashboard"})
        self.assertEqual(apply.call_args.kwargs["expected_tip"], commit)
        self.assertEqual(dash.call_args.kwargs["expected_tip"], commit)
        self.assertTrue(p.acknowledge_refresh("ui"))
        self.assertFalse(p.refresh_requested("ui"))


    def test_pending_activation_recovery_precedes_ci_only_when_stopped_and_consented(self):
        self.turn_on()
        commit = "f" * 40
        root = p.Path.home() / ".v13-runtime-source"
        events = []

        def repo_state(_root):
            return {"status": "UP_TO_DATE", "available": commit,
                    "current": commit, "changed_files": 0}, None

        def recover():
            events.append("recover")
            return "ROLLED_BACK_INCOMPLETE"

        def ci(_commit, *, scope):
            events.append("ci")
            self.assertEqual(scope, "runtime")
            return False

        with mock.patch.object(p, "_try_repo", side_effect=repo_state), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", side_effect=[True, True]), \
             mock.patch.object(p.runtime_deploy, "recover_pending_activation", side_effect=recover) as recovery, \
             mock.patch.object(u, "ci_passed", side_effect=ci), \
             mock.patch.object(u, "apply") as apply, \
             mock.patch.object(p.runtime_deploy, "deploy") as deploy:
            state = {}
            p._do_update("runtime", root, state, runtime_busy=False,
                         tested_commits={}, manual=False)
        self.assertEqual(events, ["recover", "ci"])
        self.assertEqual(state["runtime_activation_recovery"], "ROLLED_BACK_INCOMPLETE")
        self.assertEqual(state["runtime"], "CI_WAIT")
        recovery.assert_called_once()
        apply.assert_not_called()
        deploy.assert_not_called()

        # A running chat is never interrupted just to recover an activation
        # journal. The ordinary CI check still runs and keeps the current
        # CI_WAIT behavior for a red candidate.
        events.clear()
        with mock.patch.object(p, "_try_repo", side_effect=repo_state), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", return_value=True), \
             mock.patch.object(p.runtime_deploy, "recover_pending_activation") as recovery, \
             mock.patch.object(u, "ci_passed", side_effect=ci):
            state = {}
            p._do_update("runtime", root, state, runtime_busy=True,
                         tested_commits={}, manual=False)
        self.assertEqual(events, ["ci"])
        recovery.assert_not_called()
        self.assertEqual(state["runtime"], "CI_WAIT")

    def test_pending_activation_recovery_respects_auto_off_but_manual_override(self):
        commit = "e" * 40
        root = p.Path.home() / ".v13-runtime-source"
        p.set_enabled(False)
        repo_state = lambda _root: (
            {"status": "UP_TO_DATE", "available": commit,
             "current": commit, "changed_files": 0}, None)
        with mock.patch.object(p, "_try_repo", side_effect=repo_state), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", return_value=True), \
             mock.patch.object(p.runtime_deploy, "recover_pending_activation") as recovery, \
             mock.patch.object(u, "ci_passed", return_value=True):
            with self.assertRaises(p.AutoUpdateDisabled):
                p._do_update("runtime", root, {}, runtime_busy=False,
                             tested_commits={}, manual=False)
        recovery.assert_not_called()

        with mock.patch.object(p, "_try_repo", side_effect=repo_state), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", side_effect=[True, True]), \
             mock.patch.object(p.runtime_deploy, "recover_pending_activation",
                               return_value="ROLLED_BACK_INCOMPLETE") as recovery, \
             mock.patch.object(u, "ci_passed", return_value=False):
            state = {}
            p._do_update("runtime", root, state, runtime_busy=False,
                         tested_commits={}, manual=True)
        recovery.assert_called_once()
        self.assertEqual(state["runtime"], "CI_WAIT")

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
        self.assertEqual(ci.call_count, 2)
        self.assertTrue(all(call.args == (revision,) and
                            call.kwargs == {"scope": "runtime"}
                            for call in ci.call_args_list))

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

    def test_new_ci_failure_after_graceful_stop_blocks_mutation_and_restores_chat(self):
        self.turn_on()
        commit = "c" * 40
        with mock.patch.object(u, "_runtime_active", side_effect=[True, False]), \
             mock.patch.object(u, "status", return_value={
                 "status": "UPDATE_AVAILABLE", "available": commit,
                 "current": "0" * 40, "changed_files": 4}), \
             mock.patch.object(u, "ci_passed", side_effect=[True, False]) as ci, \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True) as stop, \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(u, "apply") as apply, \
             mock.patch.object(p.runtime_deploy, "deploy") as deploy:
            report = p.run_cycle(force=True, manual=True, target="runtime")
        self.assertEqual(ci.call_count, 2, "CI must be rechecked after the graceful stop")
        stop.assert_called_once()
        resume.assert_called_once_with(reason="RESTORE")
        apply.assert_not_called()
        deploy.assert_not_called()
        self.assertEqual(report["runtime"], "CI_WAIT")
        self.assertEqual(report["last_result"], "CI_WAIT")

    def test_ci_turns_red_after_source_update_blocks_launcher_activation(self):
        self.turn_on()
        commit = "c" * 40
        with mock.patch.object(u, "_runtime_active", return_value=False), \
             mock.patch.object(u, "status", return_value={
                 "status": "UPDATE_AVAILABLE", "available": commit,
                 "current": "0" * 40, "changed_files": 4}), \
             mock.patch.object(u, "ci_passed", side_effect=[True, False]) as ci, \
             mock.patch.object(u, "apply", return_value={"status": "UPDATED"}) as apply, \
             mock.patch.object(p.runtime_deploy, "deploy") as deploy:
            report = p.run_cycle(force=True, manual=True, target="runtime")
        self.assertEqual(ci.call_count, 2, "CI must be rechecked after source fast-forward")
        apply.assert_called_once()
        deploy.assert_not_called()
        self.assertEqual(report["runtime"], "CI_WAIT")
        self.assertEqual(report["last_result"], "CI_WAIT")

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

    def test_failed_activation_recovery_keeps_stopped_chat_and_disables_auto_update(self):
        self.turn_on()
        commit = "d" * 40
        report = {"status": "UP_TO_DATE", "available": commit,
                  "current": commit, "changed_files": 0}
        with mock.patch.object(p, "_try_repo", return_value=(report, None)), \
             mock.patch.object(u, "_runtime_active", side_effect=[True, False]), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", return_value=True), \
             mock.patch.object(u, "ci_passed", return_value=True) as ci, \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True) as stop, \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(p.runtime_deploy, "recover_pending_activation", \
                               side_effect=p.runtime_deploy.RuntimeDeployError("corrupt journal")) as recovery, \
             mock.patch.object(p.runtime_deploy, "deploy") as deploy:
            result = p.run_cycle(force=True, now=2000000000, target="runtime")

        self.assertEqual(result["runtime"], "ERROR")
        self.assertEqual(result["last_result"], "ERROR")
        self.assertFalse(p.enabled(), "uncertain activation must disable future auto-updates")
        stop.assert_called_once()
        ci.assert_called_once_with(commit, scope="runtime")
        recovery.assert_called_once()
        deploy.assert_not_called()
        resume.assert_not_called()

        state = p._state_raw()
        self.assertEqual(state["runtime_activation_recovery"], "ERROR")
        self.assertEqual(state["runtime_activation_auto_update"], "DISABLED")
        self.assertEqual(state["resume_suppressed"], "ACTIVATION_RECOVERY_FAILED")


    def test_keyboard_interrupt_during_activation_recovery_keeps_chat_stopped(self):
        self.turn_on()
        commit = "e" * 40
        report = {"status": "UP_TO_DATE", "available": commit,
                  "current": commit, "changed_files": 0}
        with mock.patch.object(p, "_try_repo", return_value=(report, None)), \
             mock.patch.object(u, "_runtime_active", side_effect=[True, False]), \
             mock.patch.object(p.runtime_deploy, "needs_deploy", return_value=True), \
             mock.patch.object(u, "ci_passed", return_value=True), \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True) as stop, \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(p.runtime_deploy, "recover_pending_activation",
                               side_effect=KeyboardInterrupt), \
             mock.patch.object(p.runtime_deploy, "deploy") as deploy:
            with self.assertRaises(KeyboardInterrupt):
                p.run_cycle(force=True, now=2000000010, target="runtime")

        self.assertFalse(p.enabled())
        stop.assert_called_once()
        resume.assert_not_called()
        deploy.assert_not_called()
        state = p._state_raw()
        self.assertEqual(state["runtime_activation_recovery"], "ERROR")
        self.assertEqual(state["runtime_activation_auto_update"], "DISABLED")
        self.assertEqual(state["resume_suppressed"], "ACTIVATION_RECOVERY_FAILED")


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


    def test_runtime_rollback_disables_auto_update_and_requests_managed_chat_resume(self):
        self.turn_on()
        with mock.patch.object(u, "_runtime_active", side_effect=[True, False]), \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True) as stop, \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(p.runtime_deploy, "rollback",
                               return_value={"status": "ROLLED_BACK", "restored_commit": "d" * 40}) as rollback:
            result = p.rollback_runtime()
        self.assertEqual(result["status"], "ROLLED_BACK_RUNTIME_ONLY")
        self.assertEqual(result["dashboard"], "UNCHANGED")
        self.assertEqual(result["resume"], "REQUESTED")
        self.assertEqual(result["resume_confirmation"], "PENDING_UI_CONSUMPTION")
        self.assertFalse(result["auto_enabled"])
        self.assertFalse(p.enabled())
        stop.assert_called_once()
        resume.assert_called_once_with(reason="RESTORE")
        rollback.assert_called_once()
        self.assertEqual(p.snapshot()["runtime"], "ROLLED_BACK")
        self.assertEqual(p.snapshot()["last_result"], "ROLLED_BACK_RUNTIME_ONLY")

    def test_runtime_rollback_refuses_when_update_pipeline_is_busy(self):
        self.turn_on()
        fd = os.open(p.LOCK, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = p.rollback_runtime()
        finally:
            os.close(fd)
        self.assertEqual(result["status"], "BUSY")
        self.assertTrue(p.enabled())

    def test_runtime_rollback_failure_keeps_chat_stopped_and_auto_update_off(self):
        self.turn_on()
        with mock.patch.object(u, "_runtime_active", side_effect=[True, False]), \
             mock.patch.object(p.lifecycle, "request_stop", return_value=True), \
             mock.patch.object(p.lifecycle, "request_resume") as resume, \
             mock.patch.object(p.runtime_deploy, "rollback",
                               side_effect=p.runtime_deploy.RuntimeDeployError("simulated")):
            with self.assertRaises(p.runtime_deploy.RuntimeDeployError):
                p.rollback_runtime()
        resume.assert_not_called()
        self.assertFalse(p.enabled())
        self.assertEqual(p.snapshot()["last_result"], "ERROR")
        self.assertEqual(p.snapshot()["runtime"], "ERROR")

    def test_rollback_cli_uses_launcher_safe_runtime_rollback(self):
        with mock.patch.object(p, "rollback_runtime",
                               return_value={"status": "ROLLED_BACK_RUNTIME_ONLY"}):
            with mock.patch("sys.stdout") as output:
                code = p.main(["rollback"])
        self.assertEqual(code, 0)
        self.assertTrue(output.write.called)


class GitHubCIProofTests(unittest.TestCase):
    @staticmethod
    def workflow(commit, name=u.CI_WORKFLOW, **changes):
        workflow_id = list(u.CI_WORKFLOW_PATHS).index(name) + 1
        timestamp = "2026-11-21T00:00:00Z"
        result = {"id": 10000 + workflow_id,
                  "workflow_id": workflow_id,
                  "run_number": 1,
                  "run_attempt": 1,
                  "created_at": timestamp,
                  "updated_at": timestamp,
                  "head_sha": commit, "name": name,
                  "path": u.CI_WORKFLOW_PATHS[name]+"@refs/heads/gpt6/v13-private-remote-bridge-20261111",
                  "event": "push",
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

    def test_pr_merge_checks_never_substitute_for_the_installed_source(self):
        commit = "c"*40
        for event, allowed in (("pull_request", False), ("pull_request_target", False),
                               (None, False), ("push", True), ("workflow_dispatch", True)):
            with self.subTest(event=event), self.fake_api([
                    self.workflow(commit, name, event=event)
                    for name in u.REQUIRED_CI["runtime"]]):
                self.assertEqual(u.ci_passed(commit), allowed)

    def test_every_required_workflow_path_is_bound_not_just_its_name(self):
        commit = "c"*40
        for replaced in u.REQUIRED_CI["runtime"]:
            rows = [self.workflow(commit, name,
                        **({"path": ".github/workflows/other.yml"} if name == replaced else {}))
                    for name in u.REQUIRED_CI["runtime"]]
            with self.subTest(workflow=replaced), self.fake_api(rows):
                self.assertFalse(u.ci_passed(commit))


if __name__ == "__main__":
    unittest.main()
