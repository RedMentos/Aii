"""Preregistered bounded shuffled-target negative control; stdlib-only fake RNG."""
import unittest

from v13.body_jepa import derangement


class SequenceRNG:
    def __init__(self, *rows):
        self.rows = list(rows)
        self.calls = 0

    def permutation(self, n):
        self.calls += 1
        if self.calls > len(self.rows):
            raise AssertionError("UNBOUNDED_RNG_CALL")
        return self.rows[self.calls - 1]


class BodyJepaDerangementBoundTests(unittest.TestCase):
    def test_exhausted_identity_rng_fails_closed_with_bounded_calls(self):
        rng = SequenceRNG(*([list(range(3))] * 64))
        with self.assertRaisesRegex(ValueError, "derangement attempts exhausted"):
            derangement(3, rng)
        self.assertEqual(rng.calls, 64)

    def test_malformed_no_fixed_point_permutation_rejected(self):
        rng = SequenceRNG([1, 2, 1])
        with self.assertRaisesRegex(ValueError, "invalid RNG permutation"):
            derangement(3, rng)
        self.assertEqual(rng.calls, 1)

    def test_successful_second_draw_keeps_original_rng_sequence(self):
        rng = SequenceRNG([0, 1, 2], [1, 2, 0])
        self.assertEqual(derangement(3, rng), [1, 2, 0])
        self.assertEqual(rng.calls, 2)

    def test_valid_first_draw_and_too_small_input(self):
        rng = SequenceRNG([1, 0])
        self.assertEqual(derangement(2, rng), [1, 0])
        self.assertEqual(rng.calls, 1)
        with self.assertRaises(ValueError):
            derangement(1, rng)


if __name__ == "__main__":
    unittest.main()
