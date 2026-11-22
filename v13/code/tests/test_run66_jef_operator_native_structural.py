"""Run66 native operator orchestration guards; synthetic software tests only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run66_jef_operator_native_structural as r66


class Run66JefOperatorNativeSoftwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_allowlist_never_emits_raw_sources(self):
        payload = {
            "status": "NATIVE_BINDING_RED",
            "input_sha256": "a" * 64,
            "policy_source": "PRIVATE_POLICY_DO_NOT_PUBLISH",
            "sheet_source": "PRIVATE_SHEET_DO_NOT_PUBLISH",
            "current": "PRIVATE_USER_DO_NOT_PUBLISH",
            "native_output": "PRIVATE_MODEL_OUTPUT_DO_NOT_PUBLISH",
            "native_output_sha256": "b" * 64,
        }
        safe = r66._safe_fields(payload)
        self.assertEqual(safe["status"], "NATIVE_BINDING_RED")
        self.assertEqual(safe["native_output_sha256"], "b" * 64)
        for key in ("policy_source", "sheet_source", "current", "native_output"):
            self.assertNotIn(key, safe)
        self.assertNotIn("PRIVATE", json.dumps(safe))

    def test_existing_output_or_input_paths_refused_before_store(self):
        home = self.root / "home"
        out = self.root / "out.json"
        input_root = self.root / "inputs"
        out.write_text("KEEP")
        with self.assertRaisesRegex(FileExistsError, "FRESH_OUTPUT_PATHS"):
            r66.run(home, out, input_root)
        self.assertEqual(out.read_text(), "KEEP")
        self.assertFalse(home.exists())
        out.unlink()
        input_root.mkdir()
        with self.assertRaisesRegex(FileExistsError, "FRESH_OUTPUT_PATHS"):
            r66.run(home, out, input_root)
        self.assertFalse(out.exists())
        self.assertFalse(home.exists())

    def test_mock_native_red_is_preserved_without_false_proof(self):
        home = self.root / "home"
        out = self.root / "out.json"
        input_root = self.root / "inputs"
        with patch.object(r66.cli, "run", return_value={
            "status": "NATIVE_BINDING_RED",
            "native_model_called": False,
            "native_process_reaped": None,
            "native_final": None,
            "delivery_authority": 0,
            "output_committed": False,
            "tool_dispatches": 0,
            "learning_authority": 0,
            "age0": "RECORD_ONLY",
        }) as fake:
            with self.assertRaisesRegex(RuntimeError, "STRUCTURAL_RED"):
                r66.run(home, out, input_root)
        report = json.loads(out.read_text())
        self.assertEqual(report["status"], "STRUCTURAL_SHADOW_RED")
        self.assertEqual(len(report["cases"]), 3)
        self.assertEqual(fake.call_count, 3)
        self.assertTrue(report["restart_policy_unchanged"])
        self.assertTrue(report["restart_drafts_zero"])
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(report["jepa_weight"], 0)
        self.assertEqual(report["age0"], "RECORD_ONLY")
        self.assertNotIn("policy_source", out.read_text())
        self.assertNotIn("sheet_source", out.read_text())

    def test_policy_snapshot_has_no_background_write(self):
        home = self.root / "home"
        runtime = r66.cli.Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "on")
            before = r66._db(home)["sleep_policy"]
            self.assertIsNotNone(before)
            self.assertEqual(r66._db(home)["assistant_committed"], 0)
        finally:
            runtime.close()
        self.assertEqual(r66._db(home)["sleep_policy"], before)


if __name__ == "__main__":
    unittest.main()
