import unittest
from prefill_admission import NativeProfile, admit

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.profile = NativeProfile("C3", "REDMI_NATIVE", 100, 5, 20, 2, "CONSENTED_DEVICE")

    def test_unknown_refuses(self):
        self.assertFalse(admit(None, "C3", 100, 10, 30).admitted)

    def test_cross_organ_refuses(self):
        self.assertFalse(admit(self.profile, "B1", 100, 10, 30).admitted)

    def test_prefill_plus_decode(self):
        self.assertTrue(admit(self.profile, "C3", 100, 10, 30).admitted)
        self.assertFalse(admit(self.profile, "C3", 620, 10, 30).admitted)

    def test_elapsed_counts(self):
        self.assertFalse(admit(self.profile, "C3", 100, 10, 8, 2).admitted)

    def test_synthetic_not_phone(self):
        with self.assertRaises(ValueError):
            NativeProfile("C3", "LINUX_NATIVE", 100, 1, 10, 1, "SYNTHETIC")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            admit(self.profile, "C3", -1, 2, 30)
        with self.assertRaises(ValueError):
            admit(self.profile, "C3", 1, 2, float("nan"))

if __name__ == "__main__":
    unittest.main()
