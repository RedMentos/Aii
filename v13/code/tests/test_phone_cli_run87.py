"""Run87: actual source-ZIP CLI entrypoint, across separate OS processes.

Linux model-free software evidence only. Does not run bootstrap, native
models, training, network tools, or claim Redmi/JEPA utility.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime


class PhoneCliRun87(unittest.TestCase):
    def test_two_separate_ask_processes_keep_exact_source_and_final_history(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "v13-home"
            expected = (
                ("Kopiere exakt: CLI first turn", "CLI first turn"),
                ("Kopiere exakt: CLI second turn", "CLI second turn"),
            )
            env = dict(os.environ)
            env.update(NEEDLE_TELEMETRY="0", DO_NOT_TRACK="1",
                       PYTHONDONTWRITEBYTECODE="1")
            # The test is executed from the extracted V13-Phone directory.
            root = Path(__file__).resolve().parents[1]
            env["PYTHONPATH"] = str(root)
            for query, answer in expected:
                result = subprocess.run(
                    [sys.executable, "-m", "v13", "--home", str(home),
                     "ask", query, "--no-observers"],
                    cwd=root, env=env, capture_output=True, text=True,
                    timeout=20, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1000:])
                self.assertEqual(result.stdout.strip(), answer)
            runtime = Runtime(home)
            try:
                rows = runtime.store.rows(
                    "SELECT event_id,text,status FROM messages "
                    "WHERE role='assistant' ORDER BY id")
                self.assertEqual(
                    [(r["text"], r["status"]) for r in rows],
                    [(answer, "FINAL") for _, answer in expected])
                self.assertEqual(len({r["event_id"] for r in rows}), 2)
                for row, (query, _) in zip(rows, expected):
                    event = runtime.store.one(
                        "SELECT packet FROM events WHERE id=?",
                        (row["event_id"],))
                    source = json.loads(event["packet"])["source_ref"]
                    self.assertEqual(runtime.store.read_source(source), query)
                self.assertEqual(runtime.store.queue_stats()["count"], 0)
                self.assertEqual(runtime.cfg["learning_mode"], "RECORD_ONLY")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
