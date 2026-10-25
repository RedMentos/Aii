"""Run198: actual ContextOS v1 counterexamples and off-by-default guard candidate."""
import unittest
from scripts import context_inline_guard_run198 as G
from v13 import context_os as C

FILL = 'Ordinary context that can be summarized. ' * 24


class ContextInlineGuard(unittest.TestCase):
    def test_existing_v1_loses_unclosed_late_inline_code(self):
        original = 'Opening sentence. ' + FILL + ' Later `source_ref_important ' + FILL
        out, spans, ok = C.compress(original, 80)
        self.assertTrue(ok)  # RED: original v1 compresses despite unclosed code
        self.assertNotIn('`source_ref_important', out)

    def test_candidate_preserves_unclosed_late_inline_code(self):
        original = 'Opening sentence. ' + FILL + ' Later `source_ref_important ' + FILL
        out, _, ok = G.compress_candidate(original, 80)
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_candidate_preserves_double_backtick_code(self):
        original = 'Opening sentence. ' + FILL + ' ``a ` b`` ' + FILL
        out, _, ok = G.compress_candidate(original, 80)
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_multiline_inline_code_stays_raw(self):
        original = 'Opening sentence. ' + FILL + '`first line\nsecond line`' + FILL
        out, _, ok = G.compress_candidate(original, 80)
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_existing_complete_inline_code_still_compresses(self):
        code = '`source_ref_important`'
        original = 'Opening sentence. ' + FILL + code + FILL
        out, spans, ok = G.compress_candidate(original, 80)
        self.assertTrue(ok)
        self.assertIn(code, spans)
        self.assertIn(code, out)

    def test_existing_closed_fence_with_internal_backtick_unchanged(self):
        code = '```python\nvalue = "`literal"\n```'
        original = 'Opening sentence. ' + FILL + code + FILL
        out, spans, ok = G.compress_candidate(original, 80)
        self.assertTrue(ok)
        self.assertIn(code, spans)
        self.assertIn(code, out)

    def test_unmatched_fence_still_raw(self):
        original = 'Opening sentence. ' + FILL + '```python\nprint(42)' + FILL
        out, _, ok = G.compress_candidate(original, 80)
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_escaped_backtick_does_not_force_raw(self):
        original = 'Opening sentence. ' + FILL + r' escaped \` character ' + FILL
        out, _, ok = G.compress_candidate(original, 80)
        self.assertTrue(ok)
        self.assertNotEqual(out, original)

    def test_ordinary_prose_still_compresses(self):
        original = 'Opening sentence. ' + FILL
        out, _, ok = G.compress_candidate(original, 80)
        self.assertTrue(ok)
        self.assertNotEqual(out, original)


if __name__=='__main__': unittest.main()