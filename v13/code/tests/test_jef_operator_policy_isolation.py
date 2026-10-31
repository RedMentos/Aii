"""Independent JEF operator no-background/no-persistent-policy regression tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import cohort
from v13.sleep import SleepRuntime


class JefOperatorPolicyIsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        row = cohort()[0]
        self.input_file = self.root / "input.json"
        self.input_file.write_text(json.dumps({
            "project": row["id"],
            "domain": row["domain"],
            "policy_source": row["b2_source"],
            "sheet_source": row["b1_source"],
            "current": row["current"],
        }), encoding="utf-8")
        self.home = self.root / "home"

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self):
        runtime = cli.Runtime(self.home)
        try:
            return runtime.store.state("SLEEP_POLICY", None)
        finally:
            runtime.close()

    def test_existing_sleep_policy_and_version_survive_both_diagnostics(self):
        runtime = cli.Runtime(self.home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "on")
            runtime.sleep.cycle.set_policy("tick_seconds", "7")
            before = runtime.store.state("SLEEP_POLICY", None)
            self.assertTrue(before[0]["enabled"])
            self.assertEqual(before[0]["tick_seconds"], 7.)
        finally:
            runtime.close()

        for mode in ("synthetic_exact", "synthetic_wrong"):
            with self.subTest(mode=mode):
                result = cli.run(
                    self.home, self.input_file, mode,
                    operator_opt_in=True, callback_opt_in=True)
                self.assertEqual(result["status"], "SHADOW_DRAFT_PREFLIGHT_READY")
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(result["learning_authority"], 0)
                self.assertFalse(result["output_committed"])

    def test_sleep_tick_never_runs_in_diagnostic_coordinator(self):
        calls = []
        with patch.object(SleepRuntime, "tick", autospec=True,
                          side_effect=lambda self: calls.append(True)):
            for mode in ("synthetic_exact", "synthetic_wrong"):
                result = cli.run(
                    self.home, self.input_file, mode,
                    operator_opt_in=True, callback_opt_in=True)
                self.assertEqual(result["status"], "SHADOW_DRAFT_PREFLIGHT_READY")
        self.assertEqual(calls, [])

    def test_preexisting_pending_turn_is_not_processed(self):
        runtime = cli.Runtime(self.home)
        try:
            pending = runtime.store.accept_turn(
                runtime.session, "Pending real user request",
                runtime.cfg["queue_count"], runtime.cfg["queue_bytes"],
                runtime.cfg["input_bytes"])
            eid = pending["event_id"]
        finally:
            runtime.close()
        result = cli.run(
            self.home, self.input_file, "synthetic_exact",
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "SHADOW_DRAFT_PREFLIGHT_READY")
        runtime = cli.Runtime(self.home)
        try:
            rows = runtime.store.pending_turns()
            self.assertIn(eid, [row["event"] ["event_id"] for row in rows])
            self.assertEqual(runtime.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE event_id=? "
                "AND role='assistant'", (eid,))["n"], 0)
        finally:
            runtime.close()

    def test_inert_worker_terminates_and_store_closes(self):
        runtime = cli.Runtime(self.home)
        self.assertTrue(runtime.worker.is_alive())
        runtime.close()
        self.assertFalse(runtime.worker.is_alive())
        self.assertTrue(runtime.closed)


if __name__ == "__main__":
    unittest.main()
