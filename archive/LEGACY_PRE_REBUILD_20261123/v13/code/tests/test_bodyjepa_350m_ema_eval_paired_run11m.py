"""Model-free preregistration and strict verdict tests for 350M eval-target follow-up."""
from __future__ import annotations

import math
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import bodyjepa_350m_ema_eval_paired_run11m as a
from scripts import bodyjepa_350m_heldout_ablation_20261030 as old


def fake(ce=1., train=1., eval_=0.8, shuffled=1., near_eval=2., retention_eval=1.):
    def row(p, near=2., retention=1.):
        return {"summary": {"train": p, "paraphrase": p,
                            "near_miss_leak_proxy": near, "retention": retention}}
    return {str(seed): {"CE": row(ce), "EMA_TRAIN": row(train),
                        "EMA_EVAL": row(eval_, near_eval, retention_eval),
                        "SHUFFLED": row(shuffled)}
            for seed in a.SEEDS}


class BodyJepa350mEvalPairedRun11M(unittest.TestCase):
    def test_exact_existing_fixture_and_model_source_pins(self):
        rows = a.fixture()
        self.assertEqual(rows, old.fixture())
        self.assertEqual(a.fixture_sha(rows),
                         "be4925666ef6ffc2206dc450f775dee8ac7a6eb21fbc67082a0f49f1e3804e95")
        self.assertEqual(a.MASTER_SHA256,
                         "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e")
        self.assertEqual(a.SEEDS, (73, 79, 83))
        self.assertEqual(a.ARMS, ("CE", "EMA_TRAIN", "EMA_EVAL", "SHUFFLED"))
        self.assertEqual(len(a.SEEDS) * len(a.ARMS), 12)
        self.assertEqual(a.CONFIG, old.CONFIG)
        self.assertEqual(a.CONFIG["max_steps"], 2)

    def test_only_ema_eval_arm_has_opt_in_flag(self):
        for arm in a.ARMS:
            cfg = a.arm_cfg(73, arm)
            self.assertEqual(cfg.get("jepa_target_eval", False), arm == "EMA_EVAL")
            self.assertEqual(cfg["jepa_weight"], 0. if arm == "CE" else .5)
            self.assertEqual(cfg["jepa_target"],
                             "shuffled" if arm == "SHUFFLED" else "ema")
        self.assertNotIn("jepa_target_eval", a.CONFIG)
        with self.assertRaises(ValueError):
            a.arm_cfg(1, "EMA_EVAL")
        with self.assertRaises(ValueError):
            a.arm_cfg(73, "UNREGISTERED")

    def test_bounded_signal_never_grants_utility(self):
        result = a.verdict(fake())
        self.assertEqual(result["status"], "BOUNDED_EVAL_SIGNAL_NOT_UTILITY_GATE")
        self.assertEqual(result["seed_wins"], 3)
        self.assertFalse(result["utility_gate_pass"])
        self.assertAlmostEqual(result["mean_deltas"]["paraphrase_eval_minus_train"], -.2)

    def test_no_attributable_gain_and_hurt(self):
        none = a.verdict(fake(eval_=0.99))
        self.assertEqual(none["status"], "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        hurt = a.verdict(fake(eval_=1.2))
        self.assertEqual(hurt["status"], "DIAGNOSTIC_HURT")
        self.assertFalse(hurt["utility_gate_pass"])

    def test_near_miss_leakage_and_retention_guard(self):
        leak = a.verdict(fake(near_eval=1.8))
        self.assertEqual(leak["status"], "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        regression = a.verdict(fake(retention_eval=1.2))
        self.assertEqual(regression["status"], "DIAGNOSTIC_HURT")

    def test_missing_seed_arm_or_invalid_numeric_never_completes(self):
        x = fake()
        del x["73"]["SHUFFLED"]
        with self.assertRaisesRegex(ValueError, "Incomplete arm"):
            a.verdict(x)
        x = fake()
        del x["79"]
        with self.assertRaisesRegex(ValueError, "Incomplete seed"):
            a.verdict(x)
        x = fake()
        x["73"]["EMA_EVAL"]["summary"]["paraphrase"] = math.nan
        with self.assertRaisesRegex(ValueError, "Invalid arm"):
            a.verdict(x)

    def test_export_free_and_explicit_native_optin(self):
        obj = a.ExportFreeTrainer.__new__(a.ExportFreeTrainer)
        self.assertEqual(obj._export(None, None, None, None),
                         {"gguf": "NO_EXPORT", "gguf_sha256": None})
        p = subprocess.run([sys.executable, str(Path(a.__file__)),
                            "--master", "/nonexistent/master",
                            "--out", "/nonexistent/output"],
                           capture_output=True, text=True, timeout=15)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--execute-native", p.stderr)
        self.assertNotIn("Traceback", p.stderr)


if __name__ == "__main__":
    unittest.main()
