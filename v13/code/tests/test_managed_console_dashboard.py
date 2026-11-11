"""Real local console recording and private opt-in error summary regression tests.

Fake V13 process only; no model download, GitHub, or phone permission.
"""
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
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

    def test_dashboard_has_clickable_operator_actions_and_sliders(self):
        with mock.patch.object(ui, "PRIVATE", self.path / "private"), mock.patch.object(ui, "DATA", self.home):
            controls = mock.Mock()
            controls.state.return_value = (False, "V13-Chat", None, "none")
            controls.update_status.return_value = ("UP_TO_DATE", False)
            controls.output.return_value = ""
            controls.terminal.saved_sessions.return_value = []
            html = ui.dashboard_html("abcd", controls)
            for label in ("V13 Chat starten", "Gehirnstatus", "Modelle testen",
                          "Nachricht senden", "Antwort-Tokens", "CPU-Threads",
                          "Alle Befehle", "Jetzt aktualisieren", "Diagnose-ZIP"):
                self.assertIn(label, html)


if __name__ == "__main__":
    unittest.main()
