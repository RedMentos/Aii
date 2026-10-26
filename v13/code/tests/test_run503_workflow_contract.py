"""Run503 one-shot serialized three-stage native workflow source-only contract."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
WF = ROOT / ".github" / "workflows" / "run503-batch3-native.yml"

class Run503WorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WF.read_text(encoding="utf-8")

    def test_one_shot_serial_batch_and_exact_frozen_scope(self):
        s = self.source
        self.assertIn("types: [opened]", s)
        self.assertIn("codex/run503-batch3-native-20261026", s)
        self.assertIn("v13-native-c3-run131-serialized", s)
        self.assertIn("cancel-in-progress: false", s)
        self.assertIn("scripts/run502_step2_batch.py", s)
        self.assertIn("--execute", s)
        for stage in ("C_s31_p02","C_s31_p03","C_s31_p04"):
            self.assertIn(stage, s)
        self.assertNotIn("--stage-id C_s31_p00", s)
        self.assertNotIn("--stage-id C_s31_p01", s)

    def test_fail_closed_steps_and_raw_evidence(self):
        s = self.source
        for stage in ("deps", "fixture", "bootstrap", "native"):
            self.assertIn("steps." + stage + ".outcome == 'success' && steps." +
                          stage + ".outputs.rc == '0'", s)
        tail = s.split("- name: Enforce actual native and independent receipt", 1)[-1]
        for stage in ("source", "deps", "fixture", "bootstrap", "native", "audit", "safe", "privacy"):
            self.assertIn("steps." + stage + ".outcome", tail)
        for stage in ("DEPS", "FIXTURE", "BOOTSTRAP", "NATIVE", "AUDIT", "SAFE", "PRIVACY"):
            self.assertIn("RUN503_" + stage + "_EXIT.txt", tail)
        self.assertIn("RUN503_SHA256SUMS.txt", s)
        self.assertIn("RUN502_BATCH_PROGRESS.jsonl", s)

    def test_pinned_sources_and_no_gate_promotion(self):
        s = self.source
        for blob in ("5c01768ccedbe63cb3c2eebde5a75347e3a67abd",
                     "504a4a8492bdb383869b164b82c05d13e00f6823",
                     "f4d2d8d5e66c49c508e376ebafce2146e5a2715b",
                     "543982e6c03c548eab87470732be279fbba53ac1"):
            self.assertIn(blob, s)
        self.assertIn("rows_verified", s)
        self.assertIn("canonical_gate_pass", s)
        self.assertIn("'UTILITY_FAIL'", s)
        self.assertIn("run503-heldout10-safe-no-model-", s)
        self.assertIn("if: always()", s)

if __name__ == "__main__":
    unittest.main()
