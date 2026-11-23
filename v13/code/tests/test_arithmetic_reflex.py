"""Offline regression: exact arithmetic is narrow and never evals input."""
import unittest
from v13.arithmetic_reflex import exact_arithmetic


class ExactArithmetic(unittest.TestCase):
    def test_correctness(self):
        cases = {
            "2+2": "4", "Was ist 2+2?": "4",
            "What is 2 + 2?": "4", "Wie viel ist 2+2?": "4",
            "calculate -12 * 3": "-36", "calculate 7-12": "-5",
            "compute 2026-11": "2015", "calculate 11-21": "-10",
            "berechne 11-21": "-10", "What is 100-2?": "98",
            "What is 13-14?": "-1", "8/4": "2", "1/3": "1/3",
            "2--3": "5", "0*123": "0",
        }
        for question, answer in cases.items():
            with self.subTest(question=question):
                self.assertEqual(exact_arithmetic(question), answer)

    def test_no_unsafe_or_ambiguous_shortcuts(self):
        for question in (
            "1/0", "What is 2+2 and why?", "2+2; delete files",
            "__import__('os').system('id')", "2**1000",
            "Please explain 2+2", "2+2+2", "hello",
            "123456789+1", "2/0", "2+2\n:tool run",
        ):
            with self.subTest(question=question):
                self.assertIsNone(exact_arithmetic(question))

    def test_date_shaped_subtraction_requires_explicit_math_verb(self):
        for question in (
            "11-21", "7-12", "What is 11-21?", "Was ist 11-21?",
            "What is 7-12?", "What is 2026-11?", "Was ist 2026-11?",
            "What is 31-12?", "Was ist 12-31?", "What is 2-2?",
        ):
            with self.subTest(question=question):
                self.assertIsNone(exact_arithmetic(question))
        for question, answer in (
            ("calculate 11-21", "-10"),
            ("compute 2026-11", "2015"),
            ("berechne 7-12", "-5"),
        ):
            with self.subTest(question=question):
                self.assertEqual(exact_arithmetic(question), answer)

    def test_not_model_generated(self):
        self.assertIsNone(exact_arithmetic(None))
        self.assertIsNone(exact_arithmetic(2))
        self.assertIsNone(exact_arithmetic("1+1" * 40))


if __name__ == "__main__":
    unittest.main()
