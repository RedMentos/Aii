"""Run107: human operator source to SOURCE_EXACT + CLI, restore refusal and forget.

Software-only integration; native C3 on the exact integrated head is a separate
pinned Actions stage. Requires independently GREEN Run103/105/106 imports.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts import source_exact
from v13.__main__ import main as v13_main
from v13.operator import Operator
from v13.runtime import Runtime


QUESTION = "What is the budget for Project Elyra?"
WRONG = "What is the budget for Project Dovan?"


class OperatorSourceTwoConsumers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"

    def tearDown(self):
        self.tmp.cleanup()

    def exact(self, question=QUESTION):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = source_exact.main(["--home", str(self.home), "--query", question])
        return code, json.loads(out.getvalue())

    def budget(self, question=QUESTION):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = v13_main(["--home", str(self.home), "source-answer", question])
        return code, json.loads(out.getvalue())

    def test_human_source_exact_and_cli_share_authority_then_forget(self):
        runtime = Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            operator = Operator(runtime)
            preview = json.loads(operator.run(":source budget Elyra 615"))
            self.assertEqual(preview["status"], "CONFIRM_REQUIRED")
            self.assertFalse(preview["writes"])
            recorded = json.loads(operator.run(":source budget Elyra 615 --confirm"))
            self.assertEqual(recorded["status"], "RECORDED_VERIFIED")
            ref = recorded["source_ref"]
            memory_id = recorded["memory_id"]
        finally:
            runtime.close()

        exact_code, exact = self.exact()
        budget_code, budget = self.budget()
        self.assertEqual((exact_code, exact["status"]), (0, "FINAL"))
        self.assertEqual(exact["answer"], "Project Elyra budget: 615 Euro.")
        self.assertEqual((budget_code, budget["status"]), (0, "READY"))
        self.assertEqual(exact["source_ref"], ref)
        self.assertEqual(budget["source_ref"], ref)
        self.assertEqual(exact["memory_id"], memory_id)
        self.assertEqual(budget["memory_id"], memory_id)
        self.assertEqual(exact["native_calls"] + budget["native_calls"], 0)
        self.assertFalse(exact["model_called"])
        self.assertFalse(budget["model_called"])
        self.assertNotIn("answer", budget)

        for consumer in (self.exact, self.budget):
            with self.subTest(consumer=consumer.__name__):
                code, missing = consumer(WRONG)
                self.assertEqual(code, 0)
                self.assertEqual(missing["status"], "CLARIFY")
                self.assertEqual(missing["native_calls"], 0)
                self.assertNotIn("615", missing.get("answer", ""))

        # An interrupted offline restore is not a license to open/migrate Store.
        db = self.home / "data/db/brain.sqlite3"
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        journal = self.home / "restore_pending.json"
        journal.write_text(json.dumps({"stage": "../outside", "old": "../old",
                                       "safety_backup": "none"}), encoding="utf-8")
        for consumer in (self.exact, self.budget):
            with self.subTest(consumer=consumer.__name__):
                code, refused = consumer()
                self.assertEqual(code, 2)
                self.assertEqual(refused, {"status": "ERROR", "reason": "ValueError"})
                self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)
                self.assertTrue(journal.exists())
        journal.unlink()

        runtime = Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            operator = Operator(runtime)
            self.assertEqual(json.loads(operator.run(":verified " + QUESTION))["status"],
                             "READY")
            operator.run(":forget " + str(memory_id) + " --confirm")
            self.assertEqual(json.loads(operator.run(":verified " + QUESTION))["status"],
                             "CLARIFY")
        finally:
            runtime.close()

        for consumer in (self.exact, self.budget):
            with self.subTest(consumer=consumer.__name__):
                code, revoked = consumer()
                self.assertEqual(code, 0)
                self.assertEqual(revoked["status"], "CLARIFY")
                self.assertEqual(revoked["native_calls"], 0)
                self.assertNotIn("615", revoked.get("answer", ""))


if __name__ == "__main__":
    unittest.main()
