"""2026-10-29 independent Context OS exact-code RAW fallback regression (no models)."""
import tempfile
import unittest
from pathlib import Path

from v13 import context_os as C
from v13.runtime import Runtime


LONG = "A long unrelated summary of previous observations and unrelated weather. " * 15
SENTINEL = "source_only_method_should_survive"


class UnclosedCodeCompressionTests(unittest.TestCase):
    def test_unclosed_python_fence_never_silently_compressed(self):
        text = "Intro.\\n```python\\n" + SENTINEL + " = 'opaque'\\n" + LONG
        # Deliberately use actual newlines, not a Markdown source renderer.
        text = text.replace("\\n", "\n")
        out, spans, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)
        self.assertIn(SENTINEL, out)

    def test_unclosed_inline_code_never_silently_compressed(self):
        text = "Intro. A literal `" + SENTINEL + " followed by " + LONG
        out, _, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)

    def test_mixed_closed_inline_then_unclosed_fence_stays_raw(self):
        text = "Intro. The valid `safe` span.\\n```python\\n" + SENTINEL + "\\n" + LONG
        text = text.replace("\\n", "\n")
        out, _, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)

    def test_embedded_fake_fence_close_does_not_truncate(self):
        text = "Intro.\\n```python\\nprint('```')\\n" + SENTINEL + "\\n```\\n" + LONG
        text = text.replace("\\n", "\n")
        out, _, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)

    def test_unicode_unclosed_fence_stays_raw(self):
        text = "Überblick.\\n```python\\nπ = 'geschützt'\\n" + SENTINEL + "\\n" + LONG
        text = text.replace("\\n", "\n")
        out, _, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)

    def test_closed_inline_still_compresses_and_pins(self):
        text = "Intro. The literal `pip install foo` matters. " + LONG
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertIn("`pip install foo`", spans)
        self.assertIn("`pip install foo`", out)

    def test_closed_fence_still_compresses_and_pins(self):
        fence = "```python\nprint('safe')\n```"
        text = "Intro. Here is the exact block:\n" + fence + "\n" + LONG
        out, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertIn(fence, spans)
        self.assertIn(fence, out)

    def test_nonstandard_double_backticks_fail_closed(self):
        text = "Intro. Literal ``complex`` span. " + LONG
        out, _, ok = C.compress(text, 140)
        self.assertFalse(ok)
        self.assertEqual(out, text)


class UnclosedCodePlanTests(unittest.TestCase):
    def test_old_unclosed_code_turn_is_raw_not_false_exact_recall(self):
        with tempfile.TemporaryDirectory() as d:
            r = Runtime(Path(d))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                c = C.ContextOS(r.store, r.cfg)
                old = "Intro.\\n```python\\n" + SENTINEL + " = 7\\n" + LONG
                old = old.replace("\\n", "\n")
                history = [
                    {"event_id": "ev0", "role": "user", "text": old},
                    {"event_id": "ev0", "role": "assistant", "text": "Acknowledged. " + LONG[:200]},
                ]
                for i in range(1, 9):
                    history += [
                        {"event_id": f"ev{i}", "role": "user", "text": "Other subject. " + LONG[:200]},
                        {"event_id": f"ev{i}", "role": "assistant", "text": "Other reply. " + LONG[:200]},
                    ]
                query = "Anything new?"
                e = r.store.event(r.session, query)["event_id"]
                result = c.plan(e, "C3_LANGUAGE", "SYS", [], history, query)
                first = next(x for x in result["plan"]["items"] if x["item_id"] == "ev0")
                self.assertEqual(first["form"], "RAW")
                self.assertTrue(any(SENTINEL in m["content"] for m in result["planned"]))
                self.assertEqual(result["plan"]["mode"], "SHADOW")
                self.assertFalse(result["applied"])
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
