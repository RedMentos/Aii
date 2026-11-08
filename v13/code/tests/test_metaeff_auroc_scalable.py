"""Independent quadratic reference for BP6 type-2 AUROC candidate."""
import random
import unittest

from v13.agi.metaeff import auroc2, report


def quadratic_reference(pairs):
    positive = [c for c, y in pairs if y == 1]
    negative = [c for c, y in pairs if y == 0]
    if not positive or not negative:
        return None
    return sum((p > q) + 0.5 * (p == q) for p in positive for q in negative) / (
        len(positive) * len(negative)
    )


class TestMetaEffAurocScalable(unittest.TestCase):
    def test_reference_random_and_ties(self):
        rng = random.Random(117)
        for size in (2, 3, 7, 31, 150):
            for trial in range(20):
                pairs = [(rng.randrange(5) / 4, rng.randrange(2)) for _ in range(size)]
                with self.subTest(size=size, trial=trial):
                    expected = quadratic_reference(pairs)
                    actual = auroc2(pairs)
                    if expected is None:
                        self.assertIsNone(actual)
                    else:
                        self.assertAlmostEqual(actual, expected, places=12)

    def test_all_equal_and_extremes(self):
        self.assertEqual(auroc2([(0.5, 1)] * 200 + [(0.5, 0)] * 200), 0.5)
        self.assertEqual(auroc2([(1, 1), (0, 0)]), 1.0)
        self.assertEqual(auroc2([(0, 1), (1, 0)]), 0.0)
        self.assertIsNone(auroc2([]))
        self.assertIsNone(auroc2([(0.5, 1)]))

    def test_invalid_pairs_fail_closed(self):
        for pairs in ([(float('nan'), 1), (0.5, 0)],
                      [(1.1, 1), (0.5, 0)],
                      [(0.1, 2), (0.5, 0)]):
            with self.subTest(pairs=pairs), self.assertRaises(ValueError):
                auroc2(pairs)

    def test_report_preserves_auroc(self):
        pairs = [(0.1, 0), (0.1, 1), (0.5, 1), (0.5, 0), (0.9, 1)]
        self.assertEqual(report(pairs, perm=5, boot=5)['auroc2'],
                         round(quadratic_reference(pairs), 4))


if __name__ == '__main__':
    unittest.main()
