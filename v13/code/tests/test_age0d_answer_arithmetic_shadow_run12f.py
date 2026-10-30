"""Run12F answer-aware Age0d SHADOW arithmetic calibration preflight.

Only synthetic bounded examples; no real-answer false-alarm estimate or delivery.
"""
import unittest

from v13 import age0d_answer_arithmetic_shadow_run12f as a


class AnswerAwareArithmeticRun12F(unittest.TestCase):
    def assert_shadow(self, result):
        self.assertEqual(result["authority"], "SHADOW_ONLY_NO_DELIVERY")
        self.assertFalse(result["delivery_allowed"])
        self.assertFalse(result["learning_allowed"])
        self.assertFalse(result["age_promotion"])
        self.assertFalse(result["whole_answer_verified"])

    def test_correct_explicit_equations(self):
        result = a.inspect("What is arithmetic?", "7 * 3 = 21 and 10 - 4 = 6.")
        self.assertEqual(result["status"], "LOCAL_ARITHMETIC_CONSISTENT")
        self.assertEqual(len(result["evidence"]), 2)
        self.assert_shadow(result)

    def test_wrong_explicit_equation_detected_without_delivery(self):
        result = a.inspect("What is arithmetic?", "7 * 3 = 20.")
        self.assertEqual(result["status"], "POSSIBLE_ARITHMETIC_ERROR_SHADOW")
        self.assertEqual(result["reason"], "EXPLICIT_EQUATION_MISMATCH")
        self.assertEqual(result["evidence"][0]["expected"], "21")
        self.assert_shadow(result)

    def test_question_answer_bare_integer_pair_english_and_german(self):
        for q, answer, status in (
            ("What is 7 * 3?", "21", "LOCAL_ARITHMETIC_CONSISTENT"),
            ("What is 7 * 3?", "20", "POSSIBLE_ARITHMETIC_ERROR_SHADOW"),
            ("Was ist 7 × 3?", "21.", "LOCAL_ARITHMETIC_CONSISTENT"),
            ("Berechne -2 * 3", "-6", "LOCAL_ARITHMETIC_CONSISTENT"),
        ):
            with self.subTest(q=q, answer=answer):
                r = a.inspect(q, answer)
                self.assertEqual(r["status"], status)
                self.assert_shadow(r)

    def test_extra_prose_or_multiple_numbers_abstains(self):
        for answer in ("It is 20.", "20 or 21", "The year 2026 had 12 months", "20 (roughly)"):
            with self.subTest(answer=answer):
                r = a.inspect("What is 7 * 3?", answer)
                self.assertEqual(r["status"], "ABSTAIN")
                self.assert_shadow(r)

    def test_quoted_wrong_examples_and_code_abstain(self):
        for answer in ('"7 * 3 = 20" is wrong', "`7 * 3 = 20` is an example",
                       "‘7 * 3 = 20’ is a quote"):
            with self.subTest(answer=answer):
                r = a.inspect("Please explain", answer)
                self.assert_shadow(r)
                self.assertEqual(r["status"], "ABSTAIN")

    def test_explained_false_equations_are_not_flagged_as_own_errors(self):
        for answer in ("7 * 3 = 20 is wrong, the correct result is 21.",
                       "Counterexample: 2 + 2 = 5",
                       "Das Beispiel 3 * 3 = 8 ist falsch."):
            with self.subTest(answer=answer):
                r = a.inspect("Explain the mistake", answer)
                self.assertEqual(r["status"], "ABSTAIN")
                self.assertEqual(r["reason"], "METALINGUISTIC_EXAMPLE")
                self.assert_shadow(r)

    def test_unsafe_expressions_abstain_without_eval(self):
        for q, answer in (
            ("What is 2 ** 30?", "1073741824"),
            ("What is 7 / 0?", "0"),
            ("What is __import__('os')?", "0"),
            ("What is 999999*999999*999999*999999?", "0"),
        ):
            with self.subTest(q=q):
                r = a.inspect(q, answer)
                self.assertEqual(r["status"], "ABSTAIN")
                self.assert_shadow(r)

    def test_sentence_period_allowed_but_decimal_rhs_not_partially_read(self):
        self.assertEqual(a.inspect("Check", "7 * 3 = 21.")["status"],
                         "LOCAL_ARITHMETIC_CONSISTENT")
        self.assertEqual(a.inspect("Check", "7 * 3 = 20.")["status"],
                         "POSSIBLE_ARITHMETIC_ERROR_SHADOW")
        self.assertEqual(a.inspect("Check", "1 / 2 = 0.5")["status"], "ABSTAIN")

    def test_exact_fraction_arithmetic_no_float_rounding(self):
        self.assertEqual(a.evaluate("1 / 3 + 1 / 3"), a.Fraction(2, 3))
        r = a.inspect("Please verify", "1 / 2 = 0")
        self.assertEqual(r["status"], "POSSIBLE_ARITHMETIC_ERROR_SHADOW")
        self.assertEqual(r["evidence"][0]["expected"], "1/2")

    def test_nontext_oversize_and_non_math_abstain(self):
        for q, ans in ((None, "3"), ("2+2", None), ("What is 7 * 3?", "a"*4097),
                       ("When was the meeting?", "2026-10-30")):
            with self.subTest(q=q):
                r = a.inspect(q, ans)
                self.assertEqual(r["status"], "ABSTAIN")
                self.assert_shadow(r)

    def test_false_positive_controls_dates_prices_and_context(self):
        for q, ans in (
            ("What happened on 2026-10-30?", "We met at 12:30."),
            ("What is 7 * 3?", "A price of 20 EUR was quoted."),
            ("Please quote an incorrect equation", '"2 + 2 = 5"'),
        ):
            with self.subTest(q=q):
                self.assertEqual(a.inspect(q, ans)["status"], "ABSTAIN")

    def test_multiple_equations_one_wrong_remains_shadow(self):
        r = a.inspect("Check these", "2 + 2 = 4, 3 * 3 = 8, 4 + 4 = 8")
        self.assertEqual(r["status"], "POSSIBLE_ARITHMETIC_ERROR_SHADOW")
        self.assertEqual(len(r["evidence"]), 3)
        self.assertEqual(sum(not e["correct"] for e in r["evidence"]), 1)
        self.assert_shadow(r)


if __name__ == "__main__":
    unittest.main()
