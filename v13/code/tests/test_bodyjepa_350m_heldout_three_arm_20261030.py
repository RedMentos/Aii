"""Software-only seed101 Body-JEPA heldout ablation contract tests."""
import subprocess
import sys
import unittest
from pathlib import Path

from scripts import bodyjepa_350m_heldout_three_arm_20261030 as a


def arm(ce=1.0, kl=0.01, near=0.01):
    return {"steps": 4, "frozen_unchanged": True, "adapter_delta_l2": 0.1,
            "heldout_ce": ce, "train_ce": 0.5, "retention_kl": kl,
            "near_miss_kl": near}


class HeldoutThreeArmContract(unittest.TestCase):
    def test_frozen_fixture_and_no_overlap(self):
        d = a.frozen()
        self.assertEqual(a.blob_sha(a.FIXTURE), a.FIXTURE_BLOB)
        self.assertEqual(len(d["rows"]), 8)
        self.assertEqual(len(d["retention_anchors"]), 8)
        self.assertEqual(len({r["source_id"] for r in d["rows"]}), 8)
        self.assertEqual(len({r["target"] for r in d["rows"]}), 8)
        self.assertEqual(d["seed"], 101)

    def test_fixed_true_derangement(self):
        self.assertEqual(sorted(a.PERM), list(range(8)))
        self.assertTrue(all(i != v for i, v in enumerate(a.PERM)))

    def test_exact_signal_threshold(self):
        arms = {"CE_ONLY": arm(1.0), "CE_EMA_JEPA": arm(.94),
                "CE_SHUFFLED_JEPA": arm(.99)}
        self.assertEqual(a.score(arms), "HELDOUT_JEPA_PILOT_SIGNAL")

    def test_no_gain_is_negative(self):
        arms = {"CE_ONLY": arm(1.0), "CE_EMA_JEPA": arm(1.01),
                "CE_SHUFFLED_JEPA": arm(.99)}
        self.assertEqual(a.score(arms), "HELDOUT_BENEFIT_NOT_PROVEN")

    def test_shuffled_equal_or_better_blocks_signal(self):
        arms = {"CE_ONLY": arm(1.0), "CE_EMA_JEPA": arm(.94),
                "CE_SHUFFLED_JEPA": arm(.95)}
        self.assertEqual(a.score(arms), "HELDOUT_BENEFIT_NOT_PROVEN")

    def test_retention_and_nearmiss_guard(self):
        for kw in ({"kl": .06}, {"near": .06}):
            arms = {"CE_ONLY": arm(1.0), "CE_EMA_JEPA": arm(.94, **kw),
                    "CE_SHUFFLED_JEPA": arm(.99)}
            self.assertEqual(a.score(arms), "HELDOUT_BENEFIT_NOT_PROVEN")

    def test_missing_arm_is_partial_red(self):
        self.assertEqual(a.score({"CE_ONLY": arm()}), "PILOT_PARTIAL_RED")

    def test_nonfinite_or_unchanged_is_partial_red(self):
        arms = {"CE_ONLY": arm(1.0), "CE_EMA_JEPA": arm(.94),
                "CE_SHUFFLED_JEPA": arm(.99)}
        arms["CE_EMA_JEPA"]["heldout_ce"] = float("nan")
        self.assertEqual(a.score(arms), "PILOT_PARTIAL_RED")
        arms["CE_EMA_JEPA"] = arm(.94)
        arms["CE_EMA_JEPA"]["adapter_delta_l2"] = 0
        self.assertEqual(a.score(arms), "PILOT_PARTIAL_RED")

    def test_native_optin_required(self):
        p = subprocess.run(
            [sys.executable, str(Path(a.__file__)), "--master", "/nonexistent/master",
             "--out", "/nonexistent/report"],
            capture_output=True, text=True, timeout=15)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--execute-native", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_model_and_runtime_gates(self):
        self.assertEqual(a.SEED, 101)
        self.assertEqual(a.STEPS, 4)
        self.assertEqual(a.JEPA_WEIGHT, .2)
        self.assertEqual(a.EMA_DECAY, .9)
        self.assertEqual(len(a.MASTER_SHA256), 64)
        self.assertEqual(a.ARMS, ("CE_ONLY", "CE_EMA_JEPA", "CE_SHUFFLED_JEPA"))


if __name__ == "__main__":
    unittest.main()
