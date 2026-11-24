"""RED-first, source-only counterexamples for preregistered STEP2 score integrity.

No native inference, frozen cohort mutation or gate promotion.
"""
import copy
import math
import unittest

from v13.utility import paired_utility


VARIANTS = (
    "b1_only", "b2_only", "both_none", "both_exact", "both_control",
    "same_policy_dual", "prompt_only_dual",
)
FIXTURES = ("one", "two")


def complementary_rows():
    rows = []
    for variant in VARIANTS:
        for fixture in FIXTURES:
            if variant == "b1_only":
                utility = .8 if fixture == "one" else .2
            elif variant == "b2_only":
                utility = .2 if fixture == "one" else .8
            elif variant == "both_exact":
                utility = 1.0
            else:
                utility = .5
            rows.append({"variant": variant, "fixture": fixture,
                         "score": {"utility": utility}})
    return rows


class PairedScoreIntegrityReview(unittest.TestCase):
    def test_valid_complementarity_control_unchanged(self):
        report = paired_utility(complementary_rows(), FIXTURES)
        self.assertTrue(report["complete"])
        self.assertTrue(report["scoped_utility_gate_pass"])
        self.assertEqual(report["mean_utility"]["both_exact"], 1.0)

    def test_bad_explicit_utility_cannot_be_a_valid_pair(self):
        bad_values = (float("nan"), float("inf"), -float("inf"), 10 ** 10000, True,
                      "1", -0.01, 1.01, None)
        for bad in bad_values:
            with self.subTest(value='huge-int' if type(bad) is int and bad.bit_length() > 1000 else repr(bad)):
                rows = complementary_rows()
                rows[6]["score"]["utility"] = bad
                report = paired_utility(rows, FIXTURES)
                self.assertFalse(report["complete"])
                self.assertFalse(report["scoped_utility_gate_pass"])
                self.assertIn("both_exact", report["coverage_errors"])
                self.assertTrue(all(math.isfinite(x)
                                    for x in report["mean_utility"].values()))

    def test_failed_inference_null_or_missing_score_is_zero_not_dropped(self):
        for replacement in (None, {}):
            with self.subTest(replacement=replacement):
                rows = complementary_rows()
                rows[6]["score"] = copy.deepcopy(replacement)
                report = paired_utility(rows, FIXTURES)
                self.assertTrue(report["complete"])
                self.assertEqual(report["mean_utility"]["both_exact"], .5)
                self.assertFalse(report["scoped_utility_gate_pass"])

    def test_duplicate_preregistered_fixture_id_fails_closed(self):
        report = paired_utility(complementary_rows(), ("one", "one", "two"))
        self.assertFalse(report["complete"])
        self.assertFalse(report["scoped_utility_gate_pass"])
        self.assertIn("_cohort", report["coverage_errors"])


if __name__ == "__main__":
    unittest.main()
