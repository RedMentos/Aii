"""Run393 source-bound, non-promoting STEP2 access/utility diagnostic tests."""
import copy
import hashlib
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run393_step2_access_utility as a
from step2_z2_timescale import FIXTURES


class Run393Step2Access(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports, cls.hashes = a.load_reports(a.INPUT, FIXTURES)

    def test_original_nine_sources_are_complete_and_hash_bound(self):
        self.assertEqual(len(self.reports), 9)
        self.assertEqual(len(self.hashes), 9)
        for name, expected in self.hashes.items():
            self.assertEqual(hashlib.sha256((a.INPUT / name).read_bytes()).hexdigest(), expected)
        for (arm, seed), j in self.reports.items():
            self.assertIs(a.validate_summary(j, arm, seed, FIXTURES), j)

    def test_actual_output_is_exploratory_and_complete(self):
        out = a.analyze(self.reports, self.hashes, FIXTURES)
        self.assertEqual(out["status"], "EXPLORATORY_RECORDED")
        self.assertIs(out["canonical_gate_pass"], False)
        self.assertEqual(out["step2_exit"], "UTILITY_FAIL")
        self.assertFalse(out["native_rerun"])
        for arm in ("CQA", "CQP"):
            groups = out["access_transition_associations"][arm]
            n = sum(x["n_paired_rows"] for key, x in groups.items() if key.startswith("ALL|ALL|"))
            self.assertEqual(n, 3 * 8 * 4)
            self.assertEqual(out["paired_fixture_cluster_bootstrap"][arm]["both_exact_minus_CQ_both_exact"]["fixtures"], 10)
        self.assertEqual(sum(v["wrong_committed_tool"] for v in out["safety"].values()), 0)

    def test_missing_source_row_refused_not_treated_as_zero(self):
        j = copy.deepcopy(self.reports[("CQP", 17)])
        j["z2c"]["b2_rule_rows"].pop(next(iter(j["z2c"]["b2_rule_rows"])))
        with self.assertRaisesRegex(ValueError, "missing/extra"):
            a.validate_summary(j, "CQP", 17, FIXTURES)

    def test_extra_source_row_refused(self):
        j = copy.deepcopy(self.reports[("CQP", 17)])
        j["episode_utility_tool"]["fabricated:both_exact"] = 1.0
        with self.assertRaisesRegex(ValueError, "missing/extra"):
            a.validate_summary(j, "CQP", 17, FIXTURES)

    def test_nonfinite_or_boolean_utility_refused(self):
        for value in (float("nan"), float("inf"), -1, True, "0.8"):
            with self.subTest(value=repr(value)):
                j = copy.deepcopy(self.reports[("CQP", 17)])
                j["episode_utility_tool"]["Kestrel:both_exact"] = value
                with self.assertRaisesRegex(ValueError, "invalid utility"):
                    a.validate_summary(j, "CQP", 17, FIXTURES)

    def test_string_access_flag_refused(self):
        j = copy.deepcopy(self.reports[("CQ", 17)])
        j["z2c"]["b2_rule_rows"]["Kestrel:both_exact"]["rules"] = "true"
        with self.assertRaisesRegex(ValueError, "invalid B2"):
            a.validate_summary(j, "CQ", 17, FIXTURES)

    def test_transition_math_and_unchanged_access_control(self):
        reports = copy.deepcopy(self.reports)
        for seed in a.SEEDS:
            for key in reports[("CQ", seed)]["z2c"]["b2_rule_rows"]:
                reports[("CQ", seed)]["z2c"]["b2_rule_rows"][key]["rules"] = False
                reports[("CQA", seed)]["z2c"]["b2_rule_rows"][key]["rules"] = False
                reports[("CQP", seed)]["z2c"]["b2_rule_rows"][key]["rules"] = True
                reports[("CQ", seed)]["episode_utility_tool"][key] = .2
                reports[("CQA", seed)]["episode_utility_tool"][key] = .3
                reports[("CQP", seed)]["episode_utility_tool"][key] = .8
        out = a.analyze(reports, {}, FIXTURES)
        gained = out["access_transition_associations"]["CQP"]["ALL|ALL|gained"]
        never = out["access_transition_associations"]["CQA"]["ALL|ALL|never"]
        self.assertEqual(gained["n_paired_rows"], 96)
        self.assertAlmostEqual(gained["mean_utility_delta"], .6)
        self.assertEqual(never["n_paired_rows"], 96)
        self.assertAlmostEqual(never["mean_utility_delta"], .1)
        self.assertIs(out["canonical_gate_pass"], False)

    def test_repeated_bootstrap_is_deterministic(self):
        x = a.analyze(self.reports, self.hashes, FIXTURES)
        y = a.analyze(self.reports, self.hashes, FIXTURES)
        self.assertEqual(x, y)
        self.assertEqual(x["paired_fixture_cluster_bootstrap"]["CQP"]["both_exact_minus_CQ_both_exact"]["bootstrap_seed"], a.BOOT_SEED)


if __name__ == "__main__":
    unittest.main()
