"""P0X 150-call C3-only native orchestration and independent verifier mock tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts import p0x_c3_150_baseline as base
from scripts import p0x_c3_150_native_executor as native
from scripts import p0x_c3_150_native_verifier as verifier
from scripts import hb1b_c3_format_native_executor as hb1b_native
from scripts import hb1a_two_body_native_pilot as hb1
from tests.test_hb1a_native_executor_mock import HB1AOrchestrationSoftware, FakeModels, FakePool


class CapturingPool(FakePool):
    config = None

    def __init__(self, home, models, cfg):
        type(self).config = dict(cfg)
        super().__init__(home, models, cfg)
        FakePool.calls = []
        FakePool.closed = False


class P0XBaselineNativeMock(unittest.TestCase):
    def fake_hash(self, path):
        path = Path(path)
        if path.name == "llama-server":
            return base.RUNNER_SHA256
        if path.name == "C3_LANGUAGE.gguf":
            return base.C3_MODEL_SHA256
        return hb1.sha(path.read_bytes())

    def run_mock(self, home, out):
        with (patch.object(hb1b_native, "admit"),
              patch.object(hb1b_native, "file_sha", side_effect=self.fake_hash),
              patch("v13.config.initialize", return_value={
                  "system_stage": 0, "learning_mode": "RECORD_ONLY",
                  "latents_enabled": False, "jepa_weight": 0}),
              patch("v13.models.ModelManager", FakeModels),
              patch("v13.runners.RunnerPool", CapturingPool)):
            return native.run_native(home, out)

    def test_all_150_calls_and_headroom_consistent_no_gate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = HB1AOrchestrationSoftware().setup_home(root)
            FakePool.fail_at = None
            result = self.run_mock(home, root / "evidence")
            self.assertEqual(result["recorded_calls"], 150)
            self.assertTrue(result["process_reaped"])
            self.assertEqual(len(FakePool.calls), 150)
            self.assertTrue(CapturingPool.closed)
            self.assertEqual(CapturingPool.config["c3_sampling"], "off")
            score = json.loads((root / "evidence/SCORE.json").read_bytes())
            self.assertEqual(score["per_arm"]["c3_only"]["unknown"], 150)
            self.assertEqual(score["oracle_headroom"], 150)
            self.assertFalse(score["canonical_gate_pass"])
            verified = verifier.verify(root / "evidence")
            self.assertEqual(verified["rows"], 150)
            self.assertEqual(verified["status"],
                             "CLOSED_RECORD_CONSISTENT_NO_NATIVE_ATTESTATION_NO_GATE")
            self.assertFalse(verified["redmi_measured"])

    def test_injected_failure_retains_original_partial_raw(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = HB1AOrchestrationSoftware().setup_home(root)
            FakePool.fail_at = 5
            try:
                with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_INJECTED_RED"):
                    self.run_mock(home, root / "evidence")
                raw = json.loads((root / "evidence/RAW.json").read_bytes())
                receipt = json.loads((root / "evidence/RECEIPT.json").read_bytes())
                self.assertEqual(raw["status"], "FAIL_RETAIN_RAW")
                self.assertEqual(len(raw["rows"]), 4)
                self.assertEqual(receipt["error_type"], "RuntimeError")
                self.assertTrue(receipt["process_reaped_on_exit"])
                self.assertFalse((root / "evidence/SCORE.json").exists())
            finally:
                FakePool.fail_at = None

    def test_tampered_rehashed_score_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = HB1AOrchestrationSoftware().setup_home(root)
            FakePool.fail_at = None
            self.run_mock(home, root / "evidence")
            score_path = root / "evidence/SCORE.json"
            score = json.loads(score_path.read_bytes())
            score["oracle_headroom"] = 0
            score_path.write_bytes(hb1.canonical(score))
            receipt_path = root / "evidence/RECEIPT.json"
            receipt = json.loads(receipt_path.read_bytes())
            receipt["score_sha256"] = hb1.sha(score_path.read_bytes())
            receipt_path.write_bytes(hb1.canonical(receipt))
            with self.assertRaisesRegex(ValueError, "P0X_BASELINE_VERIFY_SCORE_RED"):
                verifier.verify(root / "evidence")

    def test_missing_home_fails_without_creating_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "P0X_BASELINE_PINNED_HOME_REQUIRED"):
                native.run_native(root / "missing", root / "out")
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
