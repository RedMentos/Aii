"""Run77 preregistered B1/B2 source-context scorer software tests only."""
import copy
import unittest

from scripts import jef_b1b2_context_fixture_797 as f
from scripts import run77_b1b2_context_verify as verifier


class Run77FixtureSoftware(unittest.TestCase):
    def test_six_balanced_disjoint_sources_and_oracle(self):
        rows = f.fixtures()
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["action"] for r in rows],
                         ["A", "B", "NONE", "A", "B", "NONE"])
        self.assertEqual([r["remaining"] for r in rows],
                         [20, 20, None, 50, 15, None])
        self.assertEqual(len({r["project"] for r in rows}), 6)
        for row in rows:
            self.assertIn("archived logistics policy", row["prior"])
            self.assertIn("latest logistics options", row["current"])
            self.assertNotIn("Maximum budget:", row["current"])
            self.assertNotIn("Maximum deadline:", row["current"])
            self.assertEqual(f.sha(row["prior"].encode()),
                             row["source_sha256"]["prior"])

    def test_strict_action_and_remaining_positive(self):
        self.assertEqual(f.strict_summary(
            "I recommend Option A. Remaining budget: 20 credits.",
            "A", 20), 1)
        self.assertEqual(f.strict_summary(
            "Select B; 15 credits remaining after purchase.",
            "B", 15), 1)
        self.assertEqual(f.strict_summary(
            "Neither option qualifies under the archived policy.",
            "NONE", None), 1)
        self.assertEqual(f.strict_summary(
            "No option qualifies; choose NONE.", "NONE", None), 1)

    def test_listing_options_without_decision_is_not_semantic_success(self):
        self.assertEqual(f.strict_summary(
            "Option A uses 160 credits and Option B uses 170 credits.",
            "A", 20), 0)
        self.assertEqual(f.strict_summary(
            "I recommend Option A, with 15 credits remaining.",
            "A", 20), 0)
        self.assertEqual(f.strict_summary(
            "Option A is cheaper but I choose B.", "A", 20), 0)
        self.assertEqual(f.strict_summary(
            "Neither option qualifies, 20 credits remaining.",
            "NONE", None), 0)

    def test_registered_paired_thresholds_and_red(self):
        good = {role: {"WITH_PRIOR": 5, "CURRENT_ONLY": 2}
                for role in f.ROLES}
        self.assertEqual(f.scientific_verdict(good, 3),
                         "B1B2_SMALL_CONTEXT_UTILITY_SIGNAL_SHADOW")
        bad = copy.deepcopy(good)
        bad["B1_DETAIL"]["WITH_PRIOR"] = 3
        bad["B1_DETAIL"]["CURRENT_ONLY"] = 2
        self.assertEqual(f.scientific_verdict(bad, 3),
                         "B1B2_CONTEXT_UTILITY_SCIENTIFIC_RED")
        self.assertEqual(f.scientific_verdict(good, 2),
                         "B1B2_CONTEXT_UTILITY_SCIENTIFIC_RED")

    def test_verifier_refuses_missing_native_or_authority_claim(self):
        with self.assertRaisesRegex(ValueError, "REPORT_PIN_RED"):
            verifier.verify({})
        base = {
            "schema": verifier.SCHEMA, "seed": f.SEED,
            "table_sha256": f.TABLE_SHA256,
            "binding": {"model_sha256": {
                "B1_DETAIL": f.B1_SHA256,
                "B2_GIST": f.B2_SHA256},
                "runner_sha256": f.RUNNER_SHA256},
            "native_call_count": 36,
            "independent_utility_proven": True,
        }
        with self.assertRaisesRegex(ValueError, "AUTHORITY_RED"):
            verifier.verify(base)

    def test_frozen_source_and_runner_pins(self):
        self.assertEqual(len(f.TABLE_SHA256), 64)
        self.assertEqual(len(f.B1_SHA256), 64)
        self.assertEqual(len(f.B2_SHA256), 64)
        self.assertEqual(len(f.RUNNER_SHA256), 64)
        self.assertEqual(f.SEED, 797)


if __name__ == "__main__":
    unittest.main()
