"""Body-JEPA shuffled-target control must never coerce fake RNG values."""
import unittest

from v13.body_jepa import derangement


class OneDrawRNG:
    def __init__(self, values):
        self.values = values
        self.calls = 0

    def permutation(self, n):
        self.calls += 1
        if self.calls != 1:
            raise AssertionError("unexpected second RNG draw")
        return self.values


class BodyJepaIntegerPermutationTests(unittest.TestCase):
    def test_fractional_float_cannot_be_truncated_into_derangement(self):
        rng = OneDrawRNG([1.9, 2.9, 0.9])
        with self.assertRaisesRegex(ValueError, "invalid RNG permutation"):
            derangement(3, rng)
        self.assertEqual(rng.calls, 1)

    def test_numeric_string_cannot_be_coerced_into_derangement(self):
        rng = OneDrawRNG(["1", 2, 0])
        with self.assertRaisesRegex(ValueError, "invalid RNG permutation"):
            derangement(3, rng)
        self.assertEqual(rng.calls, 1)

    def test_boolean_cannot_be_coerced_into_derangement(self):
        rng = OneDrawRNG([True, 2, 0])
        with self.assertRaisesRegex(ValueError, "invalid RNG permutation"):
            derangement(3, rng)
        self.assertEqual(rng.calls, 1)

    def test_real_numpy_integer_scalars_are_accepted(self):
        import numpy as np
        rng = OneDrawRNG(np.array([1, 2, 0], dtype=np.int64))
        self.assertEqual(derangement(3, rng), [1, 2, 0])
        self.assertEqual(rng.calls, 1)

    def test_valid_python_integer_sequence_unchanged(self):
        rng = OneDrawRNG([1, 2, 0])
        self.assertEqual(derangement(3, rng), [1, 2, 0])
        self.assertEqual(rng.calls, 1)


if __name__ == "__main__":
    unittest.main()
