"""Preregistered typographic exact-literal Context OS regression; software only."""
import unittest

from v13 import context_os as C

TAIL = "We discussed the garden and weather in unrelated detail. " * 12


class ContextOSTypographicQuotesRun11I(unittest.TestCase):
    def text(self, literal):
        return ("Intro about weather. The exact earlier instruction was "
                + literal + " and it matters. " + TAIL)

    def assert_pinned_compressed(self, literal):
        text = self.text(literal)
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok, "balanced short literal should be compressible")
        self.assertLess(len(out), len(text))
        self.assertIn(literal, spans)
        self.assertIn(literal, out)

    def assert_unclosed_raw(self, literal):
        text = self.text(literal)
        out, _, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)

    def test_balanced_english_curly_double_exact_and_compressed(self):
        self.assert_pinned_compressed("“violet compass”")

    def test_balanced_french_guillemets_exact_and_compressed(self):
        self.assert_pinned_compressed("«violet compass»")

    def test_balanced_curly_single_exact_and_compressed(self):
        self.assert_pinned_compressed("‘violet compass’")

    def test_balanced_curly_single_with_inner_contraction(self):
        self.assert_pinned_compressed("‘don’t forget’")

    def test_unclosed_french_quote_remains_raw(self):
        self.assert_unclosed_raw("«unclosed literal")

    def test_unclosed_curly_single_quote_remains_raw(self):
        self.assert_unclosed_raw("‘unclosed literal")

    def test_unclosed_english_curly_double_remains_raw(self):
        self.assert_unclosed_raw("“unclosed literal")

    def test_intra_word_typographic_apostrophe_not_delimiter(self):
        text = self.text("John doesn’t know and we won’t ask")
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertLess(len(out), len(text))
        self.assertFalse(any("’" in s for s in spans))

    def test_original_german_low_double_quote_unchanged(self):
        self.assert_pinned_compressed("„violet compass“")


if __name__ == "__main__":
    unittest.main()
