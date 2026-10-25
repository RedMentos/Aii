"""Run332 synthetic metadata-only adversarial tests; NOT native GGUF evidence."""
import unittest
from unittest.mock import patch
from scripts import diagnose_native_gguf_header_run332 as D


class Field:
    def __init__(self, value):
        self.value = value
    def contents(self):
        return self.value


class Tensor:
    def __init__(self, name, kind=0, count=1):
        self.name = name
        self.tensor_type = kind
        self.n_elements = count


class Reader:
    def __init__(self, arch="lfm2", file_type=0, kind=0, missing=None):
        self.fields = {"general.architecture": Field(arch), "general.file_type": Field(file_type)}
        if missing:
            self.fields.pop(missing)
        self.tensors = [Tensor(name, kind) for name in D.SELECTED] + [Tensor("other", kind)]
    def get_field(self, name):
        return self.fields.get(name)


def scan(reader):
    return D.scan_reader(reader, expected_count=5, expected_elements=5)


class Run332Metadata(unittest.TestCase):
    def test_normal_header_is_metadata_only(self):
        row = scan(Reader())
        self.assertTrue(row["architecture_is_lfm2"])
        self.assertEqual(row["file_type"], 0)
        self.assertEqual(row["tensor_types"], {"0": 5})
        self.assertNotIn("data", str(row).lower())

    def test_epoch_header_missing_is_reported_not_assumed(self):
        for key in ("general.architecture", "general.file_type"):
            with self.subTest(key=key):
                row = scan(Reader(missing=key))
                self.assertFalse(row["architecture_present"] if key.endswith("architecture") else row["file_type_present"])

    def test_epoch_wrong_arch_and_file_type_reported(self):
        self.assertFalse(scan(Reader(arch="other"))["architecture_is_lfm2"])
        self.assertEqual(scan(Reader(file_type=1))["file_type"], 1)

    def test_non_f32_payload_rejected_even_when_metadata_claims_f32(self):
        with self.assertRaisesRegex(ValueError, "non-F32"):
            scan(Reader(kind=1))

    def test_missing_selected_tensor_rejected(self):
        r = Reader()
        r.tensors[-2] = Tensor("another")
        with self.assertRaisesRegex(ValueError, "selected"):
            scan(r)

    def test_duplicate_tensor_rejected(self):
        r = Reader()
        r.tensors[-1] = Tensor(D.SELECTED[0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            scan(r)

    def test_tensor_count_and_element_count_rejected(self):
        with self.assertRaisesRegex(ValueError, "count"):
            D.scan_reader(Reader(), expected_count=6, expected_elements=5)
        with self.assertRaisesRegex(ValueError, "element"):
            D.scan_reader(Reader(), expected_count=5, expected_elements=6)

    def test_invalid_metadata_scalar_is_not_leaked(self):
        r = Reader()
        r.fields["general.architecture"] = Field({"secret": "never emit"})
        row = scan(r)
        self.assertFalse(row["architecture_present"])
        self.assertNotIn("secret", str(row))

    def test_original_full_file_receipt_required_before_reader(self):
        with patch.object(D, "verify_report_and_paths", side_effect=ValueError("SHA mismatch")):
            with patch.object(D, "audit_run321", return_value={"status": "PASS_SOURCE_ONLY"}):
                with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                    D.run("a", "b", "c", {})

    def test_negative_gates_preserved(self):
        self.assertEqual(D.GATES["STEP2"], "UTILITY_FAIL")
        self.assertEqual(D.GATES["B3_L1"], "FAIL")
        self.assertEqual(D.GATES["Body_JEPA"], "UNAVAILABLE")
        self.assertEqual(D.GATES["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()
