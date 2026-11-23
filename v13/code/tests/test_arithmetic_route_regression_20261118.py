"""Regression for subtraction/signed arithmetic routing; no native model claims."""
import unittest
from v13.cognition import scaffold_route

class ArithmeticRouteTests(unittest.TestCase):
    def test_signed_and_subtraction(self):
        for prompt in ("2-2", "2 - 2", "12-7", "2 + -3", "1.5-0.5", "6/2", "3*4", "2+2"):
            with self.subTest(prompt=prompt):
                self.assertEqual(scaffold_route(prompt), "detail")
    def test_non_arithmetic_unchanged(self):
        self.assertEqual(scaffold_route("hello"), "simple")
        self.assertEqual(scaffold_route("summarize this"), "gist")
        self.assertEqual(scaffold_route("compare these"), "both")

if __name__ == "__main__":
    unittest.main()
