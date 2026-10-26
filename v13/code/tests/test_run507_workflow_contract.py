"""Run507 source-only workflow contract: disjoint 42-row A_s31 native attempt."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "run507-future001-native.yml"


class Run507WorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_one_shot_serial_frozen_future001(self):
        s = self.source
        self.assertIn("types: [opened]", s)
        self.assertIn("codex/run507-future001-native-20261026", s)
        self.assertIn("v13-native-c3-run131-serialized", s)
        self.assertIn("cancel-in-progress: false", s)
        self.assertIn("scripts/run505_future001_batch.py", s)
        self.assertIn("scripts/run504_remaining980_schedule.py", s)
        self.assertIn("--execute", s)
        for stage in ("A_s31_p00", "A_s31_p01", "A_s31_p02"):
            self.assertIn(stage, s)
        self.assertNotIn("--stage-id C_s31_p00", s)
        self.assertNotIn("--stage-id C_s31_p01", s)
        self.assertNotIn("--stage-id C_s31_p02", s)

    def test_exact_sha_pins_and_fail_closed_receipt(self):
        s = self.source
        for blob in ("8694c566247a6709d80a504ad172c608889775d6",
                     "5f447908ec6197760d55c347ffb949ae42ad1ed8",
                     "504a4a8492bdb383869b164b82c05d13e00f6823",
                     "f4d2d8d5e66c49c508e376ebafce2146e5a2715b"):
            self.assertIn(blob, s)
        for stage in ("deps", "fixture", "bootstrap", "native"):
            self.assertIn("steps." + stage + ".outcome == 'success' && steps." +
                          stage + ".outputs.rc == '0'", s)
        tail = s.split("- name: Enforce actual native and independent receipt", 1)[-1]
        for stage in ("source", "deps", "fixture", "bootstrap",
                      "native", "audit", "safe", "privacy"):
            self.assertIn("steps." + stage + ".outcome", tail)
        for stage in ("DEPS", "FIXTURE", "BOOTSTRAP", "NATIVE",
                      "AUDIT", "SAFE", "PRIVACY"):
            self.assertIn("RUN507_" + stage + "_EXIT.txt", tail)

    def test_original_scores_raw_evidence_and_no_gate_promotion(self):
        s = self.source
        for marker in ("RUN505_BATCH_PROGRESS.jsonl",
                       "RUN505_BATCH_RESULT.json",
                       "RUN504_SCHEDULE.json",
                       "RUN507_SHA256SUMS.txt",
                       "rows_verified",
                       "consumer_messages_sha256",
                       "row_sha256",
                       "wrong_committed",
                       "'UTILITY_FAIL'",
                       "canonical_gate_pass",
                       "if: always()"):
            self.assertIn(marker, s)
        self.assertIn("run507-heldout10-safe-no-model-", s)
        self.assertIn("run507-heldout10-native-raw-", s)


if __name__ == "__main__":
    unittest.main()
