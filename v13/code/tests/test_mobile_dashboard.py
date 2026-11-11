"""No-network tests of the V13 local click UI and bounded diagnostics."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from v13 import mobile_dashboard as d


class MobileDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.data = base / "v13"
        self.private = base / "priv"
        (self.data / "exports").mkdir(parents=True)
        (self.data / "bin").mkdir()
        self.private.mkdir()
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
        self.assertEqual(result["roles"]["B1_DETAIL"], {"ok": False, "error_present": True})
        self.assertEqual(result["roles"]["C3_LANGUAGE"], {"ok": True})
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertNotIn("private conversation", json.dumps(result))
        self.assertNotIn("github_pat_", json.dumps(result))

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
                  "Diagnose-ZIP", "V13 stoppen", "Ausgabe aktualisieren"):
            self.assertIn(s, page)
        self.assertNotIn("http://0.0.0.0", page)

    def test_launch_only_fixed_commands_reject_invalid_inputs(self):
        c = d.RuntimeControls()
        with self.assertRaises(ValueError):
            c.launch("shell")
        launcher = self.data / "bin/v13"
        launcher.write_text("#!/bin/sh\necho TEST\n")
        launcher.chmod(0o700)
        with mock.patch.object(d.subprocess, "Popen") as p:
            proc = p.return_value
            proc.poll.return_value = None
            c.launch("doctor")
            self.assertEqual(p.call_args.args[0], [str(launcher), "doctor"])
            self.assertNotIn("shell", p.call_args.kwargs)
        with self.assertRaises(RuntimeError):
            c.launch("probe")

    def test_symlink_or_missing_probe_not_followed(self):
        sensitive = self.private / "private.json"
        sensitive.write_text("SECRET")
        p = self.data / "exports/native-probe.json"
        p.symlink_to(sensitive)
        self.assertEqual(d.summary()["native_probe"], "NO_PROBE")


if __name__ == "__main__":
    unittest.main()
