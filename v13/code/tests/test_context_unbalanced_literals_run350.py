"""Run350 RED-first: Context OS may not silently compress unbalanced
literal/code delimiters. Pure deterministic source-only tests, no models.
"""
import unittest
from v13 import context_os as C

FILL = "Ordinary background text with no literal markers. " * 20


def trial(tail):
    text = "Opening sentence. " + FILL + tail + " " + FILL
    return text, C.compress(text, 80)


class ContextUnbalancedLiteralsRun350(unittest.TestCase):
    def test_unclosed_inline_backtick_stays_raw(self):
        original, (out, spans, ok) = trial("`unclosed source code")
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_unclosed_ascii_double_quote_stays_raw(self):
        original, (out, spans, ok) = trial('"unclosed literal quote')
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_unclosed_german_and_curly_quotes_stay_raw(self):
        for tail in ("„unclosed German quote", "“unclosed curly quote",
                     "orphan closing quote”"):
            with self.subTest(tail=tail):
                original, (out, spans, ok) = trial(tail)
                self.assertFalse(ok)
                self.assertEqual(out, original)

    def test_balanced_literal_spans_remain_compressible_and_exact(self):
        for literal in ('`pip install foo`', '```python\\nprint(1)\\n```',
                        '"the exact quote"', '„genaues Zitat“',
                        '“the exact phrase”'):
            with self.subTest(literal=literal):
                original, (out, spans, ok) = trial(literal)
                self.assertTrue(ok)
                self.assertNotEqual(out, original)
                self.assertIn(literal, spans)
                self.assertIn(literal, out)

    def test_unclosed_fenced_code_existing_raw_guard_still_holds(self):
        original, (out, spans, ok) = trial("```python\\nprint('incomplete')")
        self.assertFalse(ok)
        self.assertEqual(out, original)


if __name__ == "__main__":
    unittest.main()
