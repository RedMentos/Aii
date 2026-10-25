"""Run362: conservative German question-only list_arith recipe detection.

No model inference, no tool permission change. Ambiguous differences/counting
must abstain instead of silently choosing the max-minus-min recipe.
"""
import unittest

from v13.agi import listarith as L


class GermanListArithmeticRun362(unittest.TestCase):
    def test_explicit_german_total_questions(self):
        cases = [
            "Apfel: 4 Euro. Birne: 9 Euro. Wie viel ist das zusammen?",
            "A: 4. B: 9. Wie hoch ist die Summe?",
            "A: 4. B: 9. Was ist der Gesamtbetrag?",
            "A: 4. B: 9. Addiere die beiden Beträge.",
            "A: 4. B: 9. Wie viel kostet alles insgesamt?",
            "A: 4. B: 9. Was kosten die beiden Posten zusammen?",
            "A: 4. B: 9. Wie viele Euro sind das insgesamt?",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(L.operation(text), "total")

    def test_explicit_german_max_minus_min_questions(self):
        cases = [
            "A: 4. B: 9. Wie groß ist die Differenz zwischen dem höchsten und niedrigsten Wert?",
            "A: 4. B: 9. Wie viel mehr hat der größte Posten als der kleinste?",
            "A: 4. B: 9. Wie weit liegen der höchste und der niedrigste Betrag auseinander?",
            "A: 4. B: 9. Was ist der Abstand zwischen Maximum und Minimum?",
            "A: 4. B: 9. Wie groß ist der Unterschied zwischen dem größten und kleinsten Betrag?",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(L.operation(text), "difference_max_min")

    def test_german_counting_and_ambiguous_questions_abstain(self):
        cases = [
            "A: 4. B: 9. Wie viele Einträge sind es insgesamt?",
            "A: 4. B: 9. Wie viele Posten gibt es zusammen?",
            "A: 4. B: 9. Wie hoch ist die Gesamtanzahl der Positionen?",
            "A: 4. B: 9. Wie viele Zahlen sind das zusammen?",
            "A: 4. B: 9. Wie groß ist der Unterschied zwischen A und B?",
            "A: 4. B: 9. Was ist der Preis?",
            "A: 4. B: 9. Welche zwei Gruppen arbeiten zusammen?",
            "A: 4. B: 9. Wie viele Euro-Beträge sind aufgelistet?",
            "A: 4. B: 9. Wie viele Preisgruppen arbeiten zusammen?",
            "A: 4. B: 9. Wie viele Preisgruppen gibt es insgesamt?",
            "Gesamt: 13 Euro. A: 4. B: 9. Wie viele Zeilen gibt es?",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertIsNone(L.operation(text))

    def test_german_recipe_executes_with_original_source_number_guard(self):
        text = "Apfel: 4 Euro. Birne: 9 Euro. Wie viel kostet alles zusammen?"
        values = [{"name": "Apfel", "number": 4}, {"name": "Birne", "number": 9}]
        self.assertEqual(L.compute(L.operation(text), values, text)[0], 13)
        diff = "Apfel: 4 Euro. Birne: 9 Euro. Wie viel mehr hat der größte als der kleinste?"
        self.assertEqual(L.compute(L.operation(diff), values, diff)[0], 5)
        with self.assertRaisesRegex(ValueError, "number not in"):
            L.compute("total", [{"name": "Apfel", "number": 8}, values[1]], text)

    def test_existing_english_question_only_rules_remain(self):
        self.assertEqual(L.operation("A: 4. B: 9. What is the total?"), "total")
        self.assertIsNone(L.operation("Total: 13. A: 4. B: 9. What is the total number of entries?"))
        self.assertEqual(L.operation("A: 4. B: 9. How many more does the largest have than the smallest?"),
                         "difference_max_min")


    def test_live_toolstep_proposal_is_gated_and_reuses_number_guard_without_model(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from v13.runtime import Runtime
        from v13.agi import hub
        from v13.toolstep import ToolStep
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                text = "Apfel: 4 Euro. Birne: 9 Euro. Wie viel kostet alles zusammen?"
                event = r.store.event(r.session, text)
                values = [{"name": "Apfel", "number": 4}, {"name": "Birne", "number": 9}]
                step = ToolStep(r)
                with patch.object(r.pool, "get", return_value=object()), patch.object(
                        L, "read_values", return_value=values) as read:
                    self.assertIsNone(step._propose_list(event, text),
                                      "disabled tool must not call a model")
                    self.assertEqual(read.call_count, 0)
                    hub(r).tools.enable("list_arith")
                    proposal = step._propose_list(event, text)
                    self.assertIsNotNone(proposal)
                    self.assertEqual(proposal["tool"], "list_arith")
                    self.assertEqual(proposal["args"]["operation"], "total")
                    self.assertEqual(L.tool(**proposal["args"]), 13)
                    self.assertEqual(read.call_count, 1)
                    ambiguous = "A: 4. B: 9. Wie viele Preisgruppen arbeiten zusammen?"
                    event2 = r.store.event(r.session, ambiguous)
                    self.assertIsNone(step._propose_list(event2, ambiguous))
                    self.assertEqual(read.call_count, 1, "ambiguous count must not invoke C3")
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
