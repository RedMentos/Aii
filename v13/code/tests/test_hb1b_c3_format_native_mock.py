"""HB1b native C3 format orchestration/verification mock tests; no model weights."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_followup as hb1b
from scripts import hb1b_c3_format_native_executor as native
from scripts import hb1b_c3_format_native_verifier as verifier
from tests.test_hb1a_native_executor_mock import HB1AOrchestrationSoftware, FakeModels, FakePool


class CapturingPool(FakePool):
    config = None

    def __init__(self, home, models, cfg):
        type(self).config = dict(cfg)
        super().__init__(home, models, cfg)
        FakePool.calls = []  # FakePool.get appends to its base-class call ledger
        FakePool.closed = False


class HB1BNativeMock(unittest.TestCase):
    def fake_hash(self, path):
        path = Path(path)
        if path.name == "llama-server":
            return hb1b.RUNNER_SHA256
        if path.name == "C3_LANGUAGE.gguf":
            return hb1b.C3_MODEL_SHA256
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def setup(self, root):
        helper = HB1AOrchestrationSoftware()
        home = helper.setup_home(root)
        FakePool.fail_at = None
        helper.run_with_mocks(home, root / "parent")
        return home, root / "parent"

    def run_mock(self, home, out, parent):
        raw_sha = hb1.sha((parent / "RAW.json").read_bytes())
        score_sha = hb1.sha((parent / "SCORE.json").read_bytes())
        with (patch.object(hb1b, "PARENT_RAW_SHA256", raw_sha),
              patch.object(hb1b, "PARENT_SCORE_SHA256", score_sha),
              patch.object(native, "admit"),
              patch.object(native, "file_sha", side_effect=self.fake_hash),
              patch("v13.config.initialize", return_value={
                  "system_stage": 0, "learning_mode": "RECORD_ONLY",
                  "latents_enabled": False, "jepa_weight": 0}),
              patch("v13.models.ModelManager", FakeModels),
              patch("v13.runners.RunnerPool", CapturingPool)):
            result = native.run_native(home, out, parent)
        return result

    def verify_mock(self, out, parent):
        raw_sha = hb1.sha((parent / "RAW.json").read_bytes())
        score_sha = hb1.sha((parent / "SCORE.json").read_bytes())
        with (patch.object(hb1b, "PARENT_RAW_SHA256", raw_sha),
              patch.object(hb1b, "PARENT_SCORE_SHA256", score_sha)):
            return verifier.verify(out, parent)

    def test_24_calls_same_sampling_schema_only_for_half(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, parent = self.setup(root)
            FakePool.fail_at = None
            result = self.run_mock(home, root / "evidence", parent)
            self.assertEqual(result["recorded_calls"], 24)
            self.assertTrue(result["process_reaped"])
            self.assertTrue(CapturingPool.closed)
            self.assertEqual(len(FakePool.calls), 24)
            self.assertEqual(sum(schema is not None for _, _, _, schema in FakePool.calls), 12)
            self.assertEqual(CapturingPool.config["c3_sampling"], "off")
            self.assertEqual(CapturingPool.config["temperature"], .1)
            self.assertEqual(CapturingPool.config["threads"], 2)
            score = json.loads((root / "evidence/SCORE.json").read_bytes())
            self.assertEqual(score["per_arm"]["exact_schema"]["exact"], 2)
            self.assertEqual(score["per_arm"]["exact_plain"]["unparseable"], 6)
            self.assertEqual(score["per_arm"]["native_plain"]["unparseable"], 6)
            self.assertFalse(score["canonical_gate_pass"])
            verified = self.verify_mock(root / "evidence", parent)
            self.assertEqual(verified["status"],
                             "CLOSED_RECORD_CONSISTENT_NO_NATIVE_ATTESTATION_NO_GATE")
            self.assertFalse(verified["redmi_measured"])

    def test_failure_retains_partial_raw_and_reaps(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, parent = self.setup(root)
            FakePool.fail_at = 5
            try:
                with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_INJECTED_RED"):
                    self.run_mock(home, root / "evidence", parent)
                raw = json.loads((root / "evidence/RAW.json").read_bytes())
                receipt = json.loads((root / "evidence/RECEIPT.json").read_bytes())
                self.assertEqual(raw["status"], "FAIL_RETAIN_RAW")
                self.assertEqual(len(raw["rows"]), 4)
                self.assertEqual(receipt["error_type"], "RuntimeError")
                self.assertTrue(receipt["process_reaped_on_exit"])
                self.assertFalse((root / "evidence/SCORE.json").exists())
            finally:
                FakePool.fail_at = None

    def test_tamper_rehashed_score_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, parent = self.setup(root)
            FakePool.fail_at = None
            self.run_mock(home, root / "evidence", parent)
            path = root / "evidence/SCORE.json"
            score = json.loads(path.read_bytes())
            score["rows"] = 23
            path.write_bytes(hb1.canonical(score))
            receipt_path = root / "evidence/RECEIPT.json"
            receipt = json.loads(receipt_path.read_bytes())
            receipt["score_sha256"] = hb1.sha(path.read_bytes())
            receipt_path.write_bytes(hb1.canonical(receipt))
            with self.assertRaisesRegex(ValueError, "HB1B_VERIFY_SCORE_RED"):
                self.verify_mock(root / "evidence", parent)

    def test_missing_home_fails_before_any_native_calls(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "HB1B_PINNED_HOME_REQUIRED"):
                native.run_native(root / "missing", root / "out", root / "missing-parent")
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
