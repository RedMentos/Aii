"""Preregistered conservative post-native C3 F1/F5 answer contradiction veto."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ask_verified_budget import _answer_uses_euro_source, query
from v13.runtime import Runtime


SOURCE = {"value": "615 Euro", "topic": "Project Elyra budget"}
QUESTION = "What is the budget for Project Elyra?"


class FakeRunner:
    def __init__(self, answer):
        self.answer = answer
        self.calls = 0
        self.last_metrics = {"status": "FINAL"}

    def generate(self, messages, cancel, deadline, *, max_tokens, seed):
        self.calls += 1
        yield self.answer


class C3BudgetOutputGuardTests(unittest.TestCase):
    def test_existing_declarative_budget_answers_stay_accepted(self):
        for answer in (
            "The budget for Project Elyra is 615 Euro.",
            "615 Euros.",
            "Projekt Elyra: 615 EUR.",
        ):
            with self.subTest(answer=answer):
                self.assertTrue(_answer_uses_euro_source(answer, SOURCE))

    def test_negated_or_unverified_amount_never_passes(self):
        for answer in (
            "The budget for Project Elyra is not 615 Euro.",
            "Project Elyra: 615 Euro is wrong.",
            "615 Euro? No.",
            "The 615 Euro figure is unverified.",
        ):
            with self.subTest(answer=answer):
                self.assertFalse(_answer_uses_euro_source(answer, SOURCE))

    def test_same_amount_in_unsupported_currency_never_passes(self):
        for answer in (
            "Project Elyra: 615 Euro and 615 dollars.",
            "Project Elyra has 615 Euro but 615 USD.",
            "615 Euro or 615 GBP.",
        ):
            with self.subTest(answer=answer):
                self.assertFalse(_answer_uses_euro_source(answer, SOURCE))

    def native_answer(self, answer):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                event = r.store.event(r.session, "Project Elyra budget")
                mid = r.memory.feedback(
                    event["event_id"], "fact", "615 Euro",
                    key="Project Elyra budget", permission="record")
                r.memory.candidate(mid, r.session)
                runner = FakeRunner(answer)
                with patch("scripts.ask_verified_budget._pinned_c3", return_value=True), \
                     patch.object(r.memory.semantic_keys, "mode", return_value="off"), \
                     patch.object(r.models, "verify", return_value={
                         "language": {"ok": True, "hash_checked": True}}), \
                     patch.object(r.models, "path_for", return_value=Path("fake.gguf")), \
                     patch.object(r.pool, "get", return_value=runner), \
                     patch.object(r.pool, "unload",
                                  return_value={"process_reaped": True}) as unload:
                    result = query(r, QUESTION, native=True)
                unload.assert_called_once_with("C3_LANGUAGE")
                return result, runner.calls
            finally:
                r.close()

    def test_integrated_native_negation_fails_closed_after_one_call(self):
        result, calls = self.native_answer("Project Elyra budget is not 615 Euro.")
        self.assertEqual(calls, 1)
        self.assertEqual(result["status"], "UNVERIFIED_NATIVE_ANSWER")
        self.assertEqual(result["native_calls"], 1)
        self.assertNotIn("answer", result)

    def test_integrated_native_same_amount_foreign_currency_fails_closed(self):
        result, calls = self.native_answer("615 Euro and 615 dollars.")
        self.assertEqual(calls, 1)
        self.assertEqual(result["status"], "UNVERIFIED_NATIVE_ANSWER")
        self.assertEqual(result["native_calls"], 1)
        self.assertNotIn("answer", result)


if __name__ == "__main__":
    unittest.main()
