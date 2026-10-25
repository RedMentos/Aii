"""Run326 synthetic-only adversarial source and GGUF receipt checks."""
import tempfile
from pathlib import Path
import unittest

from scripts import audit_fp32_master_parity_run326 as A


def row(sha=A.EXPECTED_MASTER, tensor="abc", meta="same"):
    return {"sha256": sha, "tensors": {"a": {"sha256": tensor, "shape": [1],
            "type": 0, "bytes": 4}}, "metadata": {"general.name": meta},
            "tensor_count": 1}


class Run326SourceOnly(unittest.TestCase):
    def test_baseline_must_match_original_exact_master(self):
        self.assertEqual(A.classify(row(sha="x"), row(), {}, {}),
                         "BASELINE_NOT_REPRODUCED")

    def test_source_hash_mismatch_precedes_tensor_comparison(self):
        self.assertEqual(A.classify(row(), row(), {"config": "a"}, {"config": "b"}),
                         "SOURCE_MISMATCH")

    def test_real_tensor_payload_change_is_not_metadata_only(self):
        self.assertEqual(A.classify(row(), row(tensor="changed", meta="other"), {}, {}),
                         "TENSOR_DRIFT")

    def test_metadata_only_byte_drift(self):
        other = row(sha="another-file-sha", meta="changed")
        result = A.compare(row(), other, {}, {})
        self.assertEqual(result["status"], "METADATA_ONLY_DRIFT")
        self.assertEqual(result["metadata_different_keys"], ["general.name"])
        self.assertEqual(result["native_optimizer_epochs"], 0)
        self.assertEqual(result["gates"]["STEP2"], "UTILITY_FAIL")

    def test_no_drift(self):
        self.assertEqual(A.classify(row(), row(), {}, {}), "NO_DRIFT")

    def test_unexplained_binary_drift_is_red(self):
        self.assertEqual(A.classify(row(), row(sha="another-file-sha"), {}, {}),
                         "UNEXPLAINED_BINARY_DRIFT")

    def test_missing_source_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "snapshot"):
                A.source_hashes(Path(td) / "missing")

    def test_fake_source_weights_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "model.safetensors").write_bytes(b"not the pinned weights")
            with self.assertRaisesRegex(ValueError, "weight SHA"):
                A.source_hashes(root)

    def test_metadata_value_normalization_and_unknown_type(self):
        self.assertEqual(A._normal([b"one", {"x": 2}]),
                         [{"bytes_hex": "6f6e65"}, {"x": 2}])
        with self.assertRaisesRegex(TypeError, "unsupported"):
            A._normal(object())

    def test_status_not_raised_by_only_forged_metadata(self):
        original = row()
        variant = row(sha="different", tensor="mutated", meta="different")
        result = A.compare(original, variant, {}, {})
        self.assertEqual(result["status"], "TENSOR_DRIFT")
        self.assertFalse(result["tensor_payloads_equal"])
        self.assertFalse(result["model_weights_published"])


if __name__ == "__main__":
    unittest.main()
