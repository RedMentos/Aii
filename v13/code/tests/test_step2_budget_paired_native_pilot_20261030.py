"""Fixed paired STEP2 pilot fixture/scorer software tests, no native models."""
import unittest

from scripts.step2_budget_paired_native_pilot_20261030 import (
    ARMS, B1_CANDIDATE, B2_CANDIDATE, FIXTURES,
    fixture_hash, prompt, score_pair, validate_fixtures,
)


class PairedNativeBudgetPilot(unittest.TestCase):
    def test_fixed_disjoint_fixtures_and_no_answer_leak(self):
        self.assertTrue(validate_fixtures())
        self.assertEqual(len(FIXTURES), 4)
        self.assertEqual(len(ARMS), 3)
        self.assertEqual(len(fixture_hash()), 64)
        self.assertNotIn("50 Euro", B1_CANDIDATE)
        self.assertNotIn("20 Euro", B2_CANDIDATE)
        for f in FIXTURES:
            with self.subTest(project=f["project"]):
                q = prompt(f)
                self.assertIn(f["project"], q)
                self.assertIn("local, no cloud", q)
                self.assertIn("remaining budget", q)

    def test_correct_remainders_score_two_per_fixture(self):
        for f in FIXTURES:
            with self.subTest(project=f["project"]):
                ra = f["budget"] - f["a_cost"]
                rb = f["budget"] - f["b_cost"]
                answer = (f"{f['a']} has {ra} Euro left; "
                          f"{f['b']} has {rb} Euro remaining.")
                self.assertEqual(score_pair(f, answer)["correct"], 2)

    def test_swapped_and_cost_echo_not_credited(self):
        for f in FIXTURES:
            with self.subTest(project=f["project"]):
                ra = f["budget"] - f["a_cost"]
                rb = f["budget"] - f["b_cost"]
                swapped = (f"{f['a']} has {rb} Euro left; "
                           f"{f['b']} has {ra} Euro left.")
                echoed = (f"{f['a']} costs {f['a_cost']} Euro; "
                          f"{f['b']} costs {f['b_cost']} Euro.")
                self.assertEqual(score_pair(f, swapped)["correct"], 0)
                self.assertEqual(score_pair(f, echoed)["correct"], 0)

    def test_one_correct_is_not_two(self):
        f = FIXTURES[0]
        answer = f"{f['a']} has 50 Euro left. {f['b']} costs 125 Euro."
        self.assertEqual(score_pair(f, answer)["correct"], 1)


if __name__ == "__main__":
    unittest.main()
