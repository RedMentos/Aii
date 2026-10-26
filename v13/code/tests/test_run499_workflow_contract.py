"""Run499 source-only regression: skipped GitHub Actions stages cannot pass as zero.

Reads the exact one-shot workflow; never downloads or executes models.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
WF = ROOT / ".github" / "workflows" / "run499-heldout-native-retry.yml"

class NativeRetryWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WF.read_text(encoding="utf-8")

    def test_exact_one_shot_branch_and_serial_native_owner(self):
        s = self.source
        self.assertIn("types: [opened]", s)
        self.assertNotIn("types: [opened, synchronize]", s)
        self.assertIn("codex/run499-heldout14-native-retry-20261026", s)
        self.assertIn("v13-native-c3-run131-serialized", s)
        self.assertIn("cancel-in-progress: false", s)

    def test_all_native_dependencies_require_explicit_completed_success(self):
        s = self.source
        for upstream in ("deps", "fixture", "bootstrap", "native"):
            condition = (
                "steps." + upstream + ".outcome == 'success' && "
                "steps." + upstream + ".outputs.rc == '0'"
            )
            self.assertIn(condition, s, upstream)
        self.assertNotRegex(s, r"(?m)^\s*if: steps\.(?:deps|fixture|bootstrap|native)\.outputs\.rc == '0'\s*$")

    def test_final_enforcer_checks_all_outcomes_and_exit_files(self):
        s = self.source
        end = s.split("- name: Enforce actual native and independent receipt", 1)
        self.assertEqual(len(end), 2)
        tail = end[1]
        self.assertIn("if: always()", tail)
        for stage in ("source", "deps", "fixture", "bootstrap", "native", "audit", "safe", "privacy"):
            self.assertIn("steps." + stage + ".outcome", tail, stage)
        for stage in ("DEPS", "FIXTURE", "BOOTSTRAP", "NATIVE", "AUDIT", "SAFE", "PRIVACY"):
            self.assertIn("RUN499_" + stage + "_EXIT.txt", tail, stage)

    def test_frozen_source_and_no_promotion(self):
        s = self.source
        self.assertIn("95679f85c51a7265997c66f1e444be6679f6564b", s)
        self.assertIn("543982e6c03c548eab87470732be279fbba53ac1", s)
        self.assertIn("f4d2d8d5e66c49c508e376ebafce2146e5a2715b", s)
        self.assertIn("7af05962af41d0bc3f7dd18ef01d4eba55eabf99", s)
        self.assertIn("RUN496_PILOT_RESULT.json", s)
        self.assertIn("'UTILITY_FAIL'", s)
        self.assertIn("canonical_gate_pass", s)
        self.assertIn("if: always()", s)
        self.assertIn("RUN499_SHA256SUMS.txt", s)
        self.assertIn("run499-heldout10-safe-no-model-", s)
        self.assertNotIn("force-push", s)

if __name__ == "__main__":
    unittest.main()
