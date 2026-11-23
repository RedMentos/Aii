"""Run12E source-only escaped ASCII quote Context OS candidate regressions."""
import unittest

from v13 import context_os as C
from v13 import context_os_escaped_ascii_shadow_run12e as S

TAIL = "We discussed the garden and weather in unrelated detail. " * 15


class EscapedAsciiQuoteShadowRun12E(unittest.TestCase):
    def test_escaped_inner_quote_stays_exact_raw(self):
        literal = '"use \\"blue\\" key"'
        text = "Intro. The original instruction was " + literal + ". " + TAIL
        result = S.compress_shadow(text, 140)
        self.assertFalse(result["ok"])
        self.assertEqual(result["text"], text)
        self.assertEqual(result["reason"], "ESCAPED_ASCII_QUOTE_RAW")
        self.assertEqual(result["authority"], "SHADOW_ONLY_NO_RUNTIME_CONSUMER")
        self.assertEqual(len(result["escaped_quote_offsets"]), 2)

    def test_escaped_quotes_outside_pairs_fail_closed(self):
        text = 'An ambiguous \\" delimiter appears here. ' + TAIL
        result = S.compress_shadow(text, 140)
        self.assertFalse(result["ok"])
        self.assertEqual(result["text"], text)

    def test_even_backslashes_do_not_trigger_escape_guard(self):
        text = 'The exact path is \\\\"normal\\\\". ' + TAIL
        self.assertEqual(S.escaped_ascii_quote_offsets(text), ())
        result = S.compress_shadow(text, 140)
        self.assertEqual(result["reason"], "DELEGATED_UNCHANGED")
        self.assertEqual(result["text"], C.compress(text, 140)[0])

    def test_odd_three_backslashes_trigger_guard(self):
        text = 'An odd sequence \\\\\\" quoted text. ' + TAIL
        self.assertEqual(len(S.escaped_ascii_quote_offsets(text)), 1)
        self.assertFalse(S.compress_shadow(text, 140)["ok"])

    def test_plain_balanced_quotes_delegate_byte_exact(self):
        text = 'Intro. Earlier rule was "violet compass". ' + TAIL
        old = C.compress(text, 140)
        result = S.compress_shadow(text, 140)
        self.assertEqual((result["text"], result["spans"], result["ok"]), old)
        self.assertTrue(result["ok"])
        self.assertIn('"violet compass"', result["text"])

    def test_typographic_quotes_delegate_unchanged(self):
        text = 'Intro. Earlier rule was „violet compass“. ' + TAIL
        old = C.compress(text, 140)
        result = S.compress_shadow(text, 140)
        self.assertEqual((result["text"], result["spans"], result["ok"]), old)

    def test_unclosed_code_fence_still_fails_closed_in_delegate(self):
        text = "Intro. ```python\nprint('hi')\n" + TAIL
        result = S.compress_shadow(text, 140)
        self.assertFalse(result["ok"])
        self.assertEqual(result["text"], text)
        self.assertEqual(result["reason"], "DELEGATED_UNCHANGED")

    def test_empty_and_non_string_input(self):
        self.assertEqual(S.escaped_ascii_quote_offsets(""), ())
        self.assertEqual(S.compress_shadow("", 140)["text"], "")
        with self.assertRaisesRegex(TypeError, "TEXT_REQUIRED"):
            S.compress_shadow(None, 140)


if __name__ == "__main__":
    unittest.main()
