"""Run501 one-shot Xenia/Yarrow native workflow source-only contract tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
WF = ROOT / ".github" / "workflows" / "run501-xenia-yarrow-native.yml"

class Run501WorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WF.read_text(encoding="utf-8")

    def test_exact_stage_and_serial_one_shot(self):
        s = self.source
        self.assertIn("types: [opened]", s)
        self.assertIn("codex/run501-xenia-yarrow-native-20261026", s)
        self.assertIn("v13-native-c3-run131-serialized", s)
        self.assertIn("cancel-in-progress: false", s)
        self.assertIn("--stage-id C_s31_p01", s)
        self.assertIn("('Xenia','Yarrow')", s)
        self.assertNotIn("--stage-id C_s31_p00", s)

    def test_no_skipped_upstream_stage_can_pass(self):
        s = self.source
        for stage in ("deps", "fixture", "bootstrap", "native"):
            self.assertIn(
                "steps." + stage + ".outcome == 'success' && steps." +
                stage + ".outputs.rc == '0'", s)
        tail = s.split("- name: Enforce actual native and independent receipt", 1)[-1]
        for stage in ("source", "deps", "fixture", "bootstrap", "native", "audit", "safe", "privacy"):
            self.assertIn("steps." + stage + ".outcome", tail)
        for stage in ("DEPS", "FIXTURE", "BOOTSTRAP", "NATIVE", "AUDIT", "SAFE", "PRIVACY"):
            self.assertIn("RUN501_" + stage + "_EXIT.txt", tail)

    def test_frozen_source_and_no_promotion(self):
        s = self.source
        self.assertIn("504a4a8492bdb383869b164b82c05d13e00f6823", s)
        self.assertIn("543982e6c03c548eab87470732be279fbba53ac1", s)
        self.assertIn("f4d2d8d5e66c49c508e376ebafce2146e5a2715b", s)
        self.assertIn("RUN500_STAGE_MAP.json", s)
        self.assertIn("RUN500_STAGE_RESULT.json", s)
        self.assertIn("RUN501_SHA256SUMS.txt", s)
        self.assertIn("canonical_gate_pass", s)
        self.assertIn("'UTILITY_FAIL'", s)
        self.assertIn("run501-heldout10-safe-no-model-", s)
        self.assertIn("if: always()", s)

if __name__ == "__main__":
    unittest.main()
