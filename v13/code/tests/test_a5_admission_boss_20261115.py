"""Synthetic A5 admission fail-closed counterexamples (no native proof)."""
import unittest
from v13.a5_prefill_admission import SourceEnvelope, admit_sources


class A5AdmissionHardeningTests(unittest.TestCase):
    def test_required_without_consent_blocks_entire_route(self):
        result = admit_sources([
            SourceEnvelope("USER", "current", 4, required=True, consented=False),
            SourceEnvelope("B1", "optional", 2),
        ], 100)
        self.assertEqual(result.status, "REQUIRED_NOT_CONSENTED")
        self.assertEqual(result.accepted, ())
        self.assertEqual(result.used_tokens, 0)

    def test_optional_without_consent_does_not_block_required(self):
        result = admit_sources([
            SourceEnvelope("USER", "current", 4, required=True),
            SourceEnvelope("AUDIO", "private", 2, consented=False),
        ], 10)
        self.assertEqual([s.source_id for s in result.accepted], ["current"])
        self.assertEqual([s.source_id for s in result.rejected], ["private"])

    def test_invalid_token_counts_are_rejected(self):
        for value in (True, False, 1.2, "2", None, -1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    SourceEnvelope("USER", "current", value)

    def test_invalid_budget_types_are_rejected(self):
        for value in (True, 4.5, "10", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    admit_sources([], value)
                with self.assertRaises(ValueError):
                    admit_sources([], 10, value)

    def test_consent_flags_cannot_be_truthy_strings(self):
        for kwargs in ({"consented": "false"}, {"required": 1}):
            with self.assertRaises(ValueError):
                SourceEnvelope("A5", "source", 1, **kwargs)

    def test_required_overbudget_never_returns_optional(self):
        result = admit_sources([
            SourceEnvelope("A5", "optional", 1),
            SourceEnvelope("USER", "required", 8, required=True),
        ], 7)
        self.assertEqual(result.status, "REQUIRED_OVER_BUDGET")
        self.assertEqual(result.accepted, ())


if __name__ == "__main__":
    unittest.main()
