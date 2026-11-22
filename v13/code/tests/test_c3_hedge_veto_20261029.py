"""Preregistered C3 F1/F5 lexical false-positive budget veto, software-only."""
import unittest

from scripts.ask_verified_budget import _answer_uses_euro_source
from tests.test_c3_budget_output_guard_20261029 import C3BudgetOutputGuardTests


SOURCE = {"value": "615 Euro", "topic": "Project Elyra budget"}


class C3HedgeVetoTests(unittest.TestCase):
    def test_unsupported_negations_and_hedges_are_not_sourced_answers(self):
        candidates = (
            "Project Elyra's budget isn't 615 Euro.",
            "Project Elyra's budget isn’t 615 Euro.",
            "Project Elyra: 615 Euro is false.",
            "I doubt that Project Elyra has 615 Euro.",
            "Project Elyra may have 615 Euro.",
            "Project Elyra might have 615 Euro.",
            "Project Elyra: 615 Euro was rejected.",
            "Project Elyra: 615 Euro (allegedly).",
            "Projekt Elyra: 615 Euro, vielleicht.",
            "Project Elyra: 615 Euro is unconfirmed.",
            "Project Elyra: 615 Euro if approved.",
        )
        for answer in candidates:
            with self.subTest(answer=answer):
                self.assertFalse(_answer_uses_euro_source(answer, SOURCE))

    def test_affirmative_exact_source_answers_remain_accepted(self):
        for answer in (
            "The budget for Project Elyra is 615 Euro.",
            "Projekt Elyra: 615 EUR.",
            "615 Euros.",
            "The verified budget is 615 Euro.",
        ):
            with self.subTest(answer=answer):
                self.assertTrue(_answer_uses_euro_source(answer, SOURCE))

    def test_mocked_native_contradiction_never_leaves_operator_lane(self):
        result, calls = C3BudgetOutputGuardTests().native_answer(
            "Project Elyra's budget isn't 615 Euro.")
        self.assertEqual(calls, 1)
        self.assertEqual(result["status"], "UNVERIFIED_NATIVE_ANSWER")
        self.assertEqual(result["native_calls"], 1)
        self.assertNotIn("answer", result)


if __name__ == "__main__":
    unittest.main()
