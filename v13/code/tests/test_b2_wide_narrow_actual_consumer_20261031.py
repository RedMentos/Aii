"""Run101: actual Context OS wide/narrow B2 quote delivery, fake generator only.

These tests use real Runtime/Store/Cognition and persisted packets, but never
run a model or claim semantic utility. They are not Run87 native re-scoring.
"""
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from v13.common import dumps
from v13.runtime import Runtime
from v13.cognition import Cognition


PRIOR = ("Project Lyra archived logistics policy. Maximum budget: 177 credits. "
         "Maximum deadline: 13 ticks. Required local-only: true.")
CURRENT = ("Project Lyra latest logistics options. Option A: budget 155 credits; "
           "deadline 12 ticks; local-only true. Option B: budget 145 credits; "
           "deadline 10 ticks; local-only false. Which option meets archived policy?")
QUOTE = "Maximum budget: 177 credits."


class B2WideNarrowActualConsumer(unittest.TestCase):
    def setup_turns(self, width):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        runtime = Runtime(Path(temp.name))
        self.addCleanup(runtime.close)
        runtime.cfg.update({
            "b2_state_slots": 2, "b2_context_chars": 1500,
            "b2_control": "two_body", "b2_quote_select": "pointer",
            "offer_quote_context_chars": width, "memory_threshold": 0.0,
        })
        cognition = Cognition(runtime)
        captured = []

        def generate(messages, *args, **kwargs):
            payload = json.loads(messages[-1]["content"])
            captured.append(payload)
            ids = [entry["id"] for entry in payload.get("quote_choices", [])
                   if entry["text"] == QUOTE]
            if len(ids) != 1:
                raise AssertionError("Exact prior rule quote choice missing or ambiguous")
            return iter([dumps({"summary": "Source-bound policy observation.",
                                "quotes": ids, "uncertainty": "",
                                "needs_reentry": False})])

        runner = SimpleNamespace(last_metrics={"status": "FINAL"}, generate=generate)
        with patch.object(runtime.pool, "get", return_value=runner):
            prior = runtime.store.event(runtime.session, PRIOR)
            prior_offer = cognition.offer("B2_GIST", prior, 0, time.monotonic() + 30)
            current = runtime.store.event(runtime.session, CURRENT)
            current_offer = cognition.offer("B2_GIST", current, 0, time.monotonic() + 30)
        self.assertEqual(len(captured), 2)
        self.assertTrue(current_offer["context_source_refs"])
        self.assertEqual(current_offer["context_source_refs"][0]["source_id"],
                         prior["source_ref"]["source_id"])
        return runtime, cognition, prior, current, prior_offer, current_offer

    def test_wide_quote_delivers_full_verified_prior_rules(self):
        runtime, cognition, prior, current, _, offer = self.setup_turns(400)
        rendered = cognition.analyst_context([offer], current, 0)
        self.assertEqual(len(rendered), 1)
        quotes = rendered[0]["verified_quotes"]
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0]["text"], PRIOR)
        self.assertEqual(quotes[0]["verification"],
                         "EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE")
        self.assertFalse(quotes[0]["semantic_truth_authority"])
        self.assertEqual(runtime.store.read_source(quotes[0]["source_ref"]), PRIOR)
        self.assertIn("Required local-only: true.", quotes[0]["text"])
        self.assertEqual(runtime.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"], 0)

    def test_narrow_quote_delivers_only_selected_sentence(self):
        runtime, cognition, prior, current, _, offer = self.setup_turns(0)
        rendered = cognition.analyst_context([offer], current, 0)
        quotes = rendered[0]["verified_quotes"]
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0]["text"], QUOTE)
        self.assertEqual(quotes[0]["verification"], "EXACT_SOURCE_SUBSTRING_ONLY")
        self.assertFalse(quotes[0]["semantic_truth_authority"])
        self.assertNotIn("Required local-only", quotes[0]["text"])
        self.assertEqual(runtime.store.read_source(quotes[0]["source_ref"]), QUOTE)

    def test_revoked_prior_source_fails_closed_even_when_wide(self):
        runtime, cognition, prior, current, _, offer = self.setup_turns(400)
        with runtime.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (prior["source_ref"]["source_id"],))
        with self.assertRaises(ValueError):
            cognition.analyst_context([offer], current, 0)

    def test_wrong_turn_or_mutated_offer_refused(self):
        runtime, cognition, prior, current, _, offer = self.setup_turns(400)
        other = runtime.store.event(runtime.session, "Different turn.")
        with self.assertRaises(ValueError):
            cognition.analyst_context([offer], other, 0)
        changed = copy.deepcopy(offer)
        changed["offer"]["quotes"] = ["Forged new rule."]
        with self.assertRaises(ValueError):
            cognition.analyst_context([changed], current, 0)


if __name__ == "__main__":
    unittest.main()
