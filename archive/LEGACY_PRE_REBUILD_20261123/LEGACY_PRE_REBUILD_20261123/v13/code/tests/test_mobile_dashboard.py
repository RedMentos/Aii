"""No-network tests of the V13 local click UI and bounded diagnostics."""
import json
from pathlib import Path
import tempfile
import time
import unittest
import zipfile

from v13 import mobile_dashboard as d
from v13.managed_console import ManagedConsole


class MobileDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.data = base / "v13"
        self.private = base / "priv"
        (self.data / "exports").mkdir(parents=True)
        (self.data / "bin").mkdir()
        self.private.mkdir(mode=0o700)
        self.old_data, self.old_private = d.DATA, d.PRIVATE
        d.DATA, d.PRIVATE = self.data, self.private
        self.addCleanup(self.restore)

    def restore(self):
        d.DATA, d.PRIVATE = self.old_data, self.old_private

    def test_summary_omits_raw_user_texts_and_errors(self):
        (self.data / "exports/native-probe.json").write_text(json.dumps({
            "status": "SMOKE_PARTIAL", "prompts": ["Private secret example"],
            "roles": {"B1_DETAIL": {"ok": False, "error": "SECRET localhost and prompts",
                                    "actual_output": "private conversation"},
                      "C3_LANGUAGE": {"ok": True, "actual_output": "private response"}},
            "access_token": "github_pat_XYZ"
        }))
        result = d.summary()
        self.assertEqual(result["native_probe"], "SMOKE_PARTIAL")
        self.assertEqual(result["roles"]["B1_DETAIL"], {
            "ok": False, "error_present": True, "error_kind": "REDACTED_ERROR"})
        self.assertEqual(result["roles"]["C3_LANGUAGE"], {"ok": True})
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertNotIn("private conversation", json.dumps(result))
        self.assertNotIn("github_pat_", json.dumps(result))

    def test_brain_evidence_is_read_only_and_no_private_text(self):
        from v13.runtime import Runtime
        runtime = Runtime(self.data)
        try:
            e = runtime.store.event(runtime.session, "SECRET Alice personal text")
            mid = runtime.store.message(runtime.session, e["event_id"], "assistant")
            runtime.store.finish_message(mid, "DEADLINE", {
                "runner":{"role":"C3_LANGUAGE","status":"DEADLINE",
                          "prompt_tokens":617,"generated_tokens":0,
                          "last_phase":"prefill"}})
            result = d.brain_evidence_snapshot()
            self.assertEqual(result["availability"], "LOCAL_SQLITE_METADATA")
            self.assertEqual(result["turn_status"], "DEADLINE")
            self.assertEqual(result["c3_prompt_tokens"], 617)
            self.assertEqual(result["c3_generated_tokens"], 0)
            self.assertEqual(result["roles"]["B1_DETAIL"]["delivery"], "NOT_ATTEMPTED")
            line = d.brain_evidence_line(result)
            self.assertIn("C3: 0 erzeugt / 617 Prompt-Tokens", line)
            self.assertNotIn("SECRET", json.dumps(result))
            self.assertNotIn("Alice", line)
        finally:
            runtime.close()

    def test_live_processes_are_distinct_from_smoke_and_never_leak_path(self):
        status = {"ai_runtime": {"native_residency": {
            "schema": "v13.phone-native-residency/1", "availability": "AVAILABLE",
            "readability": "OBSERVED", "roles": {
                "B1_DETAIL": {"processes": 1, "pss_mib": 755.2},
                "B2_GIST": {"processes": 1, "pss_mib": 690.1},
                "C2_CONTROL": {"processes": 1, "pss_mib": 96.0},
                "C3_LANGUAGE": {"processes": 1, "pss_mib": 224.1}}}}}
        rendered = d.live_residency_html(status)
        for role in ("B1 Detail", "B2 Gist", "C2 JEF", "C3 Sprache"):
            self.assertIn(role + ": 1 laufend", rendered)
        self.assertIn("755.2 MiB PSS", rendered)
        self.assertNotIn("/data/data/", rendered)
        self.assertIn("nicht messbar", d.live_residency_html({
            "ai_runtime": {"native_residency": {
                "availability": "UNAVAILABLE", "reason": "NO_VERIFIED_MODEL_SUPERVISOR"}}}))
        self.assertIn("noch nicht nachweisbar", d.live_residency_html({
            "ai_runtime": {"native_residency": {
                "availability": "AVAILABLE", "readability": "UNKNOWN_NO_GROUP_CHILDREN"}}}))

    def test_zip_local_only_with_bound_and_redaction(self):
        (self.private / "v13-ui-last.log").write_text(
            "GitHub token=github_pat_Abcdef\nEmail user@example.com\nHello.\n")
        destination = self.private / "out.zip"
        d.diagnostics_zip(destination)
        with zipfile.ZipFile(destination) as z:
            self.assertIn("summary.json", z.namelist())
            body = z.read("logs/dashboard-last-run.log").decode("utf8")
            self.assertNotIn("github_pat_", body)
            self.assertNotIn("user@example.com", body)
            self.assertIn("REVIEW BEFORE SHARING", z.read("README.txt").decode())

    def test_dashboard_contains_real_click_targets_not_shell(self):
        c = d.RuntimeControls()
        page = d.dashboard_html("f" * 48, c)
        for s in ("Nachricht senden", "Gehirnstatus", "Modelle testen",
                  "Diagnose-ZIP", "V13 beenden", "Gesamten Chat kopieren"):
            self.assertIn(s, page)
        self.assertIn('id="live-native-roles"', page)
        self.assertIn('id="brain-evidence"', page)
        self.assertIn("Laufzeitnachweis", page)
        self.assertIn("updateNativeRoles(data.native_residency)", page)
        self.assertNotIn("http://0.0.0.0", page)

    def test_launch_only_fixed_commands_reject_invalid_inputs(self):
        c = d.RuntimeControls()
        with self.assertRaises(ValueError):
            c.launch("shell")
        launcher = self.data / "bin/v13"
        launcher.write_text("#!/bin/sh\n"
                            "while IFS= read -r input; do\n"
                            "  echo \"received: $input\"\n"
                            "  [ \"$input\" != ':shutdown' ] || exit 0\n"
                            "done\n")
        launcher.chmod(0o700)
        c.terminal = ManagedConsole(data_home=self.data,
                                    log_root=self.private / "console-logs")
        try:
            c.launch("doctor")
            proc = c.terminal.process
            c.launch("probe")
            c.launch("ask", "local fixture question")
            self.assertIs(c.terminal.process, proc, "actions must reuse the recorded chat")
            self.assertEqual(proc.args, [str(launcher), "chat", "--plain"])
            c.shutdown()
            for _ in range(100):
                if c.terminal.state()["exit_code"] is not None:
                    break
                time.sleep(.02)
            self.assertEqual(c.terminal.state()["exit_code"], 0)
            output = c.terminal.output()
            for line in (":doctor", ":probe", "local fixture question", ":shutdown"):
                self.assertIn("received: " + line, output)
        finally:
            proc = c.terminal.process
            if proc is not None:
                if proc.poll() is None:
                    proc.terminate()
                proc.wait(timeout=5)
                if c.terminal.reader is not None:
                    c.terminal.reader.join(timeout=5)
                proc.stdin.close()
                proc.stdout.close()

    def test_symlink_or_missing_probe_not_followed(self):
        sensitive = self.private / "private.json"
        sensitive.write_text("SECRET")
        p = self.data / "exports/native-probe.json"
        p.symlink_to(sensitive)
        self.assertEqual(d.summary()["native_probe"], "NO_PROBE")


if __name__ == "__main__":
    unittest.main()
