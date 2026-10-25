"""Run377 RED-first: signed one-digit source spans survive Context OS compression."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import context_os as C


LONG = "The conversation continued about gardens and weather. " * 20


class SignedSingleDigitRun377(unittest.TestCase):
    def test_exact_spans_include_sign_and_suffix(self):
        for token in ("-4", "+5", "-4%", "+5kg", "-0", "+9%"):
            with self.subTest(token=token):
                self.assertIn(token, C.exact_spans("The exact change was " + token + " today."))

    def test_compressed_derived_view_keeps_signed_one_digit_literals(self):
        text = "We discussed background first. " + LONG + " The measured change was -4 and the boost was +5kg."
        derived, spans, ok = C.compress(text, 140)
        self.assertTrue(ok)
        self.assertIn("-4", spans)
        self.assertIn("+5kg", spans)
        self.assertIn("-4", derived)
        self.assertIn("+5kg", derived)
        self.assertLess(len(derived), len(text))

    def test_existing_multidigit_decimal_date_and_code_protection(self):
        text = "The total was -12 and -0.5 on 2026-10-25. Run `print(7)` and read https://example.org/a."
        spans = C.exact_spans(text)
        for token in ("-12", "-0.5", "2026-10-25", "`print(7)`", "https://example.org/a"):
            self.assertIn(token, spans)

    def test_actual_sqlite_context_plan_preserves_sign_in_old_compressed_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                ctx = C.ContextOS(r.store, r.cfg)
                old = "A long background sentence. " + LONG + " Later the delta was -4 and the boost +5kg."
                history = []
                for i in range(10):
                    u = old if i == 0 else "A question about flowers. " + LONG
                    a = "An answer about the weather. " + LONG
                    history.extend((
                        {"event_id": f"ev{i}", "role": "user", "text": u},
                        {"event_id": f"ev{i}", "role": "assistant", "text": a},
                    ))
                event_id = r.store.event(r.session, "continue")["event_id"]
                result = ctx.plan(event_id, "C3_LANGUAGE", "SYS", [], history, "continue")
                item = next(x for x in result["plan"]["items"] if x["item_id"] == "ev0")
                self.assertEqual(item["form"], "COMPRESSED")
                self.assertIn("-4", result["planned"][1]["content"])
                self.assertIn("+5kg", result["planned"][1]["content"])
                self.assertEqual(result["legacy"][1]["content"], old)
                self.assertEqual(result["messages"], result["legacy"])
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
