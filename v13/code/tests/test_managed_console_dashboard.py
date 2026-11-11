"""Real local console recording and private opt-in error summary regression tests.

Fake V13 process only; no model download, GitHub, or phone permission.
"""
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from unittest import mock

from v13 import managed_console as mc
from v13 import mobile_dashboard as ui


class LocalConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.home = self.path / "v13"
        self.bin = self.home / "bin"
        self.bin.mkdir(parents=True)
        exe = self.bin / "v13"
        exe.write_text("#!/bin/sh\n"
                       "echo 'V13 test ready'\n"
                       "while IFS= read -r input; do\n"
                       "  echo \"received: $input\"\n"
                       "  if [ \"$input\" = ':shutdown' ]; then exit 0; fi\n"
                       "done\n")
        exe.chmod(0o700)
        self.log_root = self.path / "private" / "console-logs"
        self.console = mc.ManagedConsole(data_home=self.home, log_root=self.log_root)

    def test_captured_chat_output_survives_exit(self):
        self.assertEqual(self.console.start()["status"], "STARTED")
        self.assertEqual(self.console.start()["status"], "ALREADY_RUNNING")
        self.console.send("Hallo V13")
        self.console.send(":shutdown")
        for _ in range(100):
            if self.console.state()["exit_code"] is not None:
                break
            time.sleep(.02)
        self.assertEqual(self.console.state()["exit_code"], 0)
        text = self.console.output()
        self.assertIn("V13 test ready", text)
        self.assertIn("received: Hallo V13", text)
        self.assertIn("received: :shutdown", text)
        self.assertIn("V13 exited with code 0", text)
        self.assertEqual(stat.S_IMODE(self.console.path.stat().st_mode), 0o600)
        self.assertTrue(self.console.saved_sessions())

    def test_complete_transcript_includes_archived_session(self):
        earlier = self.log_root / "v13-session-20260101-000001-aaa.log"
        earlier.write_text("ältere Unterhaltung: 123\n")
        self.console.start()
        self.console.send("neuer Gesprächsteil")
        self.console.send(":shutdown")
        for _ in range(100):
            if self.console.state()["exit_code"] is not None:
                break
            time.sleep(.02)
        copied = self.console.transcript(all_sessions=True)
        self.assertIn("ältere Unterhaltung: 123", copied)
        self.assertIn("neuer Gesprächsteil", copied)
        self.assertGreater(len(copied), len(self.console.output(30)))

    def test_reject_multiline_and_uninstalled(self):
        with self.assertRaises(mc.ConsoleBusy):
            self.console.send("hello")
        with self.assertRaises(ValueError):
            self.console.send(":help\nrm -rf /")
        with self.assertRaises(ValueError):
            self.console.send("")
        (self.bin / "v13").unlink()
        with self.assertRaises(RuntimeError):
            self.console.start()

    def test_private_remote_excerpt_never_contains_user_text(self):
        private = self.path / "private"
        remote = private / "share-v13-log-summary.enabled"
        entry = self.log_root / "v13-session-20261111-000001-aaa.log"
        entry.write_text("[du> my private family details]\n"
                         "my private family details\n"
                         "Traceback (most recent call last):\n"
                         "RuntimeError: secret token ghp_test123456\n"
                         "[V13 exited with code 1]\n")
        with mock.patch.object(ui, "PRIVATE", private), mock.patch.object(ui, "REMOTE_LOG_FLAG", remote):
            self.assertEqual(ui.remote_console_excerpt()["state"], "USER_NOT_OPTED_IN")
            ui.set_remote_log_sharing(True)
            result = ui.remote_console_excerpt()
            self.assertEqual(result["state"], "OPTED_IN_REDACTED")
            self.assertNotIn("private family", str(result))
            self.assertNotIn("ghp_", str(result))
            self.assertIn("RuntimeError", result["lines"])
            self.assertIn("EXIT_1", result["lines"])
            ui.set_remote_log_sharing(False)
            self.assertEqual(ui.remote_console_excerpt()["state"], "USER_NOT_OPTED_IN")
        with mock.patch.object(ui, "PRIVATE", private), mock.patch.object(ui, "REMOTE_FULL_FLAG", private / "share-v13-console.enabled"):
            self.assertEqual(ui.remote_full_console()["state"], "USER_NOT_OPTED_IN")
            ui.set_remote_full_console(True)
            result = ui.remote_full_console()
            self.assertEqual(result["state"], "USER_OPTED_IN")
            self.assertIn("[LOCAL_USER_INPUT_REDACTED]", result["text"])
            self.assertNotIn("[du> my private family details]", result["text"])
            self.assertNotIn("ghp_test123456", result["text"])
            self.assertLessEqual(len(result["text"]), 6000)
            ui.set_remote_full_console(False)
            self.assertEqual(ui.remote_full_console()["state"], "USER_NOT_OPTED_IN")

    def test_private_probe_timeout_summaries_are_bounded(self):
        import json
        with mock.patch.object(ui, "DATA", self.home):
            (self.home / "exports").mkdir(parents=True)
            (self.home / "exports/native-probe.json").write_text(json.dumps({
                "status": "SMOKE_PARTIAL",
                "effective_config": {"deadline_seconds": 90, "token": "hidden"},
                "roles": {
                    "B1_DETAIL": {"ok": False, "error": "Zeitbudget erreicht", "duration_s": 54.0791},
                    "B2_GIST": {"ok": False, "error": "secret ghp_test123_very_private",
                                "duration_s": 65.835},
                    "C3_LANGUAGE": {"ok": True, "actual_output": "private chat"}
                }
            }))
            report = ui.summary()
            self.assertEqual(report["probe_deadline_seconds"], 90)
            self.assertEqual(report["roles"]["B1_DETAIL"]["error_kind"], "TIME_BUDGET")
            self.assertEqual(report["roles"]["B1_DETAIL"]["duration_s"], 54.1)
            self.assertEqual(report["roles"]["B2_GIST"]["error_kind"], "REDACTED_ERROR")
            self.assertNotIn("ghp_", str(report))
            self.assertNotIn("private chat", str(report))

    def test_dashboard_has_clickable_operator_actions_and_sliders(self):
        with mock.patch.object(ui, "PRIVATE", self.path / "private"), mock.patch.object(ui, "DATA", self.home):
            controls = mock.Mock()
            controls.state.return_value = (False, "V13-Chat", None, "none")
            controls.update_status.return_value = ("UP_TO_DATE", False)
            controls.output.return_value = ""
            controls.terminal.saved_sessions.return_value = []
            html = ui.dashboard_html("abcd", controls)
            for label in ("Chat starten", "Gehirnstatus", "Modelle testen",
                          "Nachricht senden", "Antwort-Tokens", "CPU-Threads",
                          "Alle Befehle", "V13-Code aktualisieren", "Diagnose-ZIP"):
                self.assertIn(label, html)
            self.assertIn("setInterval(refresh,1500)", html)
            self.assertIn("/t/abcd/state", html)
            self.assertIn("id=\"v13-live-output\"", html)



