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

    def test_all_recorded_console_pages_require_opt_in_and_redact_secrets(self):
        private=self.path / "private"
        entry=self.log_root / "v13-session-20261112-010001-abcd.log"
        entry.write_text("[du> personal info ghp_secret123]\n" +
                         ("V13 technical trace: tick working\n" * 160) +
                         "ERROR: token github_pat_abc123\n")
        flag=private / "share-v13-console.enabled"
        with mock.patch.object(ui,"PRIVATE",private), mock.patch.object(ui,"REMOTE_FULL_FLAG",flag):
            self.assertEqual(ui.remote_console_page(0,0)["state"],"USER_NOT_OPTED_IN")
            ui.set_remote_full_console(True)
            first=ui.remote_console_page(0,0)
            self.assertEqual(first["state"],"USER_OPTED_IN")
            self.assertGreater(first["total_pages"],1)
            self.assertLessEqual(len(first["text"].encode("utf-8")),2500)
            pages=[ui.remote_console_page(0,i)["text"] for i in range(first["total_pages"])]
            joined="".join(reversed(pages))
            self.assertIn("V13 technical trace",joined)
            self.assertNotIn("[du> personal info ghp_secret123]",joined)
            self.assertNotIn("github_pat_abc123",joined)
            self.assertIn("[LOCAL_USER_INPUT_REDACTED]",joined)
            self.assertEqual(ui.remote_console_page(0,first["total_pages"])["state"],"PAGE_NOT_AVAILABLE")
            (private / "bridge.log").write_text("POLL_ERROR: RuntimeError details\n")
            (private / "ui.log").write_text("UI startup saved\n")
            self.assertEqual(ui.remote_console_page(32,0)["kind"],"BRIDGE")
            self.assertIn("POLL_ERROR",ui.remote_console_page(32,0)["text"])
            self.assertEqual(ui.remote_console_page(33,0)["kind"],"DASHBOARD")
            self.assertIn("UI startup",ui.remote_console_page(33,0)["text"])
            self.assertEqual(ui.remote_console_page(100,0)["state"],"INVALID_SESSION")
            ui.set_remote_full_console(False)
            self.assertEqual(ui.remote_console_page(0,0)["state"],"USER_NOT_OPTED_IN")

    def test_private_diagnostics_checks_actual_background_ai_not_browser(self):
        with mock.patch.object(ui, "DATA", self.home), \
             mock.patch("v13.chat_service.call", return_value={
                 "running":True, "autostart":True, "daemon":"RUNNING",
                 "private_prompt":"My secret V13 chat"}):
            report=ui.summary()
        self.assertEqual(report["ai_runtime"]["service"],"RUNNING")
        self.assertEqual(report["ai_runtime"]["model_process"],"RUNNING")
        self.assertEqual(report["ai_runtime"]["state"],"RUNNING")
        self.assertTrue(report["ai_runtime"]["autostart"])
        self.assertNotIn("secret V13",str(report))
        with mock.patch.object(ui,"DATA",self.home), \
             mock.patch("v13.chat_service.call",
                        side_effect=ConnectionRefusedError("private secrets")):
            report=ui.summary()
        self.assertEqual(report["ai_runtime"]["service"],"OFFLINE")
        self.assertNotIn("private secrets",str(report))

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
            controls.terminal.state.return_value = {
                "running": False, "autostart": True, "daemon": "RUNNING"
            }
            html = ui.dashboard_html("abcd", controls)
            for label in ("Chat starten", "Gehirnstatus", "Modelle testen",
                          "Nachricht senden", "Antwort-Tokens", "CPU-Threads",
                          "Alle Befehle", "V13-Code aktualisieren", "Diagnose-ZIP"):
                self.assertIn(label, html)
            self.assertIn("setInterval(refresh,1500)", html)
            self.assertIn("const tokenBase = '/t/abcd'", html)
            self.assertIn("Gesamten Chat kopieren", html)
            self.assertIn("Alle Befehle", html)
            self.assertIn("data-fill=", html)
            self.assertIn("id=\"v13-live-output\"", html)



