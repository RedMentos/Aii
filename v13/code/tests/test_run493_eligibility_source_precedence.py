"""Run493 preregistered source-precedence regression; software only, no model calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.agi import eligibility as E
from v13.agi import hub
from v13.runtime import Runtime
from v13.toolstep import ToolStep

CURRENT = "Project Delta. Decide between Option A and Option B using the latest rules."
OPTIONS = ("Option A: cost 60 euros, duration 4 days, local true. "
           "Option B: cost 90 euros, duration 3 days, local true.")
NEW_USER = "Budget 50 euros. Deadline 5 days. Local-only requirement: true."
STALE_BODY = "Budget 140 euros. Deadline 9 days. Local-only requirement: false."


class ProvenanceReader(unittest.TestCase):
    def test_original_combined_reader_reproduces_stale_quote_bug(self):
        # Diagnostic of the frozen source; this test intentionally documents the defect.
        old = E.read_fixed(CURRENT, [NEW_USER, STALE_BODY, OPTIONS])
        self.assertEqual(old["budget"], 140)
        self.assertEqual(old["deadline"], 9)

    def test_newest_direct_user_rule_beats_old_body_quote(self):
        v = E.read_fixed_sources(CURRENT, [NEW_USER], [STALE_BODY, OPTIONS])
        self.assertEqual(v["budget"], 50)
        self.assertEqual(v["deadline"], 5)
        self.assertIs(v["local_only"], True)
        self.assertEqual(v["options"][0]["cost"], 60)
        args = E.args_for(v, CURRENT, [NEW_USER, STALE_BODY, OPTIONS])
        self.assertEqual(E.tool(**args)["action"], "NONE")

    def test_current_rules_override_both_history_and_quotes(self):
        current = CURRENT + " Budget 80 euros. Deadline 4 days. Local-only requirement: false."
        v = E.read_fixed_sources(current, [NEW_USER], [STALE_BODY, OPTIONS])
        self.assertEqual((v["budget"], v["deadline"], v["local_only"]), (80, 4, False))
        self.assertEqual(E.tool(**E.args_for(v, current, [NEW_USER, STALE_BODY, OPTIONS]))["action"], "A")

    def test_conflicting_verified_quotes_are_unknown_not_last_wins(self):
        q1 = "Budget 80 euros. Deadline 5 days. Local-only requirement: true."
        q2 = "Budget 140 euros. Deadline 5 days. Local-only requirement: true."
        v = E.read_fixed_sources(CURRENT, [], [q1, q2, OPTIONS])
        self.assertIsNone(v["budget"])
        self.assertEqual(v["deadline"], 5)
        self.assertIs(v["local_only"], True)
        self.assertEqual(E.tool(**E.args_for(v, CURRENT, [q1, q2, OPTIONS]))["action"], "UNKNOWN")

    def test_conflicting_current_rule_does_not_fall_back(self):
        current = CURRENT + " Budget 50 euros. Budget 90 euros."
        v = E.read_fixed_sources(current, [NEW_USER], [STALE_BODY, OPTIONS])
        self.assertIsNone(v["budget"])

    def test_partial_current_option_blocks_stale_completion(self):
        current = CURRENT + " Option A: cost 20 euros. Option B: cost 90 euros, duration 3 days, local true."
        v = E.read_fixed_sources(current, [NEW_USER], [OPTIONS])
        self.assertIsNone(v["options"])

    def test_disagreeing_body_options_do_not_pick_arbitrary_quote(self):
        changed = OPTIONS.replace("cost 60", "cost 25")
        v = E.read_fixed_sources(CURRENT, [NEW_USER], [OPTIONS, changed])
        self.assertIsNone(v["options"])

    def test_identical_body_options_remain_usable(self):
        v = E.read_fixed_sources(CURRENT, [NEW_USER], [OPTIONS, OPTIONS])
        self.assertEqual(v["options"][0]["cost"], 60)
        self.assertEqual(v["options"][1]["cost"], 90)


class LiveToolStepPrecedence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.cfg["eligibility_reader"] = "fixed"
        self.r.sleep.cycle.set_policy("enabled", "off")
        hub(self.r).tools.enable("eligibility")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_runtime_proposal_uses_user_rule_without_c3(self):
        e = self.r.store.event(self.r.session, CURRENT)
        with patch.object(ToolStep, "earlier_parts", return_value=([NEW_USER], [STALE_BODY, OPTIONS])), \
             patch.object(self.r.pool, "get", side_effect=AssertionError("MODEL_READ_FORBIDDEN")):
            proposal = ToolStep(self.r).plan(e, CURRENT)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal["args"]["budget"], 50)
        self.assertEqual(proposal["args"]["deadline"], 5)
        self.assertIs(proposal["args"]["local_only"], True)
        self.assertNotEqual(proposal["status"], "APPROVED")
        result = ToolStep(self.r).shadow(e, proposal)
        self.assertEqual(result["result"]["action"], "NONE")
        self.assertIsNone(proposal.get("truth_authority"))

    def test_runtime_conflicting_quote_rule_refuses(self):
        e = self.r.store.event(self.r.session, CURRENT)
        q1 = "Budget 80 euros. Deadline 5 days. Local-only requirement: true."
        q2 = "Budget 140 euros. Deadline 5 days. Local-only requirement: true."
        with patch.object(ToolStep, "earlier_parts", return_value=([], [q1, q2, OPTIONS])), \
             patch.object(self.r.pool, "get", side_effect=AssertionError("MODEL_READ_FORBIDDEN")):
            proposal = ToolStep(self.r).plan(e, CURRENT)
        self.assertIsNotNone(proposal)
        self.assertNotIn("budget", proposal["args"])
        self.assertEqual(ToolStep(self.r).shadow(e, proposal)["result"]["action"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
