"""Synthetic contract checks; these are not real Redmi measurements."""
import unittest
from v13.native_prefill_profile import Sample, estimate

class NativeProfile(unittest.TestCase):
    def setUp(self):
        self.samples = [Sample("redmi", "c3-rev", 2, 128, 2, n, t, True, "DEVICE_RECEIPT")
                        for n, t in ((40, 1), (120, 3.5), (300, 8))]
        self.kw = dict(device="redmi", model_revision="c3-rev", threads=2,
                       batch=128, concurrent=2, prompt_tokens=300, remaining_s=30)
    def test_admission_with_verified_samples(self):
        self.assertTrue(estimate(self.samples, **self.kw)["admit"])
    def test_no_extrapolation(self):
        self.assertEqual(estimate(self.samples, **(self.kw | {"prompt_tokens": 600}))["reason"],
                         "OUTSIDE_MEASURED_TOKEN_RANGE")
    def test_no_profile_transfer(self):
        for key, val in (("device", "linux"), ("model_revision", "other"),
                         ("threads", 4), ("concurrent", 1)):
            self.assertEqual(estimate(self.samples, **(self.kw | {key: val}))["reason"],
                             "NO_MATCHING_VERIFIED_NATIVE_PROFILE")
    def test_synthetic_cannot_authorize(self):
        synthetic = [Sample("redmi", "c3-rev", 2, 128, 2, 300, 1, True)] * 3
        self.assertFalse(estimate(synthetic, **self.kw)["admit"])
    def test_failed_prefill_not_positive(self):
        failed = [Sample("redmi", "c3-rev", 2, 128, 2, 300, 28, False, "DEVICE_RECEIPT")] * 3
        self.assertFalse(estimate(failed, **self.kw)["admit"])
    def test_bad_budgets(self):
        for value in (0, -1, 1.2, True):
            self.assertEqual(estimate(self.samples, **(self.kw | {"prompt_tokens": value}))["reason"],
                             "INVALID_BUDGET")
        for reserve in (float('nan'), float('inf'), -1):
            with self.assertRaises(ValueError):
                estimate(self.samples, **self.kw, reserve_s=reserve)
    def test_deadline_rejection(self):
        self.assertEqual(estimate(self.samples, **(self.kw | {"remaining_s": 5}))["reason"],
                         "PREFILL_EXCEEDS_DEADLINE")

if __name__ == "__main__":
    unittest.main()
