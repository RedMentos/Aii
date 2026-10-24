"""Run100: incomplete fenced code must never be summarized away by Context OS.
Preregistered deterministic software proof; no native models or mode promotion.
"""
import unittest

from v13 import context_os as C

FILL = "Long ordinary background that can safely be compressed. " * 20


class ContextUnclosedFenceRun100(unittest.TestCase):
    def test_late_unclosed_python_fence_stays_raw(self):
        original = ("Opening sentence. " + FILL +
                    "\n```python\ndef recover_archived_fact():\n    return stored_source_reference\n" +
                    FILL)
        out, spans, ok = C.compress(original, 80)
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_unclosed_fence_with_numbers_stays_raw_not_numeric_only(self):
        original = ("Opening sentence. " + FILL +
                    "\n```python\nproof = source_lookup(12345)\n" + FILL)
        out, spans, ok = C.compress(original, 80)
        self.assertFalse(ok)
        self.assertEqual(out, original)

    def test_closed_fence_still_compresses_and_keeps_code(self):
        code = "```python\nprint('exact_source')\n```"
        original = "Opening sentence. " + FILL + code + FILL
        out, spans, ok = C.compress(original, 80)
        self.assertTrue(ok)
        self.assertIn(code, spans)
        self.assertIn(code, out)
        self.assertNotEqual(out, original)

    def test_two_closed_fences_still_compress(self):
        code1 = "```python\nalpha = source_value\n```"
        code2 = "```sql\nSELECT name FROM events;\n```"
        original = "Opening sentence. " + FILL + code1 + FILL + code2 + FILL
        out, spans, ok = C.compress(original, 80)
        self.assertTrue(ok)
        for code in (code1, code2):
            self.assertIn(code, spans)
            self.assertIn(code, out)

    def test_ordinary_prose_still_compresses(self):
        original = "Opening sentence. " + FILL
        out, spans, ok = C.compress(original, 80)
        self.assertTrue(ok)
        self.assertNotEqual(out, original)


if __name__ == "__main__":
    unittest.main()
