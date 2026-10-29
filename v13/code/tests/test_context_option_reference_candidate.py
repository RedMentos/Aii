"""Run141 safe Context OS fallback from pure A/B references to exact prior source."""
from __future__ import annotations

import os
from pathlib import Path
import unittest

from scripts import context_option_reference_candidate as candidate
from scripts import step2_exact_rule_native_replay_preflight as frozen
from v13.agi import eligibility as original


PRIOR_RULES = "Project Mira. Budget 100 euros. Deadline 5 days. Local-only requirement: false."
PRIOR_OPTIONS = (
    "Project Mira supplier sheet. "
    "Option A: cost 60 euros, duration 3 days, local true. "
    "Option B: cost 85 euros, duration 4 days, local false."
)
REFERENCE = "Project Mira. Decide between Option A and Option B from the earlier supplier sheet."


class Run141OptionReference(unittest.TestCase):
    def test_original_misses_options_candidate_recovers_pure_reference(self):
        self.assertIsNone(original.read_fixed(REFERENCE, [PRIOR_RULES, PRIOR_OPTIONS])["options"])
        got = candidate.read_fixed_reference(REFERENCE, [PRIOR_RULES, PRIOR_OPTIONS])
        self.assertEqual(got["options"], [
            {"entity": "A", "cost": 60, "days": 3, "local": True},
            {"entity": "B", "cost": 85, "days": 4, "local": False},
        ])
        self.assertEqual((got["budget"], got["deadline"], got["local_only"]),
                         (100, 5, False))
        result = original.decide(
            {k: got[k] for k in ("budget", "deadline", "local_only")},
            got["options"], REFERENCE, [PRIOR_RULES, PRIOR_OPTIONS])
        self.assertEqual(result["action"], "A")

    def test_partial_current_update_blocks_fallback(self):
        current = REFERENCE + " Option A: cost 95 euros."
        self.assertIsNone(candidate.read_fixed_reference(
            current, [PRIOR_RULES, PRIOR_OPTIONS])["options"])

    def test_complete_current_option_overrides_old(self):
        current = REFERENCE + (
            " Option A: cost 90 euros, duration 3 days, local true."
            " Option B: cost 80 euros, duration 4 days, local false."
        )
        got = candidate.read_fixed_reference(current, [PRIOR_RULES, PRIOR_OPTIONS])
        self.assertEqual([o["cost"] for o in got["options"]], [90, 80])

    def test_conflicting_current_complete_clauses_refuse(self):
        current = REFERENCE + (
            " Option A: cost 60 euros, duration 3 days, local true."
            " Option A: cost 90 euros, duration 3 days, local true."
            " Option B: cost 85 euros, duration 4 days, local false."
        )
        self.assertIsNone(candidate.read_fixed_reference(
            current, [PRIOR_RULES, PRIOR_OPTIONS])["options"])

    def test_no_prior_options_is_unknown(self):
        got = candidate.read_fixed_reference(REFERENCE, [PRIOR_RULES])
        self.assertIsNone(got["options"])

    def test_newest_earlier_partial_update_blocks_stale_fallback(self):
        partial = "Option A: cost 70 euros."
        got = candidate.read_fixed_reference(
            REFERENCE, [PRIOR_RULES, PRIOR_OPTIONS, partial])
        self.assertIsNone(got["options"])

    def test_ambiguous_current_rules_still_refused(self):
        current = REFERENCE + " Budget 100 euros. Budget 50 euros."
        got = candidate.read_fixed_reference(current, [PRIOR_RULES, PRIOR_OPTIONS])
        self.assertIsNone(got["budget"])
        self.assertIsNotNone(got["options"])

    def test_uncovered_single_option_reference_not_silently_skipped(self):
        current = "Please choose Option A."
        self.assertIsNone(candidate.option_with_reference_fallback(
            "A", current, [PRIOR_OPTIONS]))

    def test_invalid_inputs_fail_before_read(self):
        with self.assertRaisesRegex(ValueError, "OPTION_SOURCE_INPUT_INVALID"):
            candidate.read_fixed_reference(REFERENCE, [PRIOR_OPTIONS, 1])
        with self.assertRaisesRegex(ValueError, "OPTION_SOURCE_INPUT_INVALID"):
            candidate.option_with_reference_fallback("C", REFERENCE, [PRIOR_OPTIONS])

    def test_original_six_fixture_full_history_upper_bound_if_supplied(self):
        source_path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        if not source_path:
            self.skipTest("original frozen native source raw not supplied")
        source = frozen.load_original(Path(source_path))
        report = candidate.replay_upper_bound(source)
        self.assertEqual(report["rows"], 6)
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(report["wrong_committed"], 0)


if __name__ == "__main__":
    unittest.main()
