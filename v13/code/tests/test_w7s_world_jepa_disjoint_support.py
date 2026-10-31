"""Software-only prereg checks for disjoint World-JEPA W7 support experiment."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import w7s_world_jepa_disjoint_support_real as exp
from scripts import z12b_world_jepa as original


class WorldJepaW7SupportTests(unittest.TestCase):
    def test_disjoint_cohort_and_original_gates_fixed(self):
        self.assertEqual(exp.SEEDS, (601, 602, 603))
        self.assertEqual(exp.ARGS, {"train": 4000, "cf": 150,
                                    "attr": 900, "steps": 3000})
        self.assertTrue(set(exp.SEEDS).isdisjoint({101, 102, 103,
                                                   201, 202, 203,
                                                   301, 302, 303,
                                                   401, 402, 403,
                                                   501, 502, 503}))
        self.assertEqual([name for name, _ in exp.ARMS],
                         ["two_slot", "six_slot", "balanced_slot"])

    def test_exact_frozen_source_blob_pins(self):
        exp.assert_frozen_sources()
        with patch.dict(exp.FROZEN, {"world_jepa_blob": "0" * 40}):
            with self.assertRaisesRegex(ValueError, "W7S_SOURCE_PIN_RED"):
                exp.assert_frozen_sources()

    def test_support_partition_matches_original_attr_eval(self):
        rows = [
            {"a": 0, "world_changed": False, "ambiguous": False},
            {"a": 0, "world_changed": True, "ambiguous": False},
            {"a": original.NOOP, "world_changed": True, "ambiguous": False},
            {"a": original.NOOP, "world_changed": False, "ambiguous": False},
            {"a": 0, "world_changed": True, "ambiguous": True},
        ]
        self.assertEqual(exp.attribution_support(rows), {
            "own_only": 1, "both": 1, "world_only": 1, "none": 1})
        self.assertEqual(sum(exp.attribution_support(rows).values()), 4)

    def test_original_w7_floor_15_preserved(self):
        counts = {k: 15 for k in ("own_only", "world_only",
                                   "both", "none")}
        scores = {"own_only_self": 0.8, "world_only_world": 0.7,
                  "both_world": 0.7, "none_self": 0.8,
                  "balanced": 0.75}
        rows = []
        for seed in exp.SEEDS:
            rows.append({"seed": seed, "attribution": {
                "jepa": dict(scores, n=dict(counts)),
                "no_action": dict(scores, n=dict(counts))}})
        gates, summary = exp.w7(rows)
        self.assertEqual(set(gates), {
            "W7a_both_world_action_gain",
            "W7b_none_self_action_gain",
            "W7c_four_class_macro_action_gain"})
        self.assertFalse(any(gates.values()))
        self.assertEqual(len(summary["per_seed"]), 3)
        rows[0]["attribution"]["jepa"]["n"]["world_only"] = 14
        rows[0]["attribution"]["no_action"]["n"]["world_only"] = 14
        with self.assertRaisesRegex(ValueError, "W7S_W7_SUPPORT"):
            exp.w7(rows)

    def test_mutated_cohort_fails_before_creating_workdir(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out, work = root / "out.json", root / "work"
            with self.assertRaisesRegex(ValueError, "W7S_COHORT_MUTATION"):
                exp.run(out, work, seeds=(601, 602, 999))
            self.assertFalse(out.exists())
            self.assertFalse(work.exists())
            with self.assertRaisesRegex(ValueError, "W7S_COHORT_MUTATION"):
                exp.run(out, work, args=dict(exp.ARGS, attr=300))
            self.assertFalse(work.exists())


if __name__ == "__main__":
    unittest.main()
