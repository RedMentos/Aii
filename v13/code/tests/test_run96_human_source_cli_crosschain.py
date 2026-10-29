"""Run96: actual human operator -> separate-process offline CLI -> revocation E2E."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v13.common import APP
from v13.operator import Operator
from v13.runtime import Runtime


QUESTION = "What is the budget for Project Elyra?"


class HumanSourceCliCrosschain(unittest.TestCase):
    def cli(self, home, question, *flags):
        process = subprocess.run(
            [sys.executable, "-m", "v13", "--home", str(home), "source-answer",
             question, *flags],
            cwd=APP, capture_output=True, text=True, timeout=45, check=False)
        self.assertTrue(process.stdout.strip(), process.stderr)
        return process.returncode, json.loads(process.stdout.strip())

    def test_real_human_source_to_separate_cli_then_forget(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            runtime = Runtime(home)
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                op = Operator(runtime)
                preview = json.loads(op.run(":source budget Elyra 615"))
                self.assertEqual(preview["status"], "CONFIRM_REQUIRED")
                self.assertEqual(runtime.store.one(
                    "SELECT count(*) AS n FROM memories WHERE active=1")["n"], 0)
                recorded = json.loads(op.run(":source budget Elyra 615 --confirm"))
                self.assertEqual(recorded["status"], "RECORDED_VERIFIED")
                self.assertEqual(recorded["native_calls"], 0)
                memory_id, source_ref, session = (
                    recorded["memory_id"], recorded["source_ref"], runtime.session)
            finally:
                runtime.close()

            code, ready = self.cli(home, QUESTION)
            self.assertEqual(code, 0)
            self.assertEqual(ready["status"], "READY")
            self.assertEqual(ready["memory_id"], memory_id)
            self.assertEqual(ready["source_ref"], source_ref)
            self.assertEqual(ready["native_calls"], 0)
            self.assertFalse(ready["model_called"])
            self.assertNotIn("answer", ready)

            wrong_code, wrong = self.cli(
                home, "What is the budget for Project Dovan?", "--native")
            outside_code, outside = self.cli(
                home, "Who leads Project Elyra?", "--native")
            self.assertEqual((wrong_code, wrong["status"], wrong["native_calls"]),
                             (0, "CLARIFY", 0))
            self.assertEqual((outside_code, outside["status"], outside["native_calls"]),
                             (0, "NOT_APPLICABLE", 0))
            # CLARIFY deliberately returns a question, not a sourced budget.
            self.assertTrue(wrong.get("answer", "").startswith(
                "I don\'t have a verified budget for Project"))
            self.assertNotIn("615 Euro", wrong.get("answer", ""))
            self.assertEqual(outside.get("answer", ""), "")

            # Even with an authorized source, native must not run when C3 is absent.
            native_code, absent = self.cli(home, QUESTION, "--native")
            self.assertEqual(native_code, 2)
            self.assertEqual(absent["status"], "C3_MODEL_NOT_PINNED")
            self.assertEqual(absent["native_calls"], 0)
            self.assertNotIn("answer", absent)

            runtime = Runtime(home)
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                self.assertEqual(runtime.session, session)
                op = Operator(runtime)
                pre = json.loads(op.run(":verified " + QUESTION))
                self.assertEqual(pre["status"], "READY")
                self.assertEqual(pre["memory_id"], memory_id)
                locked_code, locked = self.cli(home, QUESTION, "--native")
                self.assertEqual(locked_code, 2)
                self.assertEqual(locked["status"], "ERROR")
                self.assertFalse(locked.get("answer"))
                op.run(":forget " + memory_id + " --confirm")
                post = json.loads(op.run(":verified " + QUESTION))
                self.assertEqual(post["status"], "CLARIFY")
                self.assertEqual(post["native_calls"], 0)
            finally:
                runtime.close()

            revoked_code, revoked = self.cli(home, QUESTION, "--native")
            self.assertEqual(revoked_code, 0)
            self.assertEqual(revoked["status"], "CLARIFY")
            self.assertEqual(revoked["native_calls"], 0)
            self.assertTrue(revoked.get("answer", "").startswith(
                "I don\'t have a verified budget for Project"))
            self.assertNotIn("615 Euro", revoked.get("answer", ""))


if __name__ == "__main__":
    unittest.main()
