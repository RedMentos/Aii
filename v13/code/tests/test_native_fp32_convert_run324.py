"""Run324 synthetic fail-closed FP32 header/metadata checks, no real model claim."""
import struct
from pathlib import Path
import tempfile
import unittest

from scripts import probe_native_fp32_convert_run324 as P


def header(magic=b"GGUF", version=3, tensors=220, kv=26):
    return struct.pack("<4sIQQ", magic, version, tensors, kv)


class Field:
    def __init__(self, value):
        self.value = value

    def contents(self):
        return self.value


class Tensor:
    def __init__(self, kind=0, elements=350_000_000):
        self.tensor_type = kind
        self.n_elements = elements


class Reader:
    def __init__(self, architecture="lfm2", file_type=0, kind=0, elements=350_000_000):
        self.fields = {"general.architecture": Field(architecture),
                       "general.file_type": Field(file_type)}
        self.tensors = [Tensor(kind, elements)]

    def get_field(self, key):
        return self.fields.get(key)


class Run324FP32Validation(unittest.TestCase):
    def test_valid_synthetic_header(self):
        row = P.parse_header(header(), 1_400_000_000)
        self.assertEqual(row["tensor_count"], 220)
        self.assertEqual(row["gguf_version"], 3)

    def test_truncated_or_wrong_magic(self):
        for h in (header()[:20], header(magic=b"NOPE")):
            with self.subTest(h=h[:4]), self.assertRaisesRegex(ValueError, "magic"):
                P.parse_header(h, 1_400_000_000)

    def test_non_f32_master_size_rejected(self):
        with self.assertRaisesRegex(ValueError, "byte size"):
            P.parse_header(header(), 500_000_000)

    def test_empty_tensor_header_rejected(self):
        with self.assertRaisesRegex(ValueError, "tensor count"):
            P.parse_header(header(tensors=0), 1_400_000_000)

    def test_bad_metadata_count_rejected(self):
        with self.assertRaisesRegex(ValueError, "metadata"):
            P.parse_header(header(kv=0), 1_400_000_000)

    def test_f32_reader_metadata_pass(self):
        row = P.inspect_reader(Reader(), 0)
        self.assertTrue(row["all_tensors_f32"])
        self.assertEqual(row["f32_elements"], 350_000_000)

    def test_quantized_tensor_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-F32"):
            P.inspect_reader(Reader(kind=2), 0)

    def test_wrong_architecture_or_file_type_rejected(self):
        with self.assertRaisesRegex(ValueError, "architecture"):
            P.inspect_reader(Reader(architecture="qwen"), 0)
        with self.assertRaisesRegex(ValueError, "file type"):
            P.inspect_reader(Reader(file_type=2), 0)

    def test_implausible_parameter_count_rejected(self):
        with self.assertRaisesRegex(ValueError, "element count"):
            P.inspect_reader(Reader(elements=100), 0)

    def test_wrong_pinned_source_tar_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tar = Path(td) / "fake.tar.gz"
            tar.write_bytes(b"not official")
            with self.assertRaisesRegex(ValueError, "source tar"):
                P.verify(tar, td, {}, tar, tar)


if __name__ == "__main__":
    unittest.main()
