"""P0X 600-call source-arm native mock and independent verifier tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_native_executor as hb1b_native
from scripts import p0x_c3_150_native_executor as baseline_native
from scripts import p0x_c3_600_native_executor as native
from scripts import p0x_c3_600_native_verifier as verifier
from tests.test_hb1a_native_executor_mock import HB1AOrchestrationSoftware, FakeModels, FakePool


class CapturingPool(FakePool):
    config = None

    def __init__(self, home, models, cfg):
        type(self).config = dict(cfg)
        super().__init__(home, models, cfg)
        FakePool.calls = []
        FakePool.closed = False


class P0XArmsNativeMock(unittest.TestCase):
    def fake_hash(self, path):
        path = Path(path)
        if path.name == "llama-server":
            return native.arms.RUNNER_SHA256
        if path.name == "C3_LANGUAGE.gguf":
            return native.arms.C3_MODEL_SHA256
        return hb1.sha(path.read_bytes())

    def context(self):
        return (patch.object(hb1b_native, "admit"),
                patch.object(hb1b_native, "file_sha", side_effect=self.fake_hash),
                patch("v13.config.initialize", return_value={
                    "system_stage": 0, "learning_mode": "RECORD_ONLY",
                    "latents_enabled": False, "jepa_weight": 0}),
                patch("v13.models.ModelManager", FakeModels),
                patch("v13.runners.RunnerPool", CapturingPool))

    def setup(self, root):
        home = HB1AOrchestrationSoftware().setup_home(root)
        FakePool.fail_at = None
        with self.context()[0], self.context()[1], self.context()[2], self.context()[3], self.context()[4]:
            baseline_native.run_native(home, root / "baseline")
        return home, root / "baseline"

    def run_mock(self, home, out, baseline):
        raw_sha = hb1.sha((baseline / "RAW.json").read_bytes())
        score_sha = hb1.sha((baseline / "SCORE.json").read_bytes())
        patches = self.context()
        with (patch.object(native, "BASELINE_RAW_SHA256", raw_sha),
              patch.object(native, "BASELINE_SCORE_SHA256", score_sha),
              patches[0], patches[1], patches[2], patches[3], patches[4]):
            return native.run_native(home, out, baseline)

    def verify_mock(self, out, baseline):
        raw_sha = hb1.sha((baseline / "RAW.json").read_bytes())
        score_sha = hb1.sha((baseline / "SCORE.json").read_bytes())
        with (patch.object(native, "BASELINE_RAW_SHA256", raw_sha),
              patch.object(native, "BASELINE_SCORE_SHA256", score_sha)):
            return verifier.verify(out, baseline)

    def test_600_calls_and_baseline_comparison_no_gate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, baseline = self.setup(root)
            result = self.run_mock(home, root / "evidence", baseline)
            self.assertEqual(result["recorded_calls"], 600)
            self.assertTrue(result["process_reaped"])
            self.assertEqual(len(FakePool.calls), 600)
            self.assertTrue(CapturingPool.closed)
            self.assertEqual(CapturingPool.config["c3_sampling"], "off")
            score = json.loads((root / "evidence/SCORE.json").read_bytes())
            self.assertTrue(all(v["unknown"] == 150 for v in score["per_arm"].values()))
            comparison = json.loads((root / "evidence/COMPARISON.json").read_bytes())
            self.assertEqual(comparison["improvement"], 0)
            self.assertFalse(comparison["threshold_met"])
            verified = self.verify_mock(root / "evidence", baseline)
            self.assertEqual(verified["rows"], 600)
            self.assertFalse(verified["canonical_gate_pass"])

    def test_failure_retains_four_original_rows(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, baseline = self.setup(root)
            FakePool.fail_at = 5
            try:
                with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_INJECTED_RED"):
                    self.run_mock(home, root / "evidence", baseline)
                raw = json.loads((root / "evidence/RAW.json").read_bytes())
                receipt = json.loads((root / "evidence/RECEIPT.json").read_bytes())
                self.assertEqual(raw["status"], "FAIL_RETAIN_RAW")
                self.assertEqual(len(raw["rows"]), 4)
                self.assertTrue(receipt["process_reaped_on_exit"])
                self.assertFalse((root / "evidence/SCORE.json").exists())
            finally:
                FakePool.fail_at = None

    def test_missing_baseline_or_headroom_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = HB1AOrchestrationSoftware().setup_home(root)
            with self.assertRaises(FileNotFoundError):
                native.baseline_receipt(root / "missing")
            self.assertFalse((root / "evidence").exists())


if __name__ == "__main__":
    unittest.main()
