"""Run426 synthetic paired-math checks; actual native rows are verified separately in CI."""
import copy
import math
import unittest

from scripts import run426_native126_paired as D


def complete():
    return {arm: {key: value for key in D.EXPECTED}
            for arm, value in (("O", 0.2), ("P", 0.8), ("S", 0.6))}


class Run426PairedMathTests(unittest.TestCase):
    def test_same_task_complete_paired_math(self):
        r = D.aggregate(complete())
        self.assertEqual(r["same_task_pairs_per_comparison"], 42)
        self.assertEqual(r["seed_count"], 1)
        self.assertEqual(r["seed"], 20)
        for variant in D.VARIANTS:
            self.assertAlmostEqual(r["arm_mean_utility"]["P"][variant], 0.8)
            po = r["paired_differences"]["pointer_minus_off"][variant]
            ps = r["paired_differences"]["pointer_minus_shared_body"][variant]
            self.assertAlmostEqual(po["mean"], 0.6)
            self.assertAlmostEqual(ps["mean"], 0.2)
            self.assertEqual((po["positive"], po["negative"], po["ties"]), (6, 0, 0))
            self.assertEqual((ps["positive"], ps["negative"], ps["ties"]), (6, 0, 0))

    def test_mixed_sign_and_tie_count_without_fake_positive(self):
        arms = complete()
        v = D.VARIANTS[0]
        f = D.FIXTURES
        arms["P"][(f[0], v)] = arms["O"][(f[0], v)]
        arms["P"][(f[1], v)] = 0.1
        r = D.aggregate(arms)
        d = r["paired_differences"]["pointer_minus_off"][v]
        self.assertEqual((d["positive"], d["negative"], d["ties"]), (4, 1, 1))
        self.assertEqual(d["paired_count"], 6)

    def test_missing_extra_and_wrong_arm_refused(self):
        for mutant in (
            lambda a: a["P"].pop(next(iter(D.EXPECTED))),
            lambda a: a["O"].__setitem__(("extra", "variant"), 0.4),
            lambda a: a.pop("S"),
        ):
            a = complete()
            mutant(a)
            with self.assertRaises(ValueError):
                D.aggregate(a)

    def test_nonfinite_bool_and_out_of_range_refused(self):
        for invalid in (float("nan"), float("inf"), -0.1, 1.01, True):
            a = complete()
            a["P"][next(iter(D.EXPECTED))] = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    D.aggregate(a)


if __name__ == "__main__":
    unittest.main()
