import math
import random
import unittest

from v13.agi import metaeff


def entropy(p):
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


class MetaEffTieInvariance(unittest.TestCase):
    def test_constant_confidence_has_no_information_in_either_order(self):
        pairs = [(0.5, 1)] * 50 + [(0.5, 0)] * 50
        shuffled = pairs.copy()
        random.Random(1).shuffle(shuffled)

        self.assertEqual(metaeff.meta_i(pairs), 0.0)
        self.assertEqual(metaeff.meta_i(shuffled), 0.0)
        result = metaeff.report(pairs, perm=80, boot=40)
        self.assertEqual(result, metaeff.report(shuffled, perm=80, boot=40))
        self.assertEqual(result['perm_p'], 1.0)
        self.assertEqual(result['ci95'], [0.0, 0.0])
        self.assertEqual(result['auroc2'], 0.5)

    def test_shared_values_stay_together_at_quantile_boundaries(self):
        pairs = [(0.1, 0)] * 3 + [(0.5, 0)] + [(0.5, 1)] * 3 + [(0.9, 1)] * 3
        expected = 1.0 - (4.0 / 10.0) * entropy(3.0 / 4.0) / entropy(6.0 / 10.0)
        baseline = metaeff.report(pairs, bins=3, perm=80, boot=40, seed=3)
        self.assertAlmostEqual(metaeff.meta_i(pairs, bins=3), expected)
        for seed in range(10):
            shuffled = pairs.copy()
            random.Random(seed).shuffle(shuffled)
            self.assertAlmostEqual(metaeff.meta_i(shuffled, bins=3), expected)
            self.assertEqual(metaeff.report(shuffled, bins=3, perm=80, boot=40, seed=3), baseline)

    def test_unique_values_keep_the_previous_equal_count_boundaries(self):
        labels = [0, 0, 1, 0, 1, 1, 1, 1, 1, 0]
        pairs = [((i + 0.5) / 10, y) for i, y in enumerate(labels)]
        expected = 1.0 - (0.3 * entropy(1 / 3) + 0.3 * entropy(2 / 3) + 0.4 * entropy(3 / 4)) / entropy(0.6)
        self.assertAlmostEqual(metaeff.meta_i(pairs, bins=3), expected)

    def test_undefined_confidence_and_nonbinary_outcome_are_rejected(self):
        for confidence in (float('nan'), float('inf'), -0.01, 1.01):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                metaeff.meta_i([(confidence, 1), (0.5, 0)])
        with self.assertRaises(ValueError):
            metaeff.meta_i([(0.5, 2), (0.7, 0)])


if __name__ == '__main__':
    unittest.main()
