"""Context OS single-quoted literals must survive extractive compression."""
import unittest

from v13 import context_os as C

TAIL = ('We also discussed the garden and the weather in detail. ' * 7)


class ContextOSSingleQuoteExact(unittest.TestCase):
    def test_balanced_single_quoted_literal_is_exact_pinned(self):
        text = ("The earlier discussion covered the weather. "
                "Later the exact phrase was 'magenta sparrow' and matters. " + TAIL)
        out, spans, ok = C.compress(text, 140)
        self.assertIn("'magenta sparrow'", spans)
        self.assertIn("'magenta sparrow'", out)
        self.assertTrue(ok or out == text)

    def test_quoted_contraction_is_exact_pinned(self):
        text = ("Intro about the garden. "
                "The literal instruction was 'don't forget' for the next turn. " + TAIL)
        out, spans, ok = C.compress(text, 140)
        self.assertIn("'don't forget'", spans)
        self.assertIn("'don't forget'", out)
        self.assertTrue(ok or out == text)

    def test_unclosed_delimiter_style_quote_stays_raw(self):
        text = "Intro about weather. Then a user started 'unclosed literal. " + TAIL
        out, spans, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)

    def test_oversized_single_quoted_literal_stays_raw(self):
        text = "Intro about weather. Later '" + "Q"*450 + "' must remain exact. " + TAIL
        out, spans, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)

    def test_intra_word_apostrophes_are_not_quote_delimiters(self):
        text = ("Intro about weather. John's colleague doesn't know the answer. "
                "We'll discuss it later. " + TAIL)
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertLess(len(out), len(text))
        self.assertFalse(any("'" in s for s in spans))


if __name__ == '__main__':
    unittest.main()
