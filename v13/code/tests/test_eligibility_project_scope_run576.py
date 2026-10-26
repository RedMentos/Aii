"""Run576: project-labelled eligibility evidence cannot cross user project boundaries.

Actual Runtime/SQLite plan and shadow path; fixed reader, no model/native calls.
Software only; does not establish STEP2, JEPA, B3 or Redmi acceptance.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from v13.runtime import Runtime
from v13.agi import eligibility as E, hub
from v13.toolstep import ToolStep

MIRA = "Project Mira. Budget 61 euros. Deadline 8 days. Local-only requirement: false."
ORION = "Project Orion. Budget 20 euros. Deadline 3 days. Local-only requirement: true."
OPTIONS = ("Option A: cost 45 euros, duration 7 days, local true. "
           "Option B: cost 55 euros, duration 4 days, local false. "
           "Compute remaining budget and eligibility; choose cheapest eligible.")
MIRA_QUESTION = "Project Mira. Apply earlier project rules. " + OPTIONS
ORION_QUESTION = "Project Orion. Apply earlier project rules. " + OPTIONS
GENERIC_QUESTION = "Apply earlier project rules. " + OPTIONS


class ProjectScopePure(unittest.TestCase):
    def test_case_insensitive_same_project_and_other_project_excluded(self):
        h, q = E.scope_earlier("PROJECT mIrA. " + OPTIONS, [ORION, MIRA],
                               [ORION, "Project MIRA. Budget 61 euros.", "Budget 100 euros."])
        self.assertEqual(h, [MIRA])
        self.assertEqual(q, ["Project MIRA. Budget 61 euros."])

    def test_multiple_labels_or_unlabelled_question_cannot_import_named_rules(self):
        self.assertEqual(E.scope_earlier("Project Mira. Project Orion. " + OPTIONS,
                                         [MIRA, ORION], [MIRA]), ([], []))
        self.assertEqual(E.scope_earlier(GENERIC_QUESTION, [MIRA, "Budget 50 euros."],
                                         [ORION, "Deadline 7 days."]),
                         (["Budget 50 euros."], ["Deadline 7 days."]))

    def test_unlabelled_earlier_is_not_a_named_project_source(self):
        self.assertEqual(E.scope_earlier(MIRA_QUESTION, ["Budget 80 euros.", MIRA],
                                         ["Deadline 4 days.", ORION]), ([MIRA], []))

    def test_multiple_labels_in_one_earlier_source_are_not_authoritative(self):
        mixed = "Project Mira. Budget 61 euros. Project Orion. Budget 20 euros."
        self.assertEqual(E.scope_earlier(MIRA_QUESTION, [mixed, MIRA], [mixed]),
                         ([MIRA], []))


class ProjectScopeRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.cfg["eligibility_reader"] = "fixed"
        self.r.pool.get = Mock(side_effect=AssertionError("No native C3 reader is allowed"))
        hub(self.r).tools.enable("eligibility")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def prior(self, text):
        e = self.r.store.event(self.r.session, text)
        with self.r.store.tx() as c:
            c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                      "VALUES (?,?,?,?,?,?,?)",
                      (self.r.session, e["event_id"], "assistant", "Acknowledged.", "FINAL",
                       json.dumps({"context_source_refs": [e["source_ref"]]}), 0))

    def decide(self, question):
        e = self.r.store.event(self.r.session, question)
        step = ToolStep(self.r)
        p = step.plan(e, question)
        self.assertIsNotNone(p, "fixed reader must still propose the exact options")
        self.assertEqual(p["tool"], "eligibility")
        shadow = step.shadow(e, p)
        self.assertIsNotNone(shadow)
        return p, shadow["result"]

    def test_other_project_budget_never_becomes_current_project_rule(self):
        self.prior(MIRA)
        p, result = self.decide(ORION_QUESTION)
        self.assertEqual(result["action"], "UNKNOWN")
        self.assertNotIn("quotes", p["args"])
        self.assertNotIn("budget", p["args"])
        self.r.pool.get.assert_not_called()

    def test_same_project_preserves_real_earlier_rule_reuse(self):
        self.prior(MIRA)
        p, result = self.decide(MIRA_QUESTION)
        self.assertEqual(result["action"], "A")
        self.assertEqual(p["args"]["budget"], 61)
        self.assertIn(MIRA, p["args"]["quotes"])
        self.r.pool.get.assert_not_called()

    def test_mixed_history_uses_only_matching_project(self):
        self.prior(ORION)
        self.prior(MIRA)
        p, result = self.decide(MIRA_QUESTION)
        self.assertEqual(result["action"], "A")
        self.assertIn(MIRA, p["args"]["quotes"])
        self.assertNotIn(ORION, p["args"]["quotes"])

    def test_generic_question_cannot_inherit_named_project_rules(self):
        self.prior(MIRA)
        p, result = self.decide(GENERIC_QUESTION)
        self.assertEqual(result["action"], "UNKNOWN")
        self.assertNotIn("quotes", p["args"])


if __name__ == "__main__":
    unittest.main()
