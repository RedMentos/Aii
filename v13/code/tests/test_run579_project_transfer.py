"""Run579 fixed 12-case exact-source project transfer software ablation tests."""
import unittest
from scripts import run579_project_transfer as R


class ProjectTransferRun579(unittest.TestCase):
    def test_fixed_disjoint_cohort_and_oracles(self):
        self.assertEqual(len(R.CASES), 12)
        self.assertEqual(len({case[0] for case in R.CASES}), 12)
        self.assertEqual([c[-1] for c in R.CASES[:6]], ["UNKNOWN"] * 6)
        self.assertEqual([c[-1] for c in R.CASES[6:]],
                         ["A", "B", "NONE", "A", "NONE", "B"])
        self.assertTrue(all(c[0] != c[1] for c in R.CASES[:6]))
        self.assertTrue(all(c[0] == c[1] for c in R.CASES[6:]))

    def test_real_sqlite_negative_transfer_and_same_project(self):
        baseline = R.run_case(R.CASES[0], "BASELINE")
        scoped = R.run_case(R.CASES[0], "SCOPED")
        self.assertEqual(baseline["action"], "A")
        self.assertTrue(baseline["wrong_committed"])
        self.assertEqual(scoped["action"], "UNKNOWN")
        self.assertFalse(scoped["wrong_committed"])
        same = R.run_case(R.CASES[7], "SCOPED")
        self.assertEqual(same["action"], "B")
        self.assertTrue(same["exact"])
        self.assertEqual(baseline["history_sha256"], scoped["history_sha256"])
        self.assertEqual(baseline["current_sha256"], scoped["current_sha256"])

    def test_full_pre_registered_ablation(self):
        report = R.run_ablation()
        self.assertEqual(report["status"], "DESIGNED_CONTROLS_PASS", report["by_arm"])
        self.assertEqual(report["by_arm"]["BASELINE"],
                         {"n": 12, "exact": 6, "cross_wrong_committed": 6,
                          "same_project_exact": 6})
        self.assertEqual(report["by_arm"]["SCOPED"],
                         {"n": 12, "exact": 12, "cross_wrong_committed": 0,
                          "same_project_exact": 6})
        self.assertEqual(len(report["rows"]), 24)
        self.assertIs(report["native_executed"], False)
        self.assertIs(report["model_called"], False)
        self.assertIs(report["canonical_gate_pass"], False)
        self.assertEqual(report["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(report["jepa_weight"], 0)

    def test_unknown_arm_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_ARM"):
            R.run_case(R.CASES[0], "FUTURE")


if __name__ == "__main__":
    unittest.main()
