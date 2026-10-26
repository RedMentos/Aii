"""Run469 source-only utility matrix and negative gate tests; no native claims."""
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run469_native378_utility as A


def matrix():
    return {(arm, seed): {key: {"O": .2, "P": .6, "S": .4}[arm]
                          for key in A.EXPECTED}
            for arm, seed in A.IDS}


class Run469UtilityTests(unittest.TestCase):
    def test_frozen_nine_arm_pairing_exact_and_nonpromoting(self):
        d = A.aggregate(matrix())
        self.assertEqual(d["rows"], 378)
        self.assertEqual(d["seeds"], [20, 21, 22])
        self.assertEqual(d["arms"], ["O", "P", "S"])
        for variant in A.VARIANTS:
            self.assertAlmostEqual(d["arm_mean_utility"]["O"][variant], .2)
            self.assertAlmostEqual(d["arm_mean_utility"]["P"][variant], .6)
            self.assertAlmostEqual(d["arm_mean_utility"]["S"][variant], .4)
            p = d["paired_differences"]["pointer_minus_off"][variant]
            self.assertAlmostEqual(p["mean"], .4)
            self.assertEqual(p["paired_count"], 3 * len(A.FIXTURES))
            self.assertEqual(set(p["by_seed"]), {"20", "21", "22"})
            self.assertAlmostEqual(
                d["paired_differences"]["pointer_minus_shared_body"][variant]["mean"], .2)
            self.assertAlmostEqual(
                d["paired_differences"]["shared_body_minus_off"][variant]["mean"], .2)

    def test_missing_arm_or_frozen_fixture_refused(self):
        m = matrix()
        m.pop(("S", 22))
        with self.assertRaisesRegex(ValueError, "NINE_ARM"):
            A.aggregate(m)
        m = matrix()
        m[("S", 22)].pop(next(iter(A.EXPECTED)))
        with self.assertRaisesRegex(ValueError, "FROZEN_UTILITY_KEYS"):
            A.aggregate(m)

    def test_nonfinite_out_of_range_and_boolean_utility_refused(self):
        key = next(iter(A.EXPECTED))
        for value in (math.nan, math.inf, -0.01, 1.01, True, "0.5"):
            with self.subTest(value=value):
                m = matrix()
                m[("P", 20)][key] = value
                with self.assertRaisesRegex(ValueError, "UTILITY_NOT_FINITE"):
                    A.aggregate(m)

    def test_independent_verifier_refusal_never_yields_utility(self):
        with patch.object(A.verified378, "verify",
                          side_effect=ValueError("RECEIPT_RED")):
            with self.assertRaisesRegex(ValueError, "RECEIPT_RED"):
                A.analyze("/no-native-work", {})
        with patch.object(A.verified378, "verify",
                          return_value={"status": "RED", "rows_verified": 0}):
            with self.assertRaisesRegex(ValueError, "INDEPENDENT_378_NOT_VERIFIED"):
                A.analyze("/no-native-work", {})


if __name__ == "__main__":
    unittest.main()
