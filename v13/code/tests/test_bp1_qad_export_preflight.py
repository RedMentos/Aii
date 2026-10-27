"""BP1 b10964 GGUF LFM2 export preflight; synthetic-only tests."""
import os
from pathlib import Path
import tempfile
import unittest

from scripts import bp1_qad_export_preflight as P


class ExportPreflightTests(unittest.TestCase):
    def test_source_commit_is_frozen(self):
        self.assertEqual(P.SOURCE_COMMIT, "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4")
        self.assertEqual(P.GATES["jepa_weight"], 0)

    def test_missing_lfm2_architecture_rejected(self):
        class OldGGUF:
            MODEL_ARCH_NAMES = {0: "llama"}
        with self.assertRaisesRegex(ValueError, "LFM2 architecture"):
            P.resolve_arch(OldGGUF)

    def test_unknown_tensor_mapping_rejected(self):
        class BrokenMap:
            def get_name(self, name): return None
        class BrokenGGUF:
            MODEL_ARCH_NAMES = {1: "lfm2"}
            @staticmethod
            def get_tensor_name_map(arch, n): return BrokenMap()
        with self.assertRaisesRegex(ValueError, "tensor mapping"):
            P.map_modules(BrokenGGUF)

    def test_wrong_checkout_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "source checkout"):
                P.verify_checkout(d)

    def test_exact_pinned_writer_synthetic_adapter_roundtrip(self):
        checkout = os.environ["BP1_GGUF_CHECKOUT"]
        with tempfile.TemporaryDirectory() as d:
            proof = P.run(checkout, Path(d) / "new-output")
            self.assertEqual(proof["source_commit"], P.SOURCE_COMMIT)
            self.assertEqual(proof["synthetic_tensors"], 4)
            self.assertEqual(len(proof["gguf_tensor_names"]), 4)
            self.assertFalse(proof["training_executed"])
            self.assertFalse(proof["model_utility_proven"])
            self.assertEqual(proof["gates"]["STEP2"], "UTILITY_FAIL")
            self.assertEqual(proof["gates"]["B3_L1"], "FAIL")
            self.assertEqual(proof["gates"]["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()
