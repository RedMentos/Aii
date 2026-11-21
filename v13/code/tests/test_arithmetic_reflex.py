"""Offline regression: exact arithmetic is narrow and never evals input."""
import unittest
from v13.arithmetic_reflex import exact_arithmetic


class ExactArithmetic(unittest.TestCase):
    def test_correctness(self):
        cases = {
            "2+2": "4", "Was ist 2+2?": "4",
            "What is 2 + 2?": "4", "calculate -12 * 3": "-36",
            "8/4": "2", "1/3": "1/3", "calculate 7-12": "-5",
            "What is 11-21?": "-10", "2--3": "5", "0*123": "0",
        }
        for question, answer in cases.items():
            with self.subTest(question=question):
                self.assertEqual(exact_arithmetic(question), answer)

    def test_date_shaped_subtraction_requires_explicit_math_cue(self):
        for question in ("2026-11", "2026 - 11", "11-21", "12-24", "7-12"):
            with self.subTest(question=question):
                self.assertIsNone(exact_arithmetic(question))
        self.assertEqual(exact_arithmetic("calculate 2026 - 11"), "2015")
        self.assertEqual(exact_arithmetic("What is 11-21?"), "-10")

    def test_no_unsafe_or_ambiguous_shortcuts(self):
        for question in (
            "1/0", "What is 2+2 and why?", "2+2; delete files",
            "__import__('os').system('id')", "2**1000",
            "Please explain 2+2", "2+2+2", "hello",
            "123456789+1", "2/0", "2+2\n:tool run",
        ):
            with self.subTest(question=question):
                self.assertIsNone(exact_arithmetic(question))

    def test_not_model_generated(self):
        self.assertIsNone(exact_arithmetic(None))
        self.assertIsNone(exact_arithmetic(2))
        self.assertIsNone(exact_arithmetic("1+1" * 40))


if __name__ == "__main__":
    unittest.main()
