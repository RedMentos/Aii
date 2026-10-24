"""Run93 Context OS must preserve paired quoted source spans exactly.

Pure deterministic software, no models, no ContextOS ACTIVE promotion.
"""
import unittest

from v13 import context_os as C


FILL = "Ordinary background text without special exact markers. " * 18


def compress_with_late_quote(quote):
    text = "Opening sentence. " + FILL + quote + " " + FILL
    return text, C.compress(text, 80)


class ContextExactQuotesRun93(unittest.TestCase):
    def test_english_curly_double_quote_survives_compression(self):
        quote = "“the river is silver”"
        original, (out, spans, ok) = compress_with_late_quote(quote)
        self.assertTrue(ok)
        self.assertIn(quote, spans)
        self.assertIn(quote, out)
        self.assertNotEqual(out, original)

    def test_long_ascii_and_german_quotes_survive(self):
        for opener, closer in (('"', '"'), ("„", "“")):
            with self.subTest(opener=opener):
                quote = opener + "x" * 130 + closer
                original, (out, spans, ok) = compress_with_late_quote(quote)
                self.assertTrue(ok)
                self.assertIn(quote, spans)
                self.assertIn(quote, out)
                self.assertLess(len(out), len(original))

    def test_oversized_quote_forces_raw_not_lossy_compression(self):
        quote = "“" + "x" * (C.SPAN_CHARS + 1) + "”"
        original, (out, spans, ok) = compress_with_late_quote(quote)
        self.assertIn(quote, spans)
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_existing_short_ascii_and_german_quotes_remain_exact(self):
        for quote in ('"tiny phrase"', "„kleiner Satz“"):
            with self.subTest(quote=quote):
                original, (out, spans, ok) = compress_with_late_quote(quote)
                self.assertTrue(ok)
                self.assertIn(quote, spans)
                self.assertIn(quote, out)
                self.assertNotEqual(out, original)


if __name__ == "__main__":
    unittest.main()