class BrowserButtonHTTPTests(unittest.TestCase):
    """Real HTTP submissions: privacy-browser Origin variants and CSRF."""

    def test_clicks_succeed_in_brave_and_cross_site_forms_fail(self):
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["HOME"] = home
            with subprocess.Popen(
                [sys.executable, "-m", "v13.mobile_dashboard", "ui"],
                cwd=str(Path(__file__).resolve().parents[1]), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            ) as process:
                try:
                    readable, _, _ = select.select([process.stdout], [], [], 10)
                    self.assertTrue(readable, "Dashboard did not announce local URL")
                    line = process.stdout.readline().strip()
                    self.assertTrue(line.startswith("V13 LOKALE OBERFLAECHE: "), line)
                    url = line.partition(": ")[2]
                    # New UI content and independent hidden form credential.
                    page = urlopen(url, timeout=5).read().decode("utf-8")
                    self.assertIn("V13 · Redmi", page)
                    self.assertIn("name=\"csrf\"", page)
                    tokens = re.findall(r'name="csrf" value="([0-9a-f]{48})"', page)
                    self.assertGreaterEqual(len(tokens), 15)
                    self.assertEqual(len(set(tokens)), 1)
                    destination = urljoin(url, "action")
                    def click(payload, origin=None, host=None):
                        headers = {"Content-Type": "application/x-www-form-urlencoded"}
                        if origin is not None:
                            headers["Origin"] = origin
                        if host is not None:
                            headers["Host"] = host
                        request = Request(destination,
                                          data=urlencode(payload).encode("utf-8"),
                                          headers=headers, method="POST")
                        return urlopen(request, timeout=5)

                    # Brave/privacy browsers may serialize Origin as "null".
                    with click({"csrf": tokens[0], "action": "cancel"}, origin="null") as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn("NOT_RUNNING", response.read().decode("utf-8"))
                    with click({"csrf": tokens[0], "action": "cancel"},
                               origin=url.rstrip("/").split("/t/")[0]) as response:
                        self.assertEqual(response.status, 200)
                    with urlopen(urljoin(url, "transcript"), timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn("text/plain", response.headers.get("Content-Type"))
                    with urlopen(urljoin(url, "transcript.txt"), timeout=5) as response:
                        self.assertIn("attachment", response.headers.get("Content-Disposition"))
                    with click({"csrf": tokens[0], "action": "check_update"},
                               origin="null") as response:
                        self.assertEqual(response.status, 200)
                    # Live status endpoint must include visible update feedback.
                    status = __import__("json").loads(urlopen(urljoin(url, "state")).read())
                    self.assertIn("update_result", status)
                    self.assertIn("update_busy", status)
                    # JSON actions must not reload the whole dashboard.
                    req = Request(destination,
                                  data=urlencode({"csrf": tokens[0], "action":"cancel"}).encode(),
                                  headers={"Content-Type":"application/x-www-form-urlencoded",
                                           "Accept":"application/json"}, method="POST")
                    result = __import__("json").loads(urlopen(req, timeout=5).read())
                    self.assertTrue(result["ok"])
                    # No secret: cross-site form cannot run buttons.
                    for payload in (
                        {"action": "cancel"},
                        {"csrf": "0" * 48, "action": "cancel"},
                    ):
                        with self.assertRaises(HTTPError) as cm:
                            click(payload, origin="https://malicious.example")
                        self.assertEqual(cm.exception.code, 403)
                    # DNS rebinding: still reject non-loopback Host.
                    with self.assertRaises(HTTPError) as cm:
                        click({"csrf": tokens[0], "action": "cancel"},
                              host="attacker.example:9999")
                    self.assertEqual(cm.exception.code, 403)
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
