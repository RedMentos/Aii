"""Context OS equation relations stay RAW; scientific numbers pin atomically.

Software-only regression, no models or Age0 ACTIVE promotion.
"""
import unittest

from v13 import context_os as C

TAIL = "Unrelated older discussion about the garden and the weather. " * 9


class ContextOSMathExactTests(unittest.TestCase):
    def test_arithmetic_relation_not_reduced_to_unordered_operands(self):
        for equation in (
                "487 - 318 = 169",
                "100 + 50 = 150",
                "2×3=6",
                "3 ÷ 2 = 1.5",
                "5 / 10 = 0.5",
                "A=2",
                "100 <= 200",
                "10 ≥ 3",
                "2 − 1 = 1"):
            with self.subTest(equation=equation):
                text = "Intro about the weather. Later the relation was " + equation + ". " + TAIL
                out, spans, ok = C.compress(text, 140)
                self.assertFalse(ok)
                self.assertEqual(out, text)
                self.assertIn(equation, out)

    def test_scientific_exponent_is_one_exact_span(self):
        for number in ("1.23e-5", "-2E+6", ".5e-3"):
            with self.subTest(number=number):
                text = "Intro about weather. The measured value was " + number + ". " + TAIL
                out, spans, ok = C.compress(text, 140)
                self.assertIn(number, spans)
                self.assertIn(number, out)
                self.assertTrue(ok or out == text)

    def test_iso_date_does_not_trigger_arithmetic_guard(self):
        text = "The invoice date was 2026-10-09. " + TAIL
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertIn("2026-10-09", spans)
        self.assertIn("2026-10-09", out)

    def test_unspaced_numeric_range_remains_exact(self):
        text = "The allowed range is 2-3 days. " + TAIL
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertIn("2-3", spans)
        self.assertIn("2-3", out)

    def test_pinned_inline_code_math_does_not_force_raw(self):
        text = "Intro about weather. The exact code was `2+2=4`. " + TAIL
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertIn("`2+2=4`", spans)
        self.assertIn("`2+2=4`", out)

    def test_unrelated_long_text_still_compresses(self):
        text = "Intro about weather. " + TAIL
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertLess(len(out), len(text))

    def test_math_guard_does_not_modify_age0_defaults(self):
        st = C.empty()
        self.assertEqual(st["mode"], "SHADOW")
        self.assertEqual(st["learned"], "SHADOW")
        self.assertEqual(st["layout"], "append_only")


if __name__ == "__main__":
    unittest.main()