class BrowserButtonHTTPTests(unittest.TestCase):
    """Real HTTP submissions: privacy-browser Origin variants and CSRF."""

    def test_full_local_browser_flow_start_send_and_copy(self):
        """Actual HTTP UI -> local recorded chat -> transcript, no fake API success."""
        with tempfile.TemporaryDirectory() as home:
            root = Path(home)
            launcher = root / "v13" / "bin" / "v13"
            launcher.parent.mkdir(parents=True)
            launcher.write_text(
                "#!/bin/sh\n"
                "echo 'V13 fake chat started'\n"
                "while IFS= read -r text; do\n"
                "  echo \"V13 received: $text\"\n"
                "  if [ \"$text\" = ':shutdown' ]; then exit 0; fi\n"
                "done\n")
            launcher.chmod(0o700)
            env = os.environ.copy()
            env["HOME"] = home
            env["V13_UI_PORT"] = "0"
            env["V13_UI_NO_AUTO_OPEN"] = "1"
            proc = subprocess.Popen(
                [sys.executable, "-m", "v13.mobile_dashboard", "ui"],
                cwd=str(Path(__file__).resolve().parents[1]), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                ready, _, _ = select.select([proc.stdout], [], [], 10)
                self.assertTrue(ready)
                url = proc.stdout.readline().partition(": ")[2].strip()
                page = urlopen(url, timeout=5).read().decode()
                token = re.search(r'name="csrf" value="([0-9a-f]{48})"', page).group(1)
                self.assertRegex(page, r"let generation = '[0-9a-f]{24}';")
                action = urljoin(url, "action")
                def ajax(action_name, **fields):
                    args = {"csrf": token, "action": action_name, **fields}
                    request = Request(
                        action,
                        data=urlencode(args).encode("utf8"), method="POST",
                        headers={"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
                                 "Accept":"application/json"}
                    )
                    with urlopen(request, timeout=10) as response:
                        self.assertEqual(response.headers.get_content_type(), "application/json")
                        return __import__("json").loads(response.read())
                self.assertTrue(ajax("start_chat")["ok"])
                self.assertTrue(ajax("send",command=":bodyview")["ok"])
                self.assertTrue(ajax("send",command=":shutdown")["ok"])
                found = ""
                for _ in range(100):
                    found = urlopen(urljoin(url,"transcript"),timeout=4).read().decode("utf-8")
                    if "V13 received: :shutdown" in found:
                        break
                    time.sleep(.03)
                self.assertIn("V13 received: :bodyview", found)
                self.assertIn("V13 received: :shutdown", found)
                self.assertIn("[du> :bodyview]", found)
            finally:
                proc.terminate()
                proc.wait(timeout=5)

    def test_single_dashboard_per_home_and_reusable_browser_token(self):
        """Two concurrent servers are disallowed, and a later restart keeps URL auth."""
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["HOME"] = home
            env["V13_UI_PORT"] = "0"  # distinct OS ports in this isolated CI test
            command = [sys.executable, "-m", "v13.mobile_dashboard", "ui"]
            cwd = str(Path(__file__).resolve().parents[1])
            first = subprocess.Popen(command, cwd=cwd, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True)
            try:
                ready, _, _ = select.select([first.stdout], [], [], 10)
                self.assertTrue(ready)
                first_url = first.stdout.readline().partition(": ")[2].strip()
                self.assertIn("/t/", first_url)
                second = subprocess.run(command, cwd=cwd, env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        timeout=8, text=True)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn("already running", second.stderr)
                self.assertEqual(urlopen(first_url, timeout=3).status, 200)
            finally:
                first.terminate()
                first.wait(timeout=5)
            third = subprocess.Popen(command, cwd=cwd, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True)
            try:
                ready, _, _ = select.select([third.stdout], [], [], 10)
                self.assertTrue(ready)
                third_url = third.stdout.readline().partition(": ")[2].strip()
                from urllib.parse import urlsplit
                self.assertEqual(urlsplit(first_url).path, urlsplit(third_url).path)
                self.assertEqual(urlopen(third_url, timeout=3).status, 200)
            finally:
                third.terminate()
                third.wait(timeout=5)

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
                    # A valid AJAX send while no V13 is running must produce
                    # an actionable JSON error (NOT an empty body/JSON parse error).
                    req = Request(destination,
                                  data=urlencode({"csrf": tokens[0], "action":"send",
                                                 "command":":bodyview"}).encode(),
                                  headers={"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
                                           "Accept":"application/json"}, method="POST")
                    with self.assertRaises(HTTPError) as cm:
                        urlopen(req, timeout=5)
                    self.assertEqual(cm.exception.code, 400)
                    denied = __import__("json").loads(cm.exception.read())
                    self.assertFalse(denied["ok"])
                    self.assertIn("Zuerst V13 Chat starten", denied["message"])
                    # The old AJAX bug sent multipart/form-data, which must
                    # be rejected with an explanatory JSON response (415).
                    req = Request(destination, data=b"--boundary\r\n",
                                  headers={"Content-Type":"multipart/form-data; boundary=boundary",
                                           "Accept":"application/json"}, method="POST")
                    with self.assertRaises(HTTPError) as cm:
                        urlopen(req, timeout=5)
                    self.assertEqual(cm.exception.code, 415)
                    denied = __import__("json").loads(cm.exception.read())
                    self.assertIn("Formulardaten falsch", denied["message"])
                    # CSRF failures must also have a parseable JSON error.
                    req = Request(destination,
                                  data=urlencode({"csrf":"wrong", "action":"cancel"}).encode(),
                                  headers={"Content-Type":"application/x-www-form-urlencoded",
                                           "Accept":"application/json"}, method="POST")
                    with self.assertRaises(HTTPError) as cm:
                        urlopen(req, timeout=5)
                    self.assertEqual(cm.exception.code, 403)
                    self.assertIn("Sitzungsschlüssel", __import__("json").loads(cm.exception.read())["message"])
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
