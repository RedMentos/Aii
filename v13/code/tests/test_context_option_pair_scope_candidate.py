"""Counterexamples for Run141 typed joint A/B scope, source-only review."""
import unittest

from scripts import context_option_pair_scope_candidate as guarded
from scripts import context_option_reference_candidate as parent


RULES = "Project Mira. Budget 100 euros. Deadline 5 days. Local-only requirement: false."
INDIVIDUAL = (
    "Project Mira supplier sheet. "
    "Option A: cost 60 euros, duration 3 days, local true. "
    "Option B: cost 85 euros, duration 4 days, local false."
)
REFERENCE = "Project Mira. Decide between Option A and Option B from the earlier supplier sheet."
JOINT = "Project Mira. Option A and Option B: cost 60 euros, duration 3 days, local true."


class PairScopeReview(unittest.TestCase):
    def test_original_run141_accepts_unscoped_joint_values_red_witness(self):
        values = parent.read_fixed_reference(JOINT, [RULES, INDIVIDUAL])
        self.assertEqual(values["options"], [
            {"entity": "A", "cost": 60, "days": 3, "local": True},
            {"entity": "B", "cost": 60, "days": 3, "local": True},
        ])

    def test_guard_refuses_joint_typed_values(self):
        self.assertTrue(guarded.ambiguous_typed_pair(JOINT))
        self.assertIsNone(guarded.read_fixed_pair_scope(JOINT, [RULES, INDIVIDUAL])["options"])

    def test_guard_refuses_reversed_joint_values(self):
        text = "Option B or Option A: cost 70 euros, duration 4 days, local false."
        self.assertTrue(guarded.ambiguous_typed_pair(text))
        self.assertIsNone(guarded.read_fixed_pair_scope(text, [INDIVIDUAL])["options"])

    def test_guard_refuses_comma_joint_values(self):
        text = "Option A, Option B: cost 70 euros, duration 4 days, local false."
        self.assertTrue(guarded.ambiguous_typed_pair(text))
        self.assertIsNone(guarded.read_fixed_pair_scope(text, [INDIVIDUAL])["options"])

    def test_guard_refuses_versus_joint_values(self):
        text = "Option A versus Option B: cost 70 euros, duration 4 days, local false."
        self.assertTrue(guarded.ambiguous_typed_pair(text))
        self.assertIsNone(guarded.read_fixed_pair_scope(text, [INDIVIDUAL])["options"])

    def test_guard_refuses_semicolon_cross_option_value_leakage(self):
        text = "Option A: cost 60 euros; Option B: cost 85 euros, duration 4 days, local false."
        self.assertTrue(guarded.ambiguous_typed_pair(text))
        self.assertIsNone(guarded.read_fixed_pair_scope(text, [INDIVIDUAL])["options"])

    def test_pure_pair_reference_recovers_prior_distinct_options(self):
        self.assertFalse(guarded.ambiguous_typed_pair(REFERENCE))
        got = guarded.read_fixed_pair_scope(REFERENCE, [RULES, INDIVIDUAL])
        self.assertEqual([x["cost"] for x in got["options"]], [60, 85])
        self.assertEqual((got["budget"], got["deadline"], got["local_only"]), (100, 5, False))

    def test_complete_current_overrides_older_joint(self):
        got = guarded.read_fixed_pair_scope(INDIVIDUAL, [RULES, JOINT])
        self.assertEqual([x["cost"] for x in got["options"]], [60, 85])

    def test_newer_joint_blocks_stale_older_options(self):
        got = guarded.read_fixed_pair_scope(REFERENCE, [RULES, INDIVIDUAL, JOINT])
        self.assertIsNone(got["options"])

    def test_current_partial_blocks_old_fallback(self):
        got = guarded.read_fixed_pair_scope(REFERENCE + " Option A: cost 90 euros.", [INDIVIDUAL])
        self.assertIsNone(got["options"])

    def test_reference_and_separate_current_options_are_allowed(self):
        current = REFERENCE + " " + INDIVIDUAL
        self.assertFalse(guarded.ambiguous_typed_pair(current))
        got = guarded.read_fixed_pair_scope(current, [RULES])
        self.assertEqual([x["cost"] for x in got["options"]], [60, 85])

    def test_incomplete_joint_does_not_trigger_unsupported_repair(self):
        current = "Option A and Option B: cost 70 euros."
        self.assertIsNone(guarded.read_fixed_pair_scope(current, [INDIVIDUAL])["options"])

    def test_invalid_source_inputs_fail_closed(self):
        for bad in (True, 1, None):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "OPTION_SOURCE_INPUT_INVALID"):
                guarded.read_fixed_pair_scope(bad, [INDIVIDUAL])
        with self.assertRaisesRegex(ValueError, "OPTION_SOURCE_INPUT_INVALID"):
            guarded.read_fixed_pair_scope(REFERENCE, [INDIVIDUAL, 7])
        with self.assertRaisesRegex(ValueError, "OPTION_SOURCE_INPUT_INVALID"):
            guarded.option_with_pair_scope("C", REFERENCE, [INDIVIDUAL])


if __name__ == "__main__":
    unittest.main()
