"""F1/F5 Euro alias equivalence: preserve exact source and conflict veto.

Software-only, review branch; does not promote C3, STEP2, or learning gates.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ask_verified_budget import exact_source
from v13.runtime import Runtime
from v13.source_consumer import admit, recall_and_admit


class EuroAliasEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.query = "What is the budget for Project Elyra?"

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def add(self, key, value):
        event = self.runtime.store.event(self.runtime.session, key)
        mid = self.runtime.memory.feedback(
            event["event_id"], "fact", value, key=key, permission="record")
        return self.runtime.memory.candidate(mid, self.runtime.session)

    def test_euro_eur_symbol_same_integer_is_one_verified_value(self):
        sources = [
            self.add("Project Elyra budget", "615 Euro"),
            self.add("Project Elyra budgets", "615 EUR"),
            self.add("Projekt Elyra budget", "615 €"),
        ]
        got = admit(self.query, self.runtime.session, sources, self.runtime.memory)
        self.assertEqual(got["status"], "ADMITTED")
        self.assertEqual(got["admitted_count"], 3)
        self.assertIn(got["source"]["value"], {"615 Euro", "615 EUR", "615 €"})
        self.assertEqual(
            self.runtime.store.read_source(got["source"]["source_ref"]),
            got["source"]["value"])

    def test_numeric_disagreement_still_refuses_every_alias(self):
        a = self.add("Project Elyra budget", "615 Euro")
        b = self.add("Project Elyra budgets", "616 EUR")
        got = admit(self.query, self.runtime.session, [a, b], self.runtime.memory)
        self.assertEqual(got["status"], "CLARIFY")
        self.assertEqual(got["reason"], "CONFLICTING_AUTHORIZED_SOURCES")
        self.assertFalse(got["model_allowed"])

    def test_exact_operator_retains_one_raw_verified_alias_without_c3(self):
        self.add("Project Elyra budget", "615 Euro")
        self.add("Project Elyra budgets", "615 EUR")
        decision = recall_and_admit(
            self.query, self.runtime.session, self.runtime.memory)
        self.assertEqual(decision["status"], "ADMITTED")
        with patch.object(self.runtime.pool, "get",
                          side_effect=AssertionError("C3 must not run")):
            got = exact_source(self.runtime, self.query)
        self.assertEqual(got["status"], "FINAL_SOURCE_EXACT")
        self.assertIn(got["answer"], {
            "Project Elyra: 615 Euro.", "Project Elyra: 615 EUR."})
        self.assertEqual(got["authority"], "EXACT_SOURCE")
        self.assertFalse(got["model_called"])
        self.assertEqual(got["native_calls"], 0)
        self.assertFalse(got["learned"])


    def test_tampered_equivalent_competitor_vetoes_exact_output(self):
        self.add("Project Elyra budget", "615 Euro")
        rival = self.add("Project Elyra budgets", "615 EUR")
        self.assertEqual(
            exact_source(self.runtime, self.query)["status"], "FINAL_SOURCE_EXACT")
        blob = (self.runtime.home / "data/blobs" /
                rival["source_ref"]["sha256"])
        blob.write_text("tampered", encoding="utf-8")
        with patch.object(self.runtime.pool, "get",
                          side_effect=AssertionError("C3 must not run")):
            got = exact_source(self.runtime, self.query)
        self.assertEqual(got["status"], "CLARIFY")
        self.assertNotIn("answer", got)
        self.assertEqual(got["native_calls"], 0)

    def test_revoked_equivalent_competitor_does_not_poison_remaining_source(self):
        self.add("Project Elyra budget", "615 Euro")
        rival = self.add("Project Elyra budgets", "615 EUR")
        self.runtime.memory.forget(rival["id"])
        with patch.object(self.runtime.pool, "get",
                          side_effect=AssertionError("C3 must not run")):
            got = exact_source(self.runtime, self.query)
        self.assertEqual(got["status"], "FINAL_SOURCE_EXACT")
        self.assertEqual(got["answer"], "Project Elyra: 615 Euro.")
        self.assertFalse(got["model_called"])
        self.assertEqual(got["native_calls"], 0)


if __name__ == "__main__":
    unittest.main()
