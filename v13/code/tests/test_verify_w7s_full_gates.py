"""Independent W1-W6 raw-confidence replay; synthetic fixtures only."""
import copy
import json
from pathlib import Path
import unittest

from scripts import verify_w7s_full_gates as full
from tests import test_verify_w7s_world_jepa_report as fixture_module


class W7SFullGateReplayTests(unittest.TestCase):
    def setUp(self):
        self.helper = fixture_module.W7SIndependentReplayTests(
            "test_positive_nine_row_replay_is_not_native_proof")
        self.helper.setUp()
        self.data = self.helper.data
        self.work = self.helper.work
        self.result = self.helper.result
        self.raw = {}
        for arm in full.base.ARMS:
            self.raw[arm] = []
            for i, row in enumerate(self.data[arm]):
                row["collapse"] = {"effective_rank": 5, "min_std": .1}
                row["confidence"] = {"held_out_all_uncertain": True}
                row["cf_retrieval"].update({
                    "jepa_held_out": .5,
                    "no_action_covered": .4,
                    "shuffled_action_covered": .4,
                    "ridge_obs_covered_info": .5,
                })
                raw = dict(copy.deepcopy(row),
                           _conf_err=[[.1 + i * .1, .3 - i * .1]])
                self.raw[arm].append(raw)
            gates, summary = full.replay_arm(self.raw[arm])
            self.data[arm + "_gates"] = gates
            self.data[arm + "_summary"] = summary
        self.write()

    def tearDown(self):
        self.helper.tearDown()

    def write(self):
        self.result.write_text(json.dumps(self.data), encoding="utf-8")
        for arm in full.base.ARMS:
            for row in self.raw[arm]:
                (self.work / f"{arm}-{row['seed']}-RESULT.json").write_text(
                    json.dumps(row), encoding="utf-8")

    def test_complete_nine_row_w1_w7_raw_replay(self):
        report = full.verify(self.result, self.work)
        self.assertEqual(report["status"],
                         "W7S_W1_W7_FULL_RAW_REPLAY_VERIFIED_SHADOW")
        self.assertTrue(report["w1_w6_verified"])
        self.assertFalse(report["native_proof"])
        self.assertFalse(report["promotion"])

    def test_false_w4_gate_refused(self):
        self.data["balanced_slot_gates"]["W4_confidence_tracks_error"] = False
        self.write()
        with self.assertRaisesRegex(ValueError, "W1_W6_GATES"):
            full.verify(self.result, self.work)

    def test_wrong_spearman_summary_refused(self):
        self.data["two_slot_summary"]["spearman_conf_err_covered"] = .5
        self.write()
        with self.assertRaisesRegex(ValueError, "W1_W6_SUMMARY"):
            full.verify(self.result, self.work)

    def test_missing_raw_pairs_refused(self):
        self.raw["six_slot"][0].pop("_conf_err")
        self.write()
        with self.assertRaisesRegex(ValueError, "W1_W6_RAW_CONF_ERR"):
            full.verify(self.result, self.work)

    def test_tampered_control_metric_refused(self):
        self.data["balanced_slot"][0]["cf_retrieval"]["no_action_covered"] = .9
        self.raw["balanced_slot"][0]["cf_retrieval"]["no_action_covered"] = .9
        self.write()
        with self.assertRaisesRegex(ValueError, "W1_W6_"):
            full.verify(self.result, self.work)

    def test_nonfinite_raw_pair_refused(self):
        self.raw["two_slot"][1]["_conf_err"][0][1] = float("nan")
        self.write()
        with self.assertRaisesRegex(ValueError, "NONFINITE_JSON"):
            full.verify(self.result, self.work)

    def test_red_remains_red(self):
        self.data["status"] = "RED"
        self.write()
        report = full.verify(self.result, self.work)
        self.assertEqual(report["status"], "ORIGINAL_RED_OR_INCOMPLETE")
        self.assertFalse(report["w1_w6_verified"])


if __name__ == "__main__":
    unittest.main()
