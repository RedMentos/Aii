"""Software-only cross-project source-binding regressions for Run141."""
import unittest

from scripts import context_option_project_scope_candidate as scoped
from scripts import context_option_reference_candidate as parent


BETA_TASK = (
    "Project Beta. Budget 100 euros. Deadline 5 days. "
    "Local-only requirement: false. Decide between Option A and Option B from earlier sheet."
)
ALPHA_OPTIONS = (
    "Project Alpha. Option A: cost 60 euros, duration 3 days, local true. "
    "Option B: cost 85 euros, duration 4 days, local false."
)
BETA_OPTIONS = ALPHA_OPTIONS.replace("Project Alpha.", "Project Beta.")
BETA_RULES = "Project Beta. Budget 100 euros. Deadline 5 days. Local-only requirement: false."


class ProjectSourceScope(unittest.TestCase):
    def test_original_run141_cross_project_leak_red_witness(self):
        result = parent.read_fixed_reference(BETA_TASK, [ALPHA_OPTIONS])
        self.assertEqual([o["cost"] for o in result["options"]], [60, 85])

    def test_foreign_only_history_is_not_borrowed(self):
        result = scoped.read_project_scoped(BETA_TASK, [ALPHA_OPTIONS])
        self.assertIsNone(result["options"])
        self.assertEqual((result["budget"], result["deadline"], result["local_only"]),
                         (100, 5, False))

    def test_matching_project_options_are_recovered(self):
        result = scoped.read_project_scoped(BETA_TASK, [BETA_OPTIONS])
        self.assertEqual([o["cost"] for o in result["options"]], [60, 85])

    def test_interleaved_foreign_history_is_skipped(self):
        result = scoped.read_project_scoped(BETA_TASK, [BETA_OPTIONS, ALPHA_OPTIONS])
        self.assertEqual([o["cost"] for o in result["options"]], [60, 85])

    def test_foreign_newer_rule_does_not_override(self):
        task = "Project Beta. Decide between Option A and Option B from earlier sheet."
        alpha_rule = "Project Alpha. Budget 5 euros. Deadline 1 day. Local-only requirement: true."
        result = scoped.read_project_scoped(task, [BETA_RULES, BETA_OPTIONS, alpha_rule])
        self.assertEqual((result["budget"], result["deadline"], result["local_only"]),
                         (100, 5, False))

    def test_absent_current_project_cannot_borrow_history(self):
        task = "Decide between Option A and Option B from earlier sheet."
        self.assertIsNone(scoped.read_project_scoped(task, [BETA_OPTIONS])["options"])

    def test_current_complete_options_do_not_need_history(self):
        task = BETA_RULES.replace("Project Beta. ", "") + " " + BETA_OPTIONS.replace("Project Beta. ", "")
        result = scoped.read_project_scoped(task, [ALPHA_OPTIONS])
        self.assertEqual([o["cost"] for o in result["options"]], [60, 85])

    def test_conflicting_current_project_labels_fail_closed(self):
        task = BETA_TASK + " Project Alpha."
        self.assertEqual(scoped.read_project_scoped(task, [BETA_OPTIONS]), {
            "budget": None, "deadline": None, "local_only": None, "options": None
        })

    def test_ambiguous_prior_project_label_is_skipped(self):
        bad = BETA_OPTIONS + " Project Alpha."
        self.assertIsNone(scoped.read_project_scoped(BETA_TASK, [bad])["options"])

    def test_casefolded_single_token_label(self):
        self.assertEqual(scoped.project_key("project beta. Supplier sheet."), "beta")
        result = scoped.read_project_scoped(BETA_TASK, [BETA_OPTIONS.lower()])
        self.assertEqual([o["cost"] for o in result["options"]], [60, 85])

    def test_late_project_mention_does_not_authorize_history(self):
        current = "Earlier note mentions Project Beta. Decide between Option A and Option B."
        self.assertIsNone(scoped.project_key(current))
        self.assertIsNone(scoped.read_project_scoped(current, [BETA_OPTIONS])["options"])

    def test_unheaded_prior_project_mention_not_used(self):
        unheaded = "Quoted note: " + BETA_OPTIONS
        self.assertIsNone(scoped.project_key(unheaded))
        self.assertIsNone(scoped.read_project_scoped(BETA_TASK, [unheaded])["options"])

    def test_multiword_name_is_not_guessed(self):
        task = "Project New York. Decide between Option A and Option B."
        self.assertIsNone(scoped.project_key(task))
        self.assertIsNone(scoped.read_project_scoped(task, [BETA_OPTIONS])["options"])

    def test_invalid_inputs_refused(self):
        with self.assertRaisesRegex(ValueError, "PROJECT_SCOPE_SOURCE_INVALID"):
            scoped.read_project_scoped(BETA_TASK, [BETA_OPTIONS, True])
        with self.assertRaisesRegex(ValueError, "PROJECT_SCOPE_SOURCE_INVALID"):
            scoped.read_project_scoped(True, [BETA_OPTIONS])
        with self.assertRaisesRegex(ValueError, "PROJECT_SCOPE_SOURCE_INVALID"):
            scoped.project_key(None)


if __name__ == "__main__":
    unittest.main()
