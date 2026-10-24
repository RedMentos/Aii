"""Run101: a negated calculator result is not positive Age-1 tool shadow evidence.
Real Runtime/SQLite, actual pure calculator, no native models or tool promotion.
"""
import unittest

from v13 import toolstep as T
from tests.test_toolstep import Base


class ToolStepNegationRun101(Base):
    def compare_text(self, output):
        e = self.ev("What is 48 times 37?")
        ts = T.ToolStep(self.r)
        proposal = ts.plan(e, "What is 48 times 37?")
        self.assertEqual(proposal["tool"], "calc")
        self.assertNotEqual(proposal["status"], "APPROVED")
        shadow = ts.shadow(e, proposal)
        self.assertEqual(shadow["result"], 1776)
        result = ts.compare(e, shadow, output)
        report = T.report(self.r.store)
        self.assertEqual(report["shadow_compared"], 1)
        self.assertEqual(report["shadow_agreement"], 1.0 if result else 0.0)
        return result

    def test_correct_number_explicitly_called_incorrect_is_not_agreement(self):
        self.assertFalse(self.compare_text(
            "No, 1,776 is incorrect; the answer is 1,775."
        ))

    def test_not_correct_number_is_not_agreement(self):
        self.assertFalse(self.compare_text(
            "The result is not 1,776; it is 1,775."
        ))

    def test_explicit_or_ambiguity_is_not_agreement(self):
        self.assertFalse(self.compare_text(
            "Either 1,776 or 1,775."
        ))

    def test_cannot_verify_number_is_not_agreement(self):
        self.assertFalse(self.compare_text(
            "I cannot verify 1,776."
        ))

    def test_correct_answer_followed_by_negation_of_wrong_number_is_agreement(self):
        self.assertTrue(self.compare_text(
            "The answer is 1,776, not 1,775."
        ))

    def test_unambiguous_correct_answer_is_agreement(self):
        self.assertTrue(self.compare_text(
            "The answer is 1,776."
        ))


if __name__ == "__main__":
    unittest.main()
