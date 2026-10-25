"""Run294 preregistered current-message option precedence (software only).

The direct READ_LOCAL tool must not turn a stale quoted option into a
current authorized choice. No native inference or learning-gate promotion.
"""
import unittest
from v13.agi import eligibility as E

PRIOR = ("Budget 100 euros. Deadline 10 days. Local-only requirement: false. "
         "Option A: cost 40 euros, duration 5 days, local true. "
         "Option B: cost 70 euros, duration 5 days, local true.")
CURRENT = ("Budget 100 euros. Deadline 10 days. Local-only requirement: false. "
           "Option A: cost 90 euros, duration 5 days, local true. "
           "Option B: cost 70 euros, duration 5 days, local true.")
RULES = {"budget": 100, "deadline": 10, "local_only": False}
OLD = [{"entity": "A", "cost": 40, "days": 5, "local": True},
       {"entity": "B", "cost": 70, "days": 5, "local": True}]
NEW = [dict(OLD[0], cost=90), dict(OLD[1])]


class CurrentOptionAuthority(unittest.TestCase):
    def test_stale_earlier_option_cannot_override_current(self):
        d = E.decide(RULES, OLD, CURRENT, [PRIOR])
        self.assertEqual(d["action"], "UNKNOWN")
        self.assertIn("A:conflicts_current", d["rejected"])

    def test_new_current_option_remains_usable(self):
        d = E.decide(RULES, NEW, CURRENT, [PRIOR])
        self.assertEqual(d["action"], "B")
        self.assertEqual(d["rejected"], [])

    def test_two_conflicting_current_clauses_refuse(self):
        current = CURRENT + " Option A: cost 30 euros, duration 5 days, local true."
        d = E.decide(RULES, NEW, current, [PRIOR])
        self.assertEqual(d["action"], "UNKNOWN")
        self.assertIn("A:conflicts_current", d["rejected"])
        self.assertIsNone(E.fixed_option("A", current))

    def test_repeated_identical_current_clause_is_not_conflict(self):
        current = CURRENT + " Option A: cost 90 euros, duration 5 days, local true."
        self.assertEqual(E.decide(RULES, NEW, current, [PRIOR])["action"], "B")
        self.assertEqual(E.fixed_option("A", current), NEW[0])

    def test_mentions_only_preserve_earlier_exact_option_evidence(self):
        current = ("Budget 100 euros. Deadline 10 days. Local-only requirement: false. "
                   "Which option A or option B should I choose?")
        self.assertEqual(E.decide(RULES, OLD, current, [PRIOR])["action"], "A")

    def test_adjacent_option_clauses_do_not_lend_each_other_fields(self):
        current = ("Budget 100 euros. Deadline 10 days. Local-only requirement: false. "
                   "Option A: cost 40 euros, duration 5 days; "
                   "Option B: cost 70 euros, duration 5 days, local true.")
        d = E.decide(RULES, OLD, current)
        self.assertEqual(d["action"], "UNKNOWN")
        self.assertIn("A:conflicts_current", d["rejected"])

    def test_conflicting_current_rule_values_refuse(self):
        current = CURRENT + " Budget 10 euros."
        d = E.decide(RULES, NEW, current, [PRIOR])
        self.assertEqual(d["action"], "UNKNOWN")
        self.assertIn("budget:conflicts_current", d["rejected"])

    def test_string_false_is_not_boolean_false(self):
        current = CURRENT.replace("local true", "local true")
        bad = [dict(NEW[0], local="false"), dict(NEW[1])]
        d = E.decide(RULES, bad, current, [PRIOR])
        self.assertEqual(d["action"], "UNKNOWN")
        self.assertIn("A:conflicts_current", d["rejected"])


if __name__ == "__main__":
    unittest.main()
