"""Synthetic integration of exact-token admission and verified-profile gate.

No Redmi performance or phone acceptance claim.
"""
import unittest
from types import SimpleNamespace
from v13.prefill_route_gate import gate_route
from v13.native_prefill_profile import Sample


class GateTests(unittest.TestCase):
    def setUp(self):
        self.samples = [
            Sample("redmi", "c3-v1", 2, 128, 1, n, t, True, "DEVICE_RECEIPT")
            for n, t in [(40, 2), (120, 5), (300, 12)]
        ]
        self.kw = dict(device="redmi", model_revision="c3-v1", threads=2,
                       batch=128, concurrent=1, remaining_s=30)

    def decision(self, count=120, status="VERIFIED", **changes):
        return gate_route(SimpleNamespace(status=status, exact_prompt_tokens=count),
                          self.samples, **(self.kw | changes))

    def test_verified_exact_and_profile(self):
        r = self.decision()
        self.assertTrue(r.execute)
        self.assertEqual(r.exact_tokens, 120)

    def test_exact_over_budget_blocks_even_fast_profile(self):
        self.assertFalse(self.decision(status="RENDERED_OVER_BUDGET").execute)

    def test_no_verified_profile(self):
        r = gate_route(SimpleNamespace(status="VERIFIED", exact_prompt_tokens=120),
                       [], **self.kw)
        self.assertEqual(r.reason, "NO_MATCHING_VERIFIED_NATIVE_PROFILE")

    def test_wrong_revision(self):
        self.assertFalse(self.decision(model_revision="other").execute)

    def test_outside_measured_range(self):
        self.assertEqual(self.decision(count=301).reason,
                         "OUTSIDE_MEASURED_TOKEN_RANGE")

    def test_deadline(self):
        self.assertEqual(self.decision(count=300, remaining_s=10).reason,
                         "PREFILL_EXCEEDS_DEADLINE")

    def test_bool_token_rejected(self):
        self.assertFalse(self.decision(count=True).execute)

    def test_bad_native_config(self):
        self.assertEqual(self.decision(threads=True).reason,
                         "INVALID_NATIVE_CONFIG")


if __name__ == "__main__":
    unittest.main()
