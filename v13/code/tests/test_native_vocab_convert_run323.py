"""Run323 source-only structural GGUF negative tests, not native conversion proof."""
import struct
import tempfile
from pathlib import Path
import unittest

from scripts import probe_native_vocab_convert_run323 as P


class Run323VocabGGUFStructure(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "vocab.gguf"
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, magic=b"GGUF", version=3, tensors=0, kv=12, size=65536):
        header = struct.pack("<4sIQQ", magic, version, tensors, kv)
        self.path.write_bytes((header + b"\x00" * max(0, size - len(header)))[:size])

    def test_vocab_only_header_passes_as_structure_only(self):
        row = P.inspect_vocab_gguf(self.path)
        self.assertEqual(row["gguf_version"], 3)
        self.assertEqual(row["tensor_count"], 0)
        self.assertEqual(row["metadata_count"], 12)
        self.assertEqual(len(row["sha256"]), 64)

    def test_magic_corruption_rejected(self):
        self.write(magic=b"NOPE")
        with self.assertRaisesRegex(ValueError, "magic"):
            P.inspect_vocab_gguf(self.path)

    def test_truncated_header_rejected(self):
        self.write(size=20)
        with self.assertRaisesRegex(ValueError, "byte size"):
            P.inspect_vocab_gguf(self.path)

    def test_nonzero_tensors_rejected(self):
        self.write(tensors=1)
        with self.assertRaisesRegex(ValueError, "contains tensors"):
            P.inspect_vocab_gguf(self.path)

    def test_wrong_version_rejected(self):
        self.write(version=99)
        with self.assertRaisesRegex(ValueError, "version"):
            P.inspect_vocab_gguf(self.path)

    def test_implausible_metadata_count_rejected(self):
        self.write(kv=0)
        with self.assertRaisesRegex(ValueError, "metadata"):
            P.inspect_vocab_gguf(self.path)

    def test_missing_file_or_symlink_rejected(self):
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            P.inspect_vocab_gguf(self.path)
        self.path.symlink_to(Path(self.tmp.name) / "no-such-target")
        with self.assertRaisesRegex(ValueError, "missing"):
            P.inspect_vocab_gguf(self.path)

    def test_wrong_source_tar_hash_rejected_before_vocab_authority(self):
        tar = Path(self.tmp.name) / "b10964.tar.gz"
        tar.write_bytes(b"unverified")
        with self.assertRaisesRegex(ValueError, "source tar SHA"):
            P.verify(self.path, Path(self.tmp.name), {}, tar, self.path)


if __name__ == "__main__":
    unittest.main()
