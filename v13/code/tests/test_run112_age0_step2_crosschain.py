"""Run112 crosschain: source-bound Age0 CLI and fresh STEP2 fixture generator.

Software-only; does not run models or promote STEP2/B3/JEPA/age.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run109_step2_fresh_fixtures as fresh
from scripts import step2_z2_timescale as z2
from scripts import source_exact
from v13.__main__ import main as v13_main
from v13.operator import Operator
from v13.runtime import Runtime

QUESTION = "What is the budget for Project Elyra?"


class Age0Step2Crosschain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"

    def tearDown(self):
        self.tmp.cleanup()

    def _call(self, fn, args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exit_code = fn(args)
        return exit_code, json.loads(stream.getvalue())

    def _exact(self):
        return self._call(source_exact.main, ["--home", str(self.home), "--query", QUESTION])

    def _budget(self):
        return self._call(v13_main, ["--home", str(self.home), "source-answer", QUESTION])

    def test_record_exact_cli_revoke_does_not_mutate_frozen_step2(self):
        fixture_sha = fresh.inspect()["fixture_sha256"]
        frozen_z2_sha = fresh.canonical_sha256(z2.FIXTURES)
        self.assertEqual(fresh.inspect()["status"], "FRESH_FIXTURES_READY_SOFTWARE_ONLY")
        self.assertFalse(fresh.inspect()["canonical_gate_pass"])
        self.assertEqual(fresh.inspect()["native_calls"], 0)
        runtime = Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            operator = Operator(runtime)
            preview = json.loads(operator.run(":source budget Elyra 615"))
            self.assertEqual(preview["status"], "CONFIRM_REQUIRED")
            self.assertFalse(preview["writes"])
            recorded = json.loads(operator.run(":source budget Elyra 615 --confirm"))
            self.assertEqual(recorded["status"], "RECORDED_VERIFIED")
            source_ref = recorded["source_ref"]
            memory_id = recorded["memory_id"]
        finally:
            runtime.close()
        exact_code, exact = self._exact()
        budget_code, budget = self._budget()
        self.assertEqual((exact_code, exact["status"]), (0, "FINAL"))
        self.assertEqual((budget_code, budget["status"]), (0, "READY"))
        self.assertEqual(exact["answer"], "Project Elyra budget: 615 Euro.")
        self.assertEqual(exact["source_ref"], source_ref)
        self.assertEqual(budget["source_ref"], source_ref)
        self.assertEqual(exact["memory_id"], memory_id)
        self.assertEqual(budget["memory_id"], memory_id)
        self.assertEqual(exact["native_calls"] + budget["native_calls"], 0)
        self.assertFalse(exact["model_called"] or budget["model_called"])
        self.assertEqual(fresh.inspect()["fixture_sha256"], fixture_sha)
        self.assertEqual(fresh.canonical_sha256(z2.FIXTURES), frozen_z2_sha)

        # Refuse a malformed interrupted restore before either CLI touches Store.
        db = self.home / "data/db/brain.sqlite3"
        db_before = hashlib.sha256(db.read_bytes()).hexdigest()
        journal = self.home / "restore_pending.json"
        journal.write_text(json.dumps({"stage": "../outside", "old": "../old",
                                       "safety_backup": "none"}), encoding="utf-8")
        for fn in (self._exact, self._budget):
            with self.subTest(consumer=fn.__name__):
                code, refusal = fn()
                self.assertEqual(code, 2)
                self.assertEqual(refusal, {"status": "ERROR", "reason": "ValueError"})
                self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), db_before)
        journal.unlink()
        runtime = Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            operator = Operator(runtime)
            self.assertEqual(json.loads(operator.run(":verified " + QUESTION))["status"], "READY")
            operator.run(":forget " + str(memory_id) + " --confirm")
        finally:
            runtime.close()
        for fn in (self._exact, self._budget):
            with self.subTest(consumer=fn.__name__):
                code, revoked = fn()
                self.assertEqual(code, 0)
                self.assertEqual(revoked["status"], "CLARIFY")
                self.assertEqual(revoked["native_calls"], 0)
                self.assertNotIn("615", revoked.get("answer", ""))
        after = fresh.inspect()
        self.assertEqual(after["fixture_sha256"], fixture_sha)
        self.assertEqual(fresh.canonical_sha256(z2.FIXTURES), frozen_z2_sha)
        self.assertEqual(after["step2_status"], "UTILITY_FAIL")
        self.assertFalse(after["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
