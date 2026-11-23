"""Source-only composed Context OS scope review; no native/learning claim."""
import os
from pathlib import Path
import unittest

from scripts import context_option_safe_scope_candidate as safe
from scripts import context_option_reference_candidate as original_reader
from scripts import step2_exact_rule_native_replay_preflight as frozen


BETA_TASK = (
    "Project Beta. Budget 100 euros. Deadline 5 days. "
    "Local-only requirement: false. Decide between Option A and Option B from earlier sheet."
)
BETA_OPTIONS = (
    "Project Beta supplier sheet. "
    "Option A: cost 60 euros, duration 3 days, local true. "
    "Option B: cost 85 euros, duration 4 days, local false."
)
ALPHA_OPTIONS = BETA_OPTIONS.replace("Project Beta", "Project Alpha")
BETA_JOINT = (
    "Project Beta. Option A and Option B: cost 60 euros, duration 3 days, local true."
)


class ComposedSourceScope(unittest.TestCase):
    def test_original_cross_project_red_witness_is_refused(self):
        self.assertIsNotNone(original_reader.read_fixed_reference(
            BETA_TASK, [ALPHA_OPTIONS])["options"])
        self.assertEqual(safe.decide_safe(BETA_TASK, [ALPHA_OPTIONS])["action"], "UNKNOWN")

    def test_original_unscoped_pair_red_witness_is_refused(self):
        original = original_reader.read_fixed_reference(BETA_JOINT, [BETA_OPTIONS])
        self.assertEqual([o["cost"] for o in original["options"]], [60, 60])
        self.assertIsNone(safe.read_fixed_safe(BETA_JOINT, [BETA_OPTIONS])["options"])

    def test_valid_same_project_history_decides(self):
        got = safe.decide_safe(BETA_TASK, [BETA_OPTIONS])
        self.assertEqual(got["action"], "A")
        self.assertEqual([o["cost"] for o in got["values"]["options"]], [60, 85])
        self.assertEqual(got["scope"], safe.SCOPE)

    def test_foreign_interleaving_is_skipped(self):
        got = safe.decide_safe(BETA_TASK, [BETA_OPTIONS, ALPHA_OPTIONS])
        self.assertEqual(got["action"], "A")

    def test_newer_same_project_joint_blocks_old_options(self):
        got = safe.decide_safe(BETA_TASK, [BETA_OPTIONS, BETA_JOINT])
        self.assertEqual(got["action"], "UNKNOWN")

    def test_current_partial_update_blocks_history(self):
        got = safe.decide_safe(BETA_TASK + " Option A: cost 90 euros.", [BETA_OPTIONS])
        self.assertEqual(got["action"], "UNKNOWN")

    def test_no_project_can_use_current_only(self):
        current = (
            "Budget 100 euros. Deadline 5 days. Local-only requirement: false. "
            "Option A: cost 60 euros, duration 3 days, local true. "
            "Option B: cost 85 euros, duration 4 days, local false."
        )
        self.assertEqual(safe.decide_safe(current, [ALPHA_OPTIONS])["action"], "A")

    def test_ambiguous_current_project_abstains(self):
        got = safe.decide_safe(BETA_TASK + " Project Alpha.", [BETA_OPTIONS])
        self.assertEqual(got["action"], "UNKNOWN")
        self.assertIsNone(got["values"]["options"])

    def test_invalid_input_rejected_before_read(self):
        with self.assertRaisesRegex(ValueError, "CONTEXT_SOURCE_INPUT_INVALID"):
            safe.decide_safe(BETA_TASK, [BETA_OPTIONS, True])
        with self.assertRaisesRegex(ValueError, "CONTEXT_SOURCE_INPUT_INVALID"):
            safe.read_fixed_safe(True, [BETA_OPTIONS])

    def test_original_six_fixture_full_history_posthoc_if_supplied(self):
        path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        if not path:
            self.skipTest("original frozen source raw not supplied")
        source = frozen.load_original(Path(path))
        self.assertFalse(source["canonical_gate_pass"])
        self.assertEqual(len(source["fixtures"]), 6)
        for fixture in source["fixtures"]:
            with self.subTest(project=fixture["id"]):
                got = safe.decide_safe(fixture["current"], fixture["history"])
                self.assertEqual(got["action"], fixture["oracle"]["action"])
                self.assertEqual(got["scope"], safe.SCOPE)


if __name__ == "__main__":
    unittest.main()
