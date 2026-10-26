"""Run470 software/synthetic-only exact-pair and non-promotion tests."""
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run470_step2_complementarity as R


def matrix():
    out = {}
    for arm in R.ARMS:
        for seed in R.SEEDS:
            rows = {}
            for index, fixture in enumerate(R.FIXTURES):
                for variant in R.VARIANTS:
                    if variant == "b1_only":
                        val = .3 if index < 3 else .1
                    elif variant == "b2_only":
                        val = .1 if index < 3 else .3
                    elif variant == R.PRIMARY:
                        val = {"O": .7, "P": .9, "S": .8}[arm]
                    else:
                        val = .2
                    rows[(fixture, variant)] = val
            out[(arm, seed)] = rows
    return out


class Run470Diagnostics(unittest.TestCase):
    def test_complete_three_seed_primary_and_solo_coverage(self):
        result = R.diagnose(matrix())
        self.assertEqual(result["rows"], 378)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        self.assertTrue(all(result["exploratory_strict_dominance"].values()))
        p = result["between_arm_primary"]["pointer_minus_off"]
        self.assertEqual((p["pairs"], p["wins"], p["ties"], p["losses"]),
                         (18, 18, 0, 0))
        self.assertAlmostEqual(p["mean"], .2)
        for seed in R.SEEDS:
            self.assertEqual(result["per_seed_solo_coverage"]["P"][str(seed)],
                             {"b1_wins": 3, "b2_wins": 3})
        self.assertEqual(result["within_arm_primary_minus_controls"]["P"]
                         ["both_none"]["pairs"], 18)

    def test_missing_and_extra_pairs_rejected(self):
        m = matrix()
        m.pop(("P", 22))
        with self.assertRaisesRegex(ValueError, "FROZEN_NINE_ARM"):
            R.diagnose(m)
        m = matrix()
        m[("P", 22)].pop(("Alder", "both_exact"))
        with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE_VARIANT"):
            R.diagnose(m)
        m = matrix()
        m[("P", 22)][("extra", "both_exact")] = .5
        with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE_VARIANT"):
            R.diagnose(m)

    def test_bad_scores_rejected_without_promotion(self):
        for bad in (True, None, "0.5", math.nan, math.inf, -1e-9, 1.00001):
            with self.subTest(bad=bad):
                m = matrix()
                m[("P", 20)][("Alder", "both_exact")] = bad
                with self.assertRaisesRegex(ValueError, "NONFINITE_OR_INVALID"):
                    R.diagnose(m)

    def test_negative_and_tied_dominance_remains_diagnostic(self):
        m = matrix()
        for seed in R.SEEDS:
            for fixture in R.FIXTURES:
                m[("P", seed)][(fixture, R.PRIMARY)] = .2
        result = R.diagnose(m)
        self.assertFalse(result["exploratory_strict_dominance"]["P"])
        self.assertEqual(result["within_arm_primary_minus_controls"]["P"]
                         ["both_none"]["ties"], 18)
        self.assertFalse(result["canonical_gate_pass"])

    def test_solo_coverage_not_faked_by_single_seed(self):
        m = matrix()
        for fixture in R.FIXTURES:
            m[("P", 22)][(fixture, "b1_only")] = .3
            m[("P", 22)][(fixture, "b2_only")] = .1
        result = R.diagnose(m)
        self.assertFalse(result["exploratory_strict_dominance"]["P"])
        self.assertEqual(result["per_seed_solo_coverage"]["P"]["22"]["b2_wins"], 0)

    def test_unverified_export_refused_before_read(self):
        fake = type(sys)("run469_native378_utility")
        fake.ARMS, fake.SEEDS, fake.FIXTURES, fake.VARIANTS = (
            R.ARMS, R.SEEDS, R.FIXTURES, R.VARIANTS)
        fake.analyze = lambda *a: {"status": "RED", "rows_verified": 378,
                                    "canonical_gate_pass": False,
                                    "step2_exit": "UTILITY_FAIL"}
        with patch.dict(sys.modules, {"run469_native378_utility": fake}):
            with self.assertRaisesRegex(ValueError, "RUN469_INDEPENDENT"):
                R.analyze("/not-real-native", {})

    def test_frozen_cohort_change_refused(self):
        fake = type(sys)("run469_native378_utility")
        fake.ARMS, fake.SEEDS, fake.FIXTURES, fake.VARIANTS = (
            R.ARMS, R.SEEDS, R.FIXTURES[:-1], R.VARIANTS)
        fake.analyze = lambda *a: self.fail("should not read unverified source")
        with patch.dict(sys.modules, {"run469_native378_utility": fake}):
            with self.assertRaisesRegex(ValueError, "FROZEN_RUN469_COHORT"):
                R.analyze("/not-real-native", {})


if __name__ == "__main__":
    unittest.main()
