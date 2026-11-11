"""Synthetic A3 NPZ structural audit regression tests (not hardware tests)."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from v13.a3_checkpoint_audit_candidate import audit, RAW_DIM, LATENT_DIM, TEACHER_DIM, STEM

def fixture():
    return dict(projector=np.zeros((RAW_DIM, LATENT_DIM)), reconstruction_decoder=np.zeros((LATENT_DIM, RAW_DIM)),
                teacher_basis=np.zeros((LATENT_DIM, TEACHER_DIM)), teacher_mean=np.zeros(TEACHER_DIM),
                input_mean=np.zeros(RAW_DIM), support=np.zeros((2, RAW_DIM)),
                support_floor=np.array(0.5), stem=np.array(STEM))

class Audit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "a3.npz"
    def tearDown(self):
        self.temp.cleanup()
    def check(self, **changes):
        data = fixture(); data.update(changes); np.savez(self.path, **data)
        return audit(self.path)
    def test_valid_structure_never_authorizes(self):
        out = self.check()
        self.assertEqual(out["status"], "STRUCTURE_ONLY")
        self.assertFalse(out["runtime_admission_authorized"])
        self.assertFalse(out["device_verified"])
    def test_wrong_projector_dimensions(self):
        with self.assertRaises(ValueError): self.check(projector=np.zeros((4, 16)))
    def test_nonfinite_teacher_basis(self):
        a = fixture()["teacher_basis"]; a[0,0] = np.nan
        with self.assertRaises(ValueError): self.check(teacher_basis=a)
    def test_object_dtype_forbidden(self):
        with self.assertRaises(ValueError): self.check(stem=np.array({"fake":1}, dtype=object))
    def test_support_rows_bounded(self):
        with self.assertRaises(ValueError): self.check(support=np.zeros((0, RAW_DIM)))
    def test_bad_floor(self):
        with self.assertRaises(ValueError): self.check(support_floor=np.array(float("inf")))
    def test_wrong_stem(self):
        with self.assertRaises(ValueError): self.check(stem=np.array("different"))
    def test_extra_member(self):
        with self.assertRaises(ValueError): self.check(extra=np.zeros(1))
    def test_symlink_refused(self):
        self.check()
        alias = Path(self.temp.name) / "alias.npz"
        alias.symlink_to(self.path)
        with self.assertRaises(OSError): audit(alias)

    def test_float16_floor_is_not_a_supported_checkpoint_dtype(self):
        with self.assertRaises(ValueError):
            self.check(support_floor=np.array(0.5, dtype=np.float16))
    def test_nonfinite_support_rejected(self):
        support = fixture()["support"]
        support[0, 0] = np.inf
        with self.assertRaises(ValueError):
            self.check(support=support)
    def test_expanded_member_limit_rejected_before_numpy_load(self):
        data = fixture()
        data["support"] = np.zeros((2049, RAW_DIM), dtype=np.float64)
        np.savez_compressed(self.path, **data)
        with self.assertRaises(ValueError):
            audit(self.path)
    def test_invalid_zip_reports_valueerror(self):
        self.path.write_bytes(b"not-a-zip-archive")
        with self.assertRaisesRegex(ValueError, "corrupt A3 checkpoint archive"):
            audit(self.path)

    def test_corrupted_member_crc_reports_valueerror(self):
        self.check()
        raw = self.path.read_bytes()
        # Mutate the stored NPY payload, leaving the central directory intact.
        target = "projector.npy"
        import zipfile
        with zipfile.ZipFile(self.path) as archive:
            info = archive.getinfo(target)
            offset = info.header_offset
        name_len = int.from_bytes(raw[offset + 26:offset + 28], "little")
        extra_len = int.from_bytes(raw[offset + 28:offset + 30], "little")
        payload = offset + 30 + name_len + extra_len
        tampered = bytearray(raw)
        tampered[payload + 150] ^= 0x01
        self.path.write_bytes(tampered)
        with self.assertRaisesRegex(ValueError, "corrupt A3 checkpoint archive"):
            audit(self.path)

    def test_truncated_archive_rejected(self):
        self.check()
        raw = self.path.read_bytes()
        self.path.write_bytes(raw[:len(raw) // 2])
        with self.assertRaises((ValueError, OSError, EOFError, __import__("zipfile").BadZipFile)):
            audit(self.path)

if __name__ == "__main__":
    unittest.main()
