"""Run38 preregistered W7/identity guards without real-file fitting."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.run38_world_jepa_fullslot_real import ARGS, SEEDS, run, w7


def rows():
    out = []
    for seed in SEEDS:
        n = {"own_only": 40, "world_only": 30, "both": 35, "none": 40}
        out.append({"seed": seed, "attribution": {
            "jepa": {"n": n, "own_only_self": .9, "world_only_world": 1.,
                     "both_world": .9, "none_self": .9, "balanced": .925},
            "no_action": {"n": dict(n), "own_only_self": .7,
                          "world_only_world": .7, "both_world": .5,
                          "none_self": .7, "balanced": .65}}})
    return out


class Run38RealfileContract(unittest.TestCase):
    def test_w7_frozen_thresholds_and_exact_seeds(self):
        gates, summary = w7(rows())
        self.assertEqual(gates, {
            "W7a_both_world_action_gain": True,
            "W7b_none_self_action_gain": True,
            "W7c_four_class_macro_action_gain": True})
        self.assertEqual(summary["mean_both_world_gap"], .4)
        self.assertEqual(summary["mean_balanced_gap"], .275)

    def test_w7_support_and_seed_identity_fail_closed(self):
        data = rows()
        data[0]["seed"] = 301
        with self.assertRaisesRegex(ValueError, "SEED_IDENTITY"):
            w7(data)
        data = rows()
        data[1]["attribution"]["jepa"]["n"]["both"] = 14
        data[1]["attribution"]["no_action"]["n"]["both"] = 14
        with self.assertRaisesRegex(ValueError, "SUPPORT"):
            w7(data)

    def test_w7_nonfinite_rejected(self):
        data = rows()
        data[0]["attribution"]["jepa"]["both_world"] = float("nan")
        with self.assertRaisesRegex(ValueError, "NUMERIC"):
            w7(data)

    def test_cohort_mutation_rejected_before_files(self):
        with tempfile.TemporaryDirectory() as d:
            out, work = Path(d) / "result.json", Path(d) / "work"
            with self.assertRaisesRegex(ValueError, "COHORT_MUTATION"):
                run(out, work, seeds=(401, 402), args=ARGS)
            with self.assertRaisesRegex(ValueError, "COHORT_MUTATION"):
                run(out, work, seeds=SEEDS, args={**ARGS, "steps": 500})
            self.assertFalse(out.exists())
            self.assertFalse(work.exists())

    def test_non_linux_or_non_fresh_root_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            out, work = Path(d) / "result.json", Path(d) / "work"
            with patch("scripts.run38_world_jepa_fullslot_real.platform.system",
                       return_value="Windows"):
                with self.assertRaisesRegex(ValueError, "LINUX_REALFILE_ONLY"):
                    run(out, work)
            out.write_text("original")
            with patch("scripts.run38_world_jepa_fullslot_real.platform.system",
                       return_value="Linux"), patch(
                       "scripts.run38_world_jepa_fullslot_real.platform.machine",
                       return_value="x86_64"):
                with self.assertRaisesRegex(FileExistsError, "FRESH_PATHS"):
                    run(out, work)
            self.assertEqual(out.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
