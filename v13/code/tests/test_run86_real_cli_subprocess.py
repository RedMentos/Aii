"""Run86 actual python -m v13 CLI process smoke without any model weights."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


APP = Path(__file__).resolve().parents[1]


class TestRun86RealCLIProcess(unittest.TestCase):
    def _run(self, home, *args, stdin=None):
        env = os.environ.copy()
        env.update(PYTHONPATH=str(APP), V13_NO_AUTOSTART="1",
                   HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                   NO_MODEL_DOWNLOADS="1")
        p = subprocess.run([sys.executable, "-m", "v13", "--home", str(home), *args],
                           cwd=APP, env=env, input=stdin, capture_output=True,
                           text=True, timeout=30)
        self.assertEqual(p.returncode, 0,
                         "CLI_FAILED stdout=" + p.stdout[-1000:] +
                         " stderr=" + p.stderr[-1000:])
        return p.stdout

    def _doctor(self, home):
        report = json.loads(self._run(home, "doctor"))
        self.assertEqual(report["learning_mode"], "RECORD_ONLY")
        self.assertFalse(report["canonical_architecture_complete"])
        self.assertEqual(report["data_integrity_errors"], [])
        self.assertTrue({"language", "body", "gist", "needle"} <=
                        set(report["missing_models"]))
        self.assertIn("OFF", report["gates"]["B3_latents"])
        self.assertEqual(report["native_capabilities"]["body_training"]["status"],
                         "UNAVAILABLE")
        self.assertEqual(report["native_capabilities"]["model_callable_tools"]["status"],
                         "OFF")
        return report

    def test_doctor_chat_plain_help_status_shutdown_across_processes(self):
        with tempfile.TemporaryDirectory(prefix="v13-run86-cli-") as td:
            home = Path(td)
            first = self._doctor(home)
            status = self._run(home, "chat", "--plain", stdin=":status\n")
            self.assertIn("V13 lokal", status)
            self.assertIn("RECORD_ONLY", status)
            self.assertIn(first["active_generation"], status)
            help_text = self._run(home, "chat", "--plain", stdin=":help\n")
            self.assertIn(":help / :status", help_text)
            self.assertIn(":verified <Frage>", help_text)
            shutdown = self._run(home, "chat", "--plain", stdin=":shutdown\n")
            self.assertIn("Beenden", shutdown)
            second = self._doctor(home)
            self.assertEqual(second["active_generation"], first["active_generation"])
            self.assertFalse(list((home / "models").rglob("*.gguf")))
            self.assertFalse(list((home / "models").rglob("*.cact")))


if __name__ == "__main__":
    unittest.main()
