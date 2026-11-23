"""Read-only Run52 scorer counterexamples: original frozen metrics NOT replaced."""
import unittest

from scripts import run52_b1b2_cross_turn_native as original
from scripts import run52_b1b2_cross_turn_verify as replay
from scripts.run52_lexical_metric_future_candidate import strict_future_choice_signal as future


class Run52LexicalMetricAudit(unittest.TestCase):
    def test_bare_article_a_is_false_positive_in_both_original_scorers(self):
        oracle = {"choice": "A", "remaining": 30}
        summary = "Option B costs 20, a remaining budget of 30 Euro."
        self.assertEqual(original.b1_signal(summary, oracle), 1)
        self.assertEqual(replay.lexical_b1(summary, oracle), 1)
        self.assertEqual(future(summary, oracle), 0)

    def test_original_number_regex_accepts_decimal_and_negative(self):
        cases = [
            ("Option A leaves 30.5 euros.", {"choice": "A", "remaining": 30}),
            ("Option A leaves -30 euros.", {"choice": "A", "remaining": 30}),
            ("Option B leaves 15.5 euros.", {"choice": "B", "remaining": 15}),
            ("Option B leaves -15 euros.", {"choice": "B", "remaining": 15}),
        ]
        for summary, oracle in cases:
            with self.subTest(summary=summary):
                self.assertEqual(original.b1_signal(summary, oracle), 1)
                self.assertEqual(replay.lexical_b1(summary, oracle), 1)
                self.assertEqual(future(summary, oracle), 0)

    def test_original_none_regex_accepts_explicit_contradiction(self):
        oracle = {"choice": "NONE", "remaining": None}
        summary = "None of the options? Option A qualifies."
        self.assertEqual(original.b1_signal(summary, oracle), 1)
        self.assertEqual(replay.lexical_b1(summary, oracle), 1)
        self.assertEqual(future(summary, oracle), 0)

    def test_conservative_future_metric_accepts_unambiguous_examples(self):
        cases = [
            ("Option A leaves 30 euros.", {"choice": "A", "remaining": 30}),
            ("Choose Option A; 30 euros remain.", {"choice": "A", "remaining": 30}),
            ("Option B leaves 15 euros.", {"choice": "B", "remaining": 15}),
            ("No eligible option.", {"choice": "NONE", "remaining": None}),
            ("Neither option qualifies.", {"choice": "NONE", "remaining": None}),
        ]
        for summary, oracle in cases:
            with self.subTest(summary=summary):
                self.assertEqual(original.b1_signal(summary, oracle), 1)
                self.assertEqual(replay.lexical_b1(summary, oracle), 1)
                self.assertEqual(future(summary, oracle), 1)

    def test_future_metric_conservative_ambiguity_and_invalid_oracles(self):
        cases = [
            ("Option A leaves 30 euros, but Option B is selected.",
             {"choice": "A", "remaining": 30}),
            ("Option A leaves 30 euros.", {"choice": "A", "remaining": True}),
            ("Option A leaves 30 euros.", {"choice": "C", "remaining": 30}),
            ("Option A leaves 30 euros.", {"choice": "A", "remaining": -30}),
            ("Option A leaves 30 euros.", {"choice": "A", "remaining": "30"}),
        ]
        for summary, oracle in cases:
            with self.subTest(summary=summary, oracle=oracle):
                self.assertEqual(future(summary, oracle), 0)


if __name__ == "__main__":
    unittest.main()
