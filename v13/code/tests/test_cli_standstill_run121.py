"""Run121: CLI ask must not hang or enqueue under persisted human standstill.

Linux model-free real subprocess/SQLite evidence. No native model, Redmi,
learning, gate promotion, or changes to the user's stop state.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import standstill


class CliStandstillRun121(unittest.TestCase):
    def ask(self, home, text):
        root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.update(PYTHONPATH=str(root), NEEDLE_TELEMETRY="0",
                   DO_NOT_TRACK="1", PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-m", "v13", "--home", str(home),
             "ask", text, "--no-observers"],
            cwd=root, env=env, capture_output=True, text=True,
            timeout=5, check=False)

    def test_persisted_pause_refuses_ask_without_queue_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            runtime = Runtime(home)
            try:
                runtime.pause()
                self.assertTrue(runtime.paused)
                before = runtime.store.queue_stats()["count"]
            finally:
                runtime.close()
            result = self.ask(home, "Kopiere exakt: must not be queued")
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, "")
            runtime = Runtime(home)
            try:
                self.assertTrue(runtime.paused)
                self.assertEqual(runtime.store.queue_stats()["count"], before)
                self.assertEqual(runtime.store.rows(
                    "SELECT text FROM messages WHERE role='assistant'"), [])
            finally:
                runtime.close()

    def test_persisted_standstill_refuses_then_human_release_allows_ask(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            runtime = Runtime(home)
            try:
                self.assertIn("STILLSTAND AN", Operator(runtime).run(":stillstand"))
                self.assertTrue(standstill.status(runtime)["on"])
            finally:
                runtime.close()
            refused = self.ask(home, "Kopiere exakt: held until release")
            self.assertEqual(refused.returncode, 2, refused.stderr)
            self.assertEqual(refused.stdout, "")
            runtime = Runtime(home)
            try:
                self.assertTrue(standstill.status(runtime)["on"])
                self.assertEqual(runtime.store.queue_stats()["count"], 0)
                self.assertIn("aufgehoben", Operator(runtime).run(":stillstand aus"))
            finally:
                runtime.close()
            allowed = self.ask(home, "Kopiere exakt: after human release")
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertEqual(allowed.stdout.strip(), "after human release")


if __name__ == "__main__":
    unittest.main()
