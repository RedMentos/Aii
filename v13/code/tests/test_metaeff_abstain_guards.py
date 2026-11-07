"""BP6 abstention utility fail-closed input controls (software-only)."""
import math
import unittest
from v13.agi.metaeff import abstain_utility


class TestAbstainUtilityInputGuards(unittest.TestCase):
    def setUp(self):
        self.pairs = [(0.2, 0), (0.8, 1)]

    def test_steps_reject_invalid_values(self):
        for value in (0, -1, True, 1.5, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                abstain_utility(self.pairs, steps=value)

    def test_confidence_reject_invalid_values(self):
        for value in (float('nan'), float('inf'), -0.01, 1.01, 'unknown'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                abstain_utility([(value, 0), (0.8, 1)])

    def test_correctness_reject_invalid_values(self):
        with self.assertRaises(ValueError):
            abstain_utility([(0.2, 2), (0.8, 1)])

    def test_costs_reject_nonfinite(self):
        for value in (float('nan'), float('inf'), 'invalid'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    abstain_utility(self.pairs, wrong_cost=value)
                with self.assertRaises(ValueError):
                    abstain_utility(self.pairs, abstain_cost=value)

    def test_valid_case_and_order_independence(self):
        a = abstain_utility(self.pairs, wrong_cost=1, abstain_cost=0.3, steps=20)
        b = abstain_utility(list(reversed(self.pairs)), wrong_cost=1, abstain_cost=0.3, steps=20)
        self.assertEqual(a, b)
        self.assertEqual(a, {'gain': 0.7, 'threshold': 0.25, 'answer_all': 0.0})


if __name__ == '__main__':
    unittest.main()
