"""Run39 frozen cohort/W7 and three-arm runner synthetic contract."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts.run39_world_jepa_action_balanced_real import (
    ARGS, ARMS, SEEDS, run, w7,
)


def rows():
    result = []
    for seed in SEEDS:
        n = {"own_only": 40, "world_only": 30, "both": 35, "none": 40}
        result.append({"seed": seed, "attribution": {
            "jepa": {"n": n, "own_only_self": .9, "world_only_world": 1.,
                     "both_world": .9, "none_self": .9, "balanced": .95},
            "no_action": {"n": dict(n), "own_only_self": .7,
                          "world_only_world": .7, "both_world": .5,
                          "none_self": .7, "balanced": .7}}})
    return result


class Run39RealfileContract(unittest.TestCase):
    def test_w7_frozen_thresholds_and_exact_seeds(self):
        gates, summary = w7(rows())
        self.assertEqual(gates, {
            "W7a_both_world_action_gain": True,
            "W7b_none_self_action_gain": True,
            "W7c_four_class_macro_action_gain": True})
        self.assertEqual(summary["mean_both_world_gap"], .4)
        self.assertEqual(summary["mean_balanced_gap"], .25)

    def test_w7_rejects_wrong_seed_support_and_nonfinite(self):
        data = rows()
        data[0]["seed"] = 401
        with self.assertRaisesRegex(ValueError, "SEED_IDENTITY"):
            w7(data)
        data = rows()
        data[1]["attribution"]["jepa"]["n"]["both"] = 14
        data[1]["attribution"]["no_action"]["n"]["both"] = 14
        with self.assertRaisesRegex(ValueError, "SUPPORT"):
            w7(data)
        data = rows()
        data[0]["attribution"]["no_action"]["balanced"] = float("nan")
        with self.assertRaisesRegex(ValueError, "NUMERIC"):
            w7(data)

    def test_cohort_mutation_fails_before_any_file(self):
        with tempfile.TemporaryDirectory() as d:
            out, work = Path(d) / "result.json", Path(d) / "work"
            with self.assertRaisesRegex(ValueError, "COHORT_MUTATION"):
                run(out, work, seeds=(501, 502), args=ARGS)
            with self.assertRaisesRegex(ValueError, "COHORT_MUTATION"):
                run(out, work, seeds=SEEDS, args={**ARGS, "steps": 600})
            self.assertFalse(out.exists())
            self.assertFalse(work.exists())

    def test_mock_end_to_end_three_arms_preserves_all_negatives(self):
        train = [{"x": np.zeros(60), "x2": np.ones(60), "a": 0, "world": False}
                 for _ in range(20)]
        def fake_eval(seed, cls, *args):
            counts = {"own_only": 30, "world_only": 30, "both": 30, "none": 30}
            rates = {"n": counts, "own_only_self": .8, "world_only_world": .8,
                     "both_world": .8, "none_self": .8, "balanced": .8}
            return {"seed": seed, "cf_retrieval": {"jepa_covered": .7},
                    "attribution": {"jepa": rates,
                                    "no_action": {**rates, "n": dict(counts)}},
                    "_conf_err": [[.1, .2]]}
        gates = {"W1_cf_retrieval_covered": False, "W2_controls_fail": False,
                 "W3_no_collapse": True, "W4_confidence_tracks_error": False,
                 "W5_attribution_jepa": True, "W6_no_action_attribution_worse": False}
        with tempfile.TemporaryDirectory() as d:
            out, work = Path(d) / "result.json", Path(d) / "work"
            with patch("scripts.run39_world_jepa_action_balanced_real.platform.system",
                       return_value="Linux"), patch(
                       "scripts.run39_world_jepa_action_balanced_real.platform.machine",
                       return_value="x86_64"), patch(
                       "scripts.run39_world_jepa_action_balanced_real.original.collect_train",
                       return_value=train), patch(
                       "scripts.run39_world_jepa_action_balanced_real.original.collect_cf",
                       return_value=[]), patch(
                       "scripts.run39_world_jepa_action_balanced_real.original.collect_attr",
                       return_value=[]), patch(
                       "scripts.run39_world_jepa_action_balanced_real.evaluate",
                       side_effect=fake_eval), patch(
                       "scripts.run39_world_jepa_action_balanced_real.original_gates",
                       return_value=(gates, {})):
                result = run(out, work)
            self.assertEqual(result["status"], "SHADOW_CANDIDATE_FAIL")
            self.assertEqual(result["seeds"], [501, 502, 503])
            self.assertEqual(result["affected_slot_copies"], 5)
            self.assertFalse(result["same_training_example_count"])
            self.assertEqual(result["step2"], "UTILITY_FAIL")
            self.assertEqual(result["jepa_weight"], 0)
            self.assertFalse(result["whole_system_complete"])
            for arm, _ in ARMS:
                self.assertEqual(len(result[arm]), 3)
                for seed in SEEDS:
                    self.assertTrue((work / f"{arm}-{seed}-RESULT.json").exists())
            self.assertNotIn("_conf_err", out.read_text())

    def test_non_linux_and_existing_result_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            out, work = Path(d) / "result.json", Path(d) / "work"
            with patch("scripts.run39_world_jepa_action_balanced_real.platform.system",
                       return_value="Windows"):
                with self.assertRaisesRegex(ValueError, "LINUX_REALFILE_ONLY"):
                    run(out, work)
            out.write_text("original")
            with patch("scripts.run39_world_jepa_action_balanced_real.platform.system",
                       return_value="Linux"), patch(
                       "scripts.run39_world_jepa_action_balanced_real.platform.machine",
                       return_value="x86_64"):
                with self.assertRaisesRegex(FileExistsError, "FRESH_PATHS"):
                    run(out, work)
            self.assertEqual(out.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
