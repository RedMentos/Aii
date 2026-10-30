"""Run32 W7 prereg thresholds, original W1..W6 containment, path isolation."""
from __future__ import annotations

import copy
import math
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import run32_world_jepa_disjoint_attribution as run32


def seed_row(seed, both_gap=.35, none_gap=.15, own_gap=.0, world_gap=.0):
    base = {"own_only_self": .8, "world_only_world": .9,
            "both_world": .45, "none_self": .7,
            "n": {"own_only": 40, "world_only": 20, "both": 40, "none": 30}}
    candidate = copy.deepcopy(base)
    candidate["own_only_self"] += own_gap
    candidate["world_only_world"] += world_gap
    candidate["both_world"] += both_gap
    candidate["none_self"] += none_gap
    return {"seed": seed, "attribution": {"jepa": candidate, "no_action": base}}


class Run32DisjointAttribution(unittest.TestCase):
    def rows(self, **kw):
        return [seed_row(s, **kw) for s in run32.SEEDS]

    def test_preregistered_three_seeds_and_thresholds(self):
        gates, summary = run32.four_class_attribution(self.rows())
        self.assertTrue(all(gates.values()))
        self.assertEqual(len(summary["per_seed"]), 3)
        self.assertEqual(summary["mean_both_world_gap"], .35)
        self.assertEqual(summary["mean_none_self_gap"], .15)
        self.assertEqual(summary["mean_four_class_macro_gap"], .125)

    def test_action_gap_failure_is_not_waived(self):
        gates, _ = run32.four_class_attribution(self.rows(both_gap=.1, none_gap=.02))
        self.assertFalse(gates["W7a_both_world_action_gain"])
        self.assertFalse(gates["W7b_none_self_action_gain"])
        self.assertFalse(gates["W7c_four_class_macro_action_gain"])

    def test_seed_identity_and_class_support_fail_closed(self):
        rows = self.rows()
        rows[0]["seed"] = 101
        with self.assertRaisesRegex(ValueError, "SEED"):
            run32.four_class_attribution(rows)
        rows = self.rows()
        rows[1]["attribution"]["jepa"]["n"]["both"] = 14
        with self.assertRaisesRegex(ValueError, "SUPPORT"):
            run32.four_class_attribution(rows)
        rows = self.rows()
        rows[2]["attribution"]["no_action"]["n"]["both"] = 39
        with self.assertRaisesRegex(ValueError, "SUPPORT"):
            run32.four_class_attribution(rows)

    def test_nonfinite_or_boolean_rate_fail_closed(self):
        for bad in (float("nan"), float("inf"), True, -1, 2):
            with self.subTest(kind=type(bad).__name__):
                rows = self.rows()
                rows[0]["attribution"]["jepa"]["none_self"] = bad
                with self.assertRaisesRegex(ValueError, "RATE"):
                    run32.four_class_attribution(rows)

    def test_original_w6_remains_required_and_nonfinite_w4_red(self):
        gates = {k: True for k in (
            "W1_cf_retrieval_covered", "W2_controls_fail",
            "W3_no_collapse", "W4_confidence_tracks_error",
            "W5_attribution_jepa", "W6_no_action_attribution_worse")}
        gates["W6_no_action_attribution_worse"] = False
        with patch.object(run32.original, "criteria",
                          return_value=(gates, {"spearman_conf_err_covered": -.5})):
            actual, _ = run32.original_gates([])
        self.assertFalse(actual["W6_no_action_attribution_worse"])
        with patch.object(run32.original, "criteria",
                          return_value=(gates, {"spearman_conf_err_covered": float("nan")})):
            actual, summary = run32.original_gates([])
        self.assertFalse(actual["W4_confidence_tracks_error"])
        self.assertIsNone(summary["spearman_conf_err_covered"])

    def test_fresh_paths_required_before_native_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaisesRegex(FileExistsError, "FRESH"):
                run32.run(base / "result.json", base)


if __name__ == "__main__":
    unittest.main()
