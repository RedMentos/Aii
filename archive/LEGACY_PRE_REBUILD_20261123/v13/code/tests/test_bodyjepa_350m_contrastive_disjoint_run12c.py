"""Run12C source-only preregistered contrastive 350M pilot contract tests.

These tests never download a model or execute Torch; native evidence requires a
separate explicit serial trigger after preflight and ownership checks.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import bodyjepa_350m_contrastive_disjoint_run12c as p


def row(nll):
    return {"summary": {"train": nll, "paraphrase": nll,
                        "near_miss_leak_proxy": 2.0, "retention": 1.0}}


def result_set(ce=1.0, cos=.95, contrast=.80, shuffled=1.0):
    return {str(seed): {"CE": row(ce), "COS_EMA": row(cos),
                        "CONTRAST_EMA": row(contrast),
                        "CONTRAST_SHUFFLED": row(shuffled)}
            for seed in p.SEEDS}


class Run12CProtocol(unittest.TestCase):
    def test_disjoint_preregistered_facts_hash_seeds_arms_and_exact_config(self):
        f = p.fixture()
        self.assertEqual({k: len(v) for k, v in f.items()},
                         {"train": 4, "paraphrase": 4, "near_miss_leak_proxy": 4, "retention": 4})
        self.assertEqual(len({q for group in f.values() for q, _ in group}), 16)
        self.assertEqual(p.fixture_sha(f),
                         "848021441551627c47107c7b1298d338ab674d8983ff10af4848cf33adf77748")
        self.assertEqual(p.SEEDS, (227, 229, 233))
        self.assertEqual(p.ARMS, ("CE", "COS_EMA", "CONTRAST_EMA", "CONTRAST_SHUFFLED"))
        self.assertEqual(p.CONFIG["rank"], 2)
        self.assertEqual(p.CONFIG["max_steps"], p.CONFIG["min_steps"] == 8 and 8)
        self.assertEqual(p.CONFIG["targets"], ["w1", "w2", "w3"])
        self.assertEqual(p.CONFIG["jepa_ema_decay"], 0.9)
        self.assertTrue(p.CONFIG["jepa_target_eval"])
        self.assertEqual(p.CONFIG["contrastive_temperature"], 0.1)
        self.assertFalse(p.CONFIG["checkpoint_resume"])
        self.assertEqual(p.CONFIG["anchor_weight"], 0.)
        self.assertEqual(p.LICENSE_SHA256,
                         "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c")
        self.assertFalse(any(s in str(f) for s in ("Orriven", "Talmera", "Selenor", "Dravik")))

    def test_signal_only_when_both_controls_and_retention_guard_hold(self):
        got = p.verdict(result_set())
        self.assertEqual(got["status"], "BOUNDED_CONTRASTIVE_NLL_SIGNAL_NOT_UTILITY_GATE")
        self.assertEqual(got["seed_wins"], 3)
        self.assertFalse(got["utility_gate_pass"])
        self.assertEqual(p.verdict(result_set(contrast=.99))["status"],
                         "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        self.assertEqual(p.verdict(result_set(contrast=1.1))["status"], "DIAGNOSTIC_HURT")
        x = result_set()
        x["227"]["CONTRAST_EMA"]["summary"]["retention"] = 1.30
        self.assertNotEqual(p.verdict(x)["status"],
                            "BOUNDED_CONTRASTIVE_NLL_SIGNAL_NOT_UTILITY_GATE")

    def test_missing_seed_arm_or_metric_fail_closed(self):
        x = result_set()
        del x["227"]["CONTRAST_SHUFFLED"]
        with self.assertRaisesRegex(ValueError, "Incomplete arm"):
            p.verdict(x)
        x = result_set()
        del x["229"]
        with self.assertRaisesRegex(ValueError, "Incomplete seed"):
            p.verdict(x)
        x = result_set()
        x["233"]["CE"]["summary"]["paraphrase"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Invalid NLL"):
            p.verdict(x)
        x = result_set()
        del x["233"]["CE"]["summary"]["train"]
        with self.assertRaisesRegex(ValueError, "Incomplete NLL"):
            p.verdict(x)

    def test_no_export_both_objectives(self):
        self.assertEqual(p.ExportFreeCosineTrainer._export(None, None, None, None, None),
                         {"gguf": "NO_EXPORT", "gguf_sha256": None})
        self.assertEqual(p.ExportFreeContrastiveTrainer._export(None, None, None, None, None),
                         {"gguf": "NO_EXPORT", "gguf_sha256": None})

    def test_native_execution_is_explicit_opt_in(self):
        completed = subprocess.run(
            [sys.executable, str(Path(p.__file__)),
             "--master", "/does/not/exist", "--out", "/does/not/exist"],
            capture_output=True, text=True, timeout=15)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--execute-native", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_model_free_twelve_arm_scaffold_keeps_all_gates_negative(self):
        calls = []
        class Fake:
            kind = "?"
            def __init__(self, master, work, **kwargs):
                self.cfg = kwargs["cfg"]
                calls.append((self.kind, self.cfg.copy()))
            def fit(self, items, base_generation):
                self.items = items
                return {"artifact": "NO_EXPORT", "hash": None,
                        "files": {"gguf": "NO_EXPORT"},
                        "metrics": {"steps": 8, "jepa_weight": self.cfg["jepa_weight"]}}
        class Cos(Fake):
            kind = "cosine"
        class Contrast(Fake):
            kind = "contrastive"
        synthetic = {name: [{"nll": 1.0}] for name in p.fixture()}
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            with patch.object(p, "ExportFreeCosineTrainer", Cos), \
                 patch.object(p, "ExportFreeContrastiveTrainer", Contrast), \
                 patch.object(p, "measure", return_value=synthetic):
                report = p.run(Path(temp) / "unused-master", out)
            self.assertEqual(report["completed_arms"], 12)
            self.assertFalse(report["utility_gate_pass"])
            self.assertFalse(report["production_activation"])
            self.assertFalse(report["step2_utility_pass"])
            self.assertFalse(report["body_jepa_available"])
            self.assertFalse(report["whole_system_complete"])
            self.assertEqual(report["runtime_jepa_weight"], 0)
            self.assertEqual(len(calls), 12)
            self.assertEqual(sum(k == "cosine" for k, _ in calls), 6)
            self.assertEqual(sum(k == "contrastive" for k, _ in calls), 6)
            self.assertEqual(sum(c["jepa_weight"] == 0 for _, c in calls), 3)
            self.assertEqual(sum(c["jepa_target"] == "shuffled" for _, c in calls), 3)
            self.assertEqual(json.loads((out / "report.json").read_text())["completed_arms"], 12)

    def test_first_native_failure_persists_partial_raw_receipt(self):
        class Fail:
            def __init__(self, *args, **kwargs):
                pass
            def fit(self, *args, **kwargs):
                raise RuntimeError("SYNTHETIC_FAILURE_ONLY")
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            with patch.object(p, "ExportFreeCosineTrainer", Fail):
                with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_FAILURE"):
                    p.run(Path(temp) / "unused-master", out)
            report = json.loads((out / "report.json").read_text())
            self.assertEqual(report["status"], "FAILED_PRESERVED")
            self.assertEqual(report["failures"][0]["seed"], 227)
            self.assertEqual(report["failures"][0]["arm"], "CE")
            self.assertEqual(report["failures"][0]["error_type"], "RuntimeError")
            self.assertEqual(report["results"], {})


if __name__ == "__main__":
    unittest.main()
