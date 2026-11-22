"""Run102 real C3 Context OS plan consumes exact B2 source context, no model."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from v13.common import dumps
from v13.runtime import Runtime
from v13 import context_os as ctxos


PRIOR = ("Project Mira archived logistics policy. Maximum budget: 163 credits. "
         "Maximum deadline: 14 ticks. Required local-only: true.")
CURRENT = ("Project Mira latest options. Option A budget 150 credits, deadline 12 ticks, "
           "local-only true. Option B budget 149 credits, deadline 13 ticks, "
           "local-only false. Which is allowed?")
QUOTE = "Maximum budget: 163 credits."


class C3ContextOSB2Evidence(unittest.TestCase):
    def setup_offers(self, width):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        runtime = Runtime(Path(temp.name))
        self.addCleanup(runtime.close)
        runtime.cfg.update({
            "b2_state_slots": 2, "b2_context_chars": 1500,
            "b2_control": "two_body", "b2_quote_select": "pointer",
            "offer_quote_context_chars": width, "memory_threshold": 0.0,
        })
        def generate(messages, *args, **kwargs):
            payload = json.loads(messages[-1]["content"])
            ids = [x["id"] for x in payload.get("quote_choices", [])
                   if x["text"] == QUOTE]
            if len(ids) != 1:
                raise AssertionError("Missing exact budget quote pointer")
            return iter([dumps({"summary": "Source-bound archived policy.",
                                "quotes": ids, "uncertainty": "",
                                "needs_reentry": False})])
        fake = SimpleNamespace(last_metrics={"status": "FINAL"}, generate=generate)
        with patch.object(runtime.pool, "get", return_value=fake):
            prior = runtime.store.event(runtime.session, PRIOR)
            runtime.cognition.offer("B2_GIST", prior, 0, time.monotonic() + 30)
            current = runtime.store.event(runtime.session, CURRENT)
            offer = runtime.cognition.offer("B2_GIST", current, 0, time.monotonic() + 30)
        return runtime, prior, current, offer

    def plan(self, width):
        runtime, prior, current, offer = self.setup_offers(width)
        rendered = runtime.cognition.analyst_context([offer], current, 0)
        volatile = [("HYPOTHESES", "\nSource-bound hypotheses, not facts: ", rendered)]
        plan = ctxos.controller(runtime).plan(
            current["event_id"], "C3_LANGUAGE", "Pinned safety instructions.",
            volatile, [], CURRENT, provenance=[current["source_ref"], prior["source_ref"]])
        self.assertFalse(plan["applied"])
        self.assertEqual(plan["plan"]["mode"], "SHADOW")
        self.assertEqual(plan["plan"]["role"], "C3_LANGUAGE")
        self.assertIn(prior["source_ref"], plan["plan"]["provenance"])
        self.assertEqual(runtime.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"], 0)
        return rendered, plan

    def test_wide_exact_prior_rules_survive_c3_legacy_and_planned_view(self):
        rendered, plan = self.plan(400)
        self.assertEqual(rendered[0]["verified_quotes"][0]["text"], PRIOR)
        for view in ("messages", "planned"):
            text = "\n".join(m["content"] for m in plan[view])
            self.assertIn(PRIOR, text)
            self.assertIn("Maximum deadline: 14 ticks.", text)
            self.assertIn("Required local-only: true.", text)
            self.assertIn("semantic_truth_authority", text)

    def test_narrow_c3_view_contains_only_selected_prior_sentence(self):
        rendered, plan = self.plan(0)
        self.assertEqual(rendered[0]["verified_quotes"][0]["text"], QUOTE)
        for view in ("messages", "planned"):
            text = "\n".join(m["content"] for m in plan[view])
            self.assertIn(QUOTE, text)
            self.assertNotIn("Maximum deadline: 14 ticks.", text)
            self.assertNotIn("Required local-only: true.", text)

    def test_deleted_prior_ref_cannot_enter_context_plan(self):
        runtime, prior, current, offer = self.setup_offers(400)
        with runtime.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (prior["source_ref"]["source_id"],))
        with self.assertRaises(ValueError):
            rendered = runtime.cognition.analyst_context([offer], current, 0)
            ctxos.controller(runtime).plan(current["event_id"], "C3_LANGUAGE",
                                         "Pinned.", [("HYPOTHESES", "", rendered)], [],
                                         CURRENT, provenance=[current["source_ref"]])
        self.assertEqual(runtime.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")["n"], 0)


if __name__ == "__main__":
    unittest.main()
