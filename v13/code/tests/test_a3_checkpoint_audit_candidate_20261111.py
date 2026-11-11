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

if __name__ == "__main__":
    unittest.main()
