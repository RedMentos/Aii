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


    def test_complete_other_literal_protects_its_inner_unpaired_delimiter(self):
        for literal in ('"a single ` inside a complete quote"',
                        '`print("unfinished)`',
                        '„ein ` innerhalb eines ganzen Zitats“'):
            with self.subTest(literal=literal):
                original, (out, spans, ok) = trial(literal)
                self.assertTrue(ok)
                self.assertNotEqual(out, original)
                self.assertIn(literal, spans)
                self.assertIn(literal, out)

    def test_old_unbalanced_source_turn_is_not_silently_compressed_in_plan(self):
        from tests.test_context_exact_pin_run73 import FakeStore, history
        store = FakeStore()
        planner = C.ContextOS(store, {"context_tokens": 4096, "answer_tokens": 128})
        hist = history(n=10, chars=150)
        hist[0]["text"] = "First sentence. " + FILL + "`unclosed literal tail"
        result = planner.plan("new-event", "B1_DETAIL", "SYSTEM", [], hist, "What next?")
        item = next(x for x in result["plan"]["items"] if x["item_id"] == "turn0")
        self.assertEqual(item["form"], "RAW")
        self.assertIn("`unclosed literal tail", result["planned"][1]["content"])


if __name__ == "__main__":
    unittest.main()
