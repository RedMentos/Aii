"""Run363: strict local row extraction can avoid a C3 wake for unambiguous list arithmetic.

Source-only Runtime/SQLite with mocked C3. The fast arm is only a proposer;
existing user enable, prohibition, Age and approval gates remain in force.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.agi import hub, listarith as L
from v13.toolstep import ToolStep


class ExactRowsRun363(unittest.TestCase):
    def test_strict_rows_and_summary_not_counted(self):
        text = "Apfel: 4 Euro. Birne: 9 Euro. Gesamt: 13 Euro. Wie viel kostet alles zusammen?"
        values = L.parse_explicit_rows(text)
        self.assertEqual(values, [{"name": "Apfel", "number": 4},
                                  {"name": "Birne", "number": 9}])
        self.assertEqual(L.compute(L.operation(text), values, text)[0], 13)

    def test_strict_signed_rows_and_source_guard(self):
        text = "A: -4. B: 9. Wie viel ist das zusammen?"
        values = L.parse_explicit_rows(text)
        self.assertEqual(values, [{"name": "A", "number": -4}, {"name": "B", "number": 9}])
        self.assertEqual(L.compute(L.operation(text), values, text)[0], 5)

    def test_ambiguous_or_inexact_rows_do_not_silently_coerce(self):
        cases = [
            "A: 4,5 Euro. B: 9 Euro. Wie viel ist das zusammen?",
            "A: 4, B: 9. Wie viel ist das zusammen?",
            "A: 4. A: 9. Wie viel ist das zusammen?",
            "A: 4. B: 9. 999. Wie viel ist das zusammen?",
            "A: 04. B: 9. Wie viel ist das zusammen?",
            "A: 4. Wie viel ist das zusammen?",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertIsNone(L.parse_explicit_rows(text))

    def test_gated_toolstep_exact_rows_never_wakes_c3(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                text = "Apfel: 4 Euro. Birne: 9 Euro. Wie viel kostet alles zusammen?"
                event = r.store.event(r.session, text)
                step = ToolStep(r)
                with patch.object(r.pool, "get", side_effect=AssertionError("C3 woke")), patch.object(
                        L, "read_values", side_effect=AssertionError("model read")):
                    self.assertIsNone(step._propose_list(event, text),
                                      "disabled tool must not parse or wake a model")
                    hub(r).tools.enable("list_arith")
                    p = step._propose_list(event, text)
                    self.assertIsNotNone(p)
                    self.assertEqual(p["tool"], "list_arith")
                    self.assertEqual(L.tool(**p["args"]), 13)
            finally:
                r.close()

    def test_ambiguous_input_still_uses_existing_c3_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                hub(r).tools.enable("list_arith")
                text = "A: 4, B: 9. Wie viel ist das zusammen?"
                event = r.store.event(r.session, text)
                with patch.object(r.pool, "get", return_value=object()), patch.object(
                        L, "read_values", return_value=[{"name": "A", "number": 4},
                                                        {"name": "B", "number": 9}]) as read:
                    p = ToolStep(r)._propose_list(event, text)
                    self.assertIsNotNone(p)
                    self.assertEqual(L.tool(**p["args"]), 13)
                    self.assertEqual(read.call_count, 1)
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
