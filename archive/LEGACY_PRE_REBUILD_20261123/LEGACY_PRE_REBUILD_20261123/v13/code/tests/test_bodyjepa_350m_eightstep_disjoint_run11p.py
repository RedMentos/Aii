"""Run11P model-free immutable eight-step disjoint Body-JEPA cohort tests.

The real FP32 model experiment is a separate Actions step, not a unit-test claim.
"""
import subprocess
import sys
from pathlib import Path
import unittest

from scripts import bodyjepa_350m_eightstep_disjoint_run11p as a


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


class BodyJepaEightStepDisjointProtocol(unittest.TestCase):
    def test_exact_preregistered_source_and_disjoint_queries(self):
        f = a.fixture()
        self.assertEqual({k: len(v) for k, v in f.items()},
                         {"train": 4, "paraphrase": 4,
                          "near_miss_leak_proxy": 4, "retention": 4})
        self.assertEqual(len({q for rows in f.values() for q, _ in rows}), 16)
        self.assertEqual(a.fixture_sha(f),
                         "1b2f71817200389d3f78fc87cf70512e23bd7273e75c2901768c3cc76ded56aa")
        self.assertEqual(a.SEEDS, (97, 101, 103))
        self.assertEqual(a.ARMS, ("CE", "EMA", "SHUFFLED"))
        self.assertEqual(a.CONFIG["max_steps"], 8)
        self.assertEqual(a.CONFIG["min_steps"], 8)
        self.assertEqual(a.CONFIG["rank"], 2)
        self.assertEqual(a.CONFIG["jepa_ema_decay"], 0.9)
        self.assertEqual(a.FIXTURE_SHA256, a.fixture_sha(f))
        self.assertEqual(a.LICENSE_SHA256, "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c")
        self.assertFalse(any(old in str(f) for old in ("Asterion", "Keldara", "Velaris", "Meridia", "Cobalt", "Vermilion", "Juniper", "Saffron")))
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
        del x["97"]["SHUFFLED"]
        with self.assertRaisesRegex(ValueError, "Incomplete arm"):
            a.verdict(x)
        x = fake(1., .8, 1.)
        del x["101"]
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
