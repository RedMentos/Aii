"""Prospective v1-v2 C2 route feature ablation, no trained-head authority."""
import math
import unittest

import numpy as np

from v13 import route_words as v1
from v13 import route_words_numeric_candidate as v2


def cosine(a, b):
    x = np.asarray(a, float)
    y = np.asarray(b, float)
    d = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(np.dot(x, y) / d) if d else 0.


class RouteNumericCandidateTests(unittest.TestCase):
    def test_number_length_and_notation_do_not_change_v2_route_features(self):
        pairs = (
            ("How much is half of 7?", "How much is half of 7000?"),
            ("The reading is 1.23e-5 kg", "The reading is 8000 kg"),
            ("Rate 1,000%", "Rate 99%"),
            ("A2 route 9", "A777 route 8888"),
            ("2 + 3", "123456 + 7"),
            ("2026-10-09", "1999-12-31"),
            ("Result .5e-3", "Result 99.99"),
        )
        for a, b in pairs:
            with self.subTest(a=a, b=b):
                self.assertEqual(v2.tokens(a), v2.tokens(b))
                self.assertEqual(v2.vector(a), v2.vector(b))
        print("C2_ROUTE_NUMERIC_V2_MATCHED_PAIRS", len(pairs))

    def test_v1_numeric_length_leaks_but_v2_does_not(self):
        a, b = "How much is half of 7?", "How much is half of 7000?"
        self.assertNotEqual(v1.tokens(a), v1.tokens(b))
        self.assertNotEqual(v1.vector(a), v1.vector(b))
        self.assertEqual(v2.vector(a), v2.vector(b))
        print("C2_ROUTE_NUMERIC_COSINE_V1", round(cosine(v1.vector(a), v1.vector(b)), 6))
        print("C2_ROUTE_NUMERIC_COSINE_V2", round(cosine(v2.vector(a), v2.vector(b)), 6))

    def test_task_words_and_operand_count_still_matter(self):
        a = v2.vector("How much is half of 7?")
        b = v2.vector("What color is 7?")
        c = v2.vector("How much is half of 7 and 8?")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertTrue(math.isfinite(cosine(a, b)))
        self.assertTrue(math.isfinite(cosine(a, c)))
        self.assertEqual(v2.tokens("2+3"), ["#", "#"])
        self.assertEqual(v2.tokens("2+3+4"), ["#", "#", "#"])

    def test_determinism_norm_empty_and_revision_separation(self):
        self.assertNotEqual(v1.REVISION, v2.REVISION)
        self.assertEqual(v1.DIM, len(v2.vector("hello")))
        self.assertEqual(v2.vector("hello"), v2.vector("hello"))
        self.assertEqual(v2.tokens(""), [])
        self.assertTrue(all(x == 0 for x in v2.vector("")))
        self.assertAlmostEqual(np.linalg.norm(v2.vector("hello")), v2.SCALE, places=6)


if __name__ == "__main__":
    unittest.main()
