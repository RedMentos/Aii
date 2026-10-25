"""Run333 source-only adversarial tests: never a native optimizer or tensor proof."""
import sys
import types
import unittest
from unittest.mock import patch

from scripts import audit_native_weight_delta_run333 as A


class Field:
    def __init__(self, value):
        self.value = value
    def contents(self):
        return self.value


class Tensor:
    def __init__(self, name, kind=0):
        import numpy as np
        self.name = name
        self.tensor_type = kind
        self.data = np.array([1.0], dtype=np.float32)
        self.shape = [1]
        self.n_elements = 1


class Reader:
    def __init__(self, arch="lfm2", kind=0, tensor_kind=0, missing=False):
        self.fields = {"general.architecture": Field(arch)}
        if not missing:
            self.fields["general.file_type"] = Field(kind)
        self.tensors = [Tensor(name, tensor_kind) for name in A.SELECTED] + [Tensor("other", tensor_kind)]
    def get_field(self, name):
        return self.fields.get(name)


def inspect(reader, master=False):
    fake = types.SimpleNamespace(GGUFReader=lambda _: reader,
                                 GGMLQuantizationType=types.SimpleNamespace(F32=0))
    with patch.dict(sys.modules, {"gguf": fake}):
        with patch.object(A, "EXPECTED_TENSORS", 5), patch.object(A, "EXPECTED_ELEMENTS", 5):
            return A.inspect("synthetic-not-a-file", master=master)


class Run333MetadataCompat(unittest.TestCase):
    def test_exact_master_requires_explicit_f32(self):
        self.assertEqual(A.check_file_type(Field(0), master=True), "EXPLICIT_F32")
        with self.assertRaisesRegex(ValueError, "master"):
            A.check_file_type(None, master=True)

    def test_only_epoch_can_omit_file_type(self):
        self.assertEqual(A.check_file_type(None, master=False), "OMITTED_EPOCH_ONLY")
        self.assertEqual(A.check_file_type(Field(0), master=False), "EXPLICIT_F32")

    def test_present_non_f32_rejected_for_master_and_epoch(self):
        for master in (True, False):
            with self.subTest(master=master), self.assertRaisesRegex(ValueError, "non-F32"):
                A.check_file_type(Field(1), master=master)

    def test_malformed_file_type_rejected(self):
        for value in ("wrong", {}, None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "malformed"):
                A.check_file_type(Field(value), master=False)

    def test_synthetic_epoch_missing_header_but_all_f32_is_accepted_structurally(self):
        _, tensors, _, mode = inspect(Reader(missing=True), master=False)
        self.assertEqual(mode, "OMITTED_EPOCH_ONLY")
        self.assertEqual(len(tensors), 5)
        self.assertEqual(set(A.SELECTED) & set(tensors), set(A.SELECTED))

    def test_synthetic_master_missing_header_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "master"):
            inspect(Reader(missing=True), master=True)

    def test_missing_or_wrong_architecture_rejected(self):
        for arch in ("other", None):
            with self.subTest(arch=arch), self.assertRaisesRegex(ValueError, "architecture"):
                inspect(Reader(arch=arch), master=False)

    def test_non_f32_tensor_rejected_even_when_header_omitted(self):
        with self.assertRaisesRegex(ValueError, "non-F32 GGUF tensor"):
            inspect(Reader(missing=True, tensor_kind=1), master=False)

    def test_missing_selected_tensor_rejected(self):
        reader = Reader(missing=True)
        reader.tensors[-2] = Tensor("unrelated")
        with self.assertRaisesRegex(ValueError, "selected"):
            inspect(reader, master=False)

    def test_duplicate_tensor_rejected(self):
        reader = Reader(missing=True)
        reader.tensors[-1] = Tensor(A.SELECTED[0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            inspect(reader, master=False)

    def test_tensor_count_and_elements_rejected(self):
        reader = Reader(missing=True)
        reader.tensors.append(Tensor("extra"))
        with self.assertRaisesRegex(ValueError, "count"):
            inspect(reader, master=False)
        reader = Reader(missing=True)
        reader.tensors[-1].n_elements = 2
        with self.assertRaisesRegex(ValueError, "element"):
            inspect(reader, master=False)

    def test_unselected_parameter_drift_rejected_by_original_assess(self):
        base = {k: {"sha256": "a", "shape": [1], "type": 0, "bytes": 4, "finite": True}
                for k in A.SELECTED}
        base["other"] = {"sha256": "static", "shape": [1], "type": 0, "bytes": 4, "finite": True}
        e1 = {k: dict(v) for k, v in base.items()}
        e2 = {k: dict(v) for k, v in base.items()}
        e1[A.SELECTED[0]]["sha256"] = "b"
        e2[A.SELECTED[0]]["sha256"] = "c"
        e1["other"]["sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "unselected"):
            A.assess(base, e1, e2)

    def test_missing_numeric_update_rejected(self):
        zero = {stage: {name: {"changed_elements": 0, "l2": 0.0, "max_abs": 0.0}
                        for name in A.SELECTED}
                for stage in ("baseline_to_epoch1", "epoch1_to_epoch2")}
        with self.assertRaisesRegex(ValueError, "numerical"):
            A.validate_numeric_deltas(zero)

    def test_original_run321_must_pass_before_any_header(self):
        with patch.object(A, "original_run321", return_value={"status": "FAIL_CLOSED"}):
            with self.assertRaisesRegex(ValueError, "Run321"):
                A.audit("master", "epoch1", "epoch2", {})

    def test_receipt_sha_must_pass_before_any_header(self):
        with patch.object(A, "original_run321", return_value={"status": "PASS_SOURCE_ONLY"}):
            with patch.object(A, "verify_report_and_paths", side_effect=ValueError("SHA mismatch")):
                with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                    A.audit("master", "epoch1", "epoch2", {})

    def test_negative_gates_unchanged(self):
        self.assertEqual(A.GATES["STEP2"], "UTILITY_FAIL")
        self.assertEqual(A.GATES["B3_L1"], "FAIL")
        self.assertEqual(A.GATES["Body_JEPA"], "UNAVAILABLE")
        self.assertEqual(A.GATES["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()
