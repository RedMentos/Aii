"""Model-free preregistration and verdict tests for Body-JEPA 350M heldout NLL.

The real FP32 model experiment is a separate Actions step, not a unit-test claim.
"""
import subprocess
import sys
from pathlib import Path
import unittest

from scripts import bodyjepa_350m_heldout_ablation_20261030 as a


def fake(ce, ema, wrong):
    def row(v):
        return {"summary": {
            "paraphrase": v,
            "near_miss_leak_proxy": 2.0,
            "retention": 1.0,
            "train": v,
        }}
    return {str(seed): {"CE": row(ce), "EMA": row(ema), "SHUFFLED": row(wrong)}
            for seed in a.SEEDS}


class BodyJepaHeldoutProtocol(unittest.TestCase):
    def test_exact_preregistered_source_and_disjoint_queries(self):
        f = a.fixture()
        self.assertEqual({k: len(v) for k, v in f.items()},
                         {"train": 4, "paraphrase": 4,
                          "near_miss_leak_proxy": 4, "retention": 4})
        self.assertEqual(len({q for rows in f.values() for q, _ in rows}), 16)
        self.assertEqual(a.fixture_sha(f),
                         "be4925666ef6ffc2206dc450f775dee8ac7a6eb21fbc67082a0f49f1e3804e95")
        self.assertEqual(a.SEEDS, (73, 79, 83))
        self.assertEqual(a.ARMS, ("CE", "EMA", "SHUFFLED"))
        self.assertEqual(a.CONFIG["max_steps"], 2)
        self.assertEqual(a.CONFIG["anchor_weight"], 0.)
        self.assertEqual(a.CONFIG["locality_swaps"], 0)

    def test_signal_is_diagnostic_only_and_requires_wrong_target_control(self):
        s = a.verdict(fake(1.0, .80, 1.0))
        self.assertEqual(s["status"], "BOUNDED_NLL_SIGNAL_NOT_UTILITY_GATE")
        self.assertFalse(s["utility_gate_pass"])
        self.assertEqual(s["seed_wins"], 3)
        no_gain = a.verdict(fake(1.0, .99, 1.0))
        self.assertEqual(no_gain["status"], "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        self.assertFalse(no_gain["utility_gate_pass"])
        hurt = a.verdict(fake(1.0, 1.2, 1.0))
        self.assertEqual(hurt["status"], "DIAGNOSTIC_HURT")

    def test_missing_arm_or_seed_is_never_a_completed_result(self):
        x = fake(1., .8, 1.)
        del x["73"]["SHUFFLED"]
        with self.assertRaisesRegex(ValueError, "Incomplete arm"):
            a.verdict(x)
        x = fake(1., .8, 1.)
        del x["79"]
        with self.assertRaisesRegex(ValueError, "Incomplete seed"):
            a.verdict(x)

    def test_trainer_does_not_export_adapters(self):
        obj = a.ExportFreeTrainer.__new__(a.ExportFreeTrainer)
        self.assertEqual(obj._export(None, None, None, None),
                         {"gguf": "NO_EXPORT", "gguf_sha256": None})

    def test_native_execution_is_opt_in(self):
        p = Path(a.__file__)
        result = subprocess.run(
            [sys.executable, str(p), "--master", "/nonexistent/master",
             "--out", "/nonexistent/result"],
            capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--execute-native", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
