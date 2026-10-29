"""Run139 preregistered source-rule ambiguity counterexamples (software only)."""
from __future__ import annotations

from copy import deepcopy
import unittest

from scripts import eligibility_rule_ambiguity_candidate as candidate
from v13.agi import eligibility as original


OPTIONS = [
    {"entity": "A", "cost": 60, "days": 3, "local": True},
    {"entity": "B", "cost": 85, "days": 4, "local": False},
]
OPTION_SOURCE = (
    "Option A: cost 60 euros, duration 3 days, local true. "
    "Option B: cost 85 euros, duration 4 days, local false."
)
RULE_SOURCE = (
    "Budget 100 euros. Deadline 5 days. Local-only requirement: false. "
)
RULES = {"budget": 100, "deadline": 5, "local_only": False}


class Run139EligibilityAmbiguity(unittest.TestCase):
    def call(self, rules=RULES, current=RULE_SOURCE + OPTION_SOURCE, quotes=()):
        return candidate.strict_decide(rules, OPTIONS, current, quotes)

    def assert_unknown(self, result, reason):
        self.assertEqual(result["action"], "UNKNOWN")
        self.assertIn(reason, result["rejected"])
        self.assertTrue(all(
            o["eligible"] is None and o["remaining"] is None
            for o in result["options"]
        ))
        self.assertEqual(result["revision"], original.REVISION)

    def test_original_accepts_ambiguous_current_budget_candidate_refuses(self):
        source = RULE_SOURCE + "Budget 50 euros. " + OPTION_SOURCE
        self.assertEqual(
            original.decide(RULES, OPTIONS, source)["action"], "A"
        )
        self.assert_unknown(
            self.call(current=source), "budget:ambiguous_current"
        )

    def test_current_conflicts_for_each_rule_refuse(self):
        for field, contradiction in (
            ("budget", "Budget 50 euros. "),
            ("deadline", "Deadline 1 day. "),
            ("local_only", "Local-only requirement: true. "),
        ):
            with self.subTest(field=field):
                result = self.call(current=RULE_SOURCE + contradiction + OPTION_SOURCE)
                self.assert_unknown(result, field + ":ambiguous_current")

    def test_conflicting_verified_quotes_refuse_without_current_rule(self):
        quotes = [
            "Budget 100 euros. Deadline 5 days. Local-only requirement: false.",
            "Budget 50 euros. Deadline 1 day. Local-only requirement: true.",
        ]
        for field in ("budget", "deadline", "local_only"):
            with self.subTest(field=field):
                result = self.call(current=OPTION_SOURCE, quotes=quotes)
                self.assert_unknown(result, field + ":ambiguous_quotes")
        self.assertEqual(
            self.call(current=OPTION_SOURCE, quotes=quotes)["action"], "UNKNOWN"
        )
        self.assertEqual(
            self.call(current=OPTION_SOURCE, quotes=list(reversed(quotes))),
            self.call(current=OPTION_SOURCE, quotes=quotes),
        )

    def test_unique_current_rule_overrides_older_conflict(self):
        old = ["Budget 50 euros. Deadline 1 day. Local-only requirement: true."]
        expected = original.decide(RULES, OPTIONS, RULE_SOURCE + OPTION_SOURCE, old)
        actual = self.call(current=RULE_SOURCE + OPTION_SOURCE, quotes=old)
        self.assertEqual(actual, expected)
        self.assertEqual(actual["action"], "A")
        wrong = dict(RULES, budget=50)
        self.assert_unknown(
            self.call(rules=wrong, current=RULE_SOURCE + OPTION_SOURCE, quotes=old),
            "budget:conflicts_current",
        )

    def test_unambiguous_historical_quotes_preserve_original(self):
        current = OPTION_SOURCE
        quotes = [RULE_SOURCE]
        self.assertEqual(
            self.call(current=current, quotes=quotes),
            original.decide(RULES, OPTIONS, current, quotes),
        )
        self.assertEqual(self.call(current=current, quotes=quotes)["action"], "A")

    def test_repeated_identical_values_not_ambiguous(self):
        source = RULE_SOURCE + RULE_SOURCE + OPTION_SOURCE
        self.assertEqual(
            self.call(current=source),
            original.decide(RULES, OPTIONS, source),
        )

    def test_input_is_immutable_and_untrusted_quote_types_refused(self):
        rules, options = deepcopy(RULES), deepcopy(OPTIONS)
        source = RULE_SOURCE + "Budget 50 euros. " + OPTION_SOURCE
        self.assert_unknown(self.call(current=source), "budget:ambiguous_current")
        self.assertEqual((rules, options), (RULES, OPTIONS))
        with self.assertRaisesRegex(ValueError, "VERIFIED_QUOTES_INPUT_INVALID"):
            self.call(quotes=["Budget 100 euros.", 5])
        with self.assertRaisesRegex(ValueError, "RULE_AMBIGUITY_INPUT_INVALID"):
            candidate.strict_decide([], OPTIONS, source)

    def test_no_option_ambiguity_claim(self):
        # This run is scoped to *rule* ambiguity. Do not infer an option
        # ambiguity guarantee or modify the frozen original option reader.
        self.assertIs(candidate.original.decide, original.decide)


if __name__ == "__main__":
    unittest.main()
