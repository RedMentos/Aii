"""Run117BI software-only frozen synthetic grouped-source 350M pilot controls."""
import math
import json
from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path

from scripts import bodyjepa_350m_grouped_run117bi as p
from v13.body_jepa_grouped_source_candidate import validate_training_rows


class Grouped350mPreflight(unittest.TestCase):
    def test_preregistered_fixture_exact_hash_and_disjoint_question_strings(self):
        rows = p.fixture()
        self.assertEqual(p.fixture_sha(rows), p.FIXTURE_SHA256)
        self.assertEqual(len(rows["train"]), 8)
        self.assertEqual(len(rows["paraphrase"]), 4)
        self.assertEqual(len(rows["near_miss_wrong_answer"]), 4)
        self.assertEqual(len(rows["source_disjoint_heldout"]), 2)
        self.assertEqual(len(rows["retention"]), 4)
        q = [q for values in rows.values() for q, _ in values]
        self.assertEqual(len(q), len(set(q)))
        self.assertEqual(p.SEEDS, (263, 269))
        self.assertEqual(p.ARMS, ("CE", "UNGROUPED_EMA", "GROUPED_EMA"))

    def test_exact_source_groups_and_heldout_are_disjoint(self):
        items, heldout, binding = p.items_and_heldout(p.fixture())
        self.assertEqual(len(items), 8)
        self.assertEqual(len(heldout), 2)
        self.assertEqual(binding["source_group_count"], 4)
        self.assertEqual(binding["repeated_view_count"], 4)
        self.assertEqual(len(set(binding["groups"])), 4)
        self.assertEqual(binding["groups"][::2], binding["groups"][1::2])
        self.assertEqual(binding["source_authentication"], "REQUIRED_EXTERNAL")
        self.assertFalse(binding["body_jepa_available"])
        self.assertEqual(binding["runtime_jepa_weight"], 0)
        self.assertTrue(all(row["source_id"].startswith("synthetic_fact_") for row in items))
        self.assertFalse({x["source_sha256"] for x in items} &
                         {x["source_sha256"] for x in heldout})

    def test_source_spoof_and_heldout_leak_refused(self):
        items, heldout, _ = p.items_and_heldout(p.fixture())
        forged = [dict(x) for x in items]
        forged[0]["target_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_TARGET_MISMATCH_RED"):
            validate_training_rows(forged, heldout_rows=heldout)
        with self.assertRaisesRegex(ValueError, "HELDOUT_SOURCE_LEAK_RED"):
            validate_training_rows(items, heldout_rows=[
                dict(items[0], view_id="heldout_new")])

    def fake(self, *, grouped_paraphrase=.93):
        def arm(para, ret=1.0, near=1.0, held=1.0):
            return {"summary": {"train": .8, "paraphrase": para,
                    "retention": ret, "near_miss_wrong_answer": near,
                    "source_disjoint_heldout": held}}
        return {str(seed): {
            "CE": arm(1.0),
            "UNGROUPED_EMA": arm(.98),
            "GROUPED_EMA": arm(grouped_paraphrase, 1.01, 1.0, 1.01),
        } for seed in p.SEEDS}

    def test_verdict_signal_is_only_diagnostic(self):
        result = p.verdict(self.fake())
        self.assertEqual(result["status"], "GROUPED_MASK_EXPLORATORY_NLL_SIGNAL_NO_GATE")
        self.assertEqual(result["seed_wins"], 2)
        self.assertFalse(result["utility_gate_pass"])
        self.assertEqual(len(result["per_seed_deltas"]), 2)

    def test_verdict_no_gain_and_adversarial_missing_nan(self):
        self.assertEqual(p.verdict(self.fake(grouped_paraphrase=.99))["status"],
                         "GROUPED_MASK_NO_ATTRIBUTABLE_SIGNAL")
        bad = self.fake()
        del bad[str(p.SEEDS[0])]["CE"]
        with self.assertRaisesRegex(ValueError, "RUN117BI_ARM_INCOMPLETE_RED"):
            p.verdict(bad)
        bad = self.fake()
        bad[str(p.SEEDS[1])]["GROUPED_EMA"]["summary"]["retention"] = math.nan
        with self.assertRaisesRegex(ValueError, "RUN117BI_NLL_SUMMARY_RED"):
            p.verdict(bad)

    def test_model_free_six_arm_scaffold_and_no_export(self):
        calls = []
        class Fake:
            kind = "?"
            def __init__(self, master, work, **kwargs):
                self.cfg = kwargs["cfg"]
                calls.append((self.kind, dict(self.cfg)))
            def fit(self, items, base_generation):
                self.items = items
                binding = {"source_group_count": 4, "repeated_view_count": 4,
                           "source_authentication": "REQUIRED_EXTERNAL"}
                return {"artifact": "NO_EXPORT", "hash": None,
                        "files": {"gguf": "NO_EXPORT"},
                        "metrics": {"steps": 8, "grouped_source_binding": binding}}
        class CE(Fake):
            kind = "ce"
        class Ungrouped(Fake):
            kind = "ungrouped"
        class Grouped(Fake):
            kind = "grouped"
        synthetic = {name: [{"nll": 1.0}] for name in p.fixture()}
        with tempfile.TemporaryDirectory() as td:
            with patch.object(p, "ExportFreeCosineTrainer", CE), \
                 patch.object(p, "ExportFreeContrastiveTrainer", Ungrouped), \
                 patch.object(p, "ExportFreeGroupedTrainer", Grouped), \
                 patch.object(p, "measure", return_value=synthetic):
                report = p.run(Path(td) / "unused-master", Path(td))
            self.assertEqual(report["completed_arms"], 6)
            self.assertFalse(report["utility_gate_pass"])
            self.assertFalse(report["production_activation"])
            self.assertFalse(report["body_jepa_available"])
            self.assertEqual(report["runtime_jepa_weight"], 0)
            self.assertEqual(report["source_group_count"], 4)
            self.assertEqual([x[0] for x in calls].count("grouped"), 2)
            self.assertEqual(sum(x[1].get("grouped_source_enabled") is True
                                 for x in calls), 2)
            self.assertEqual(sum(x[1]["jepa_weight"] == 0 for x in calls), 2)
            self.assertEqual(json.loads((Path(td) / "report.json").read_text())["completed_arms"], 6)

    def test_first_fit_failure_persists_raw_red(self):
        class Fail:
            def __init__(self, *args, **kwargs):
                pass
            def fit(self, *args, **kwargs):
                raise RuntimeError("SYNTHETIC_FAILURE_ONLY")
        with tempfile.TemporaryDirectory() as td:
            with patch.object(p, "ExportFreeCosineTrainer", Fail):
                with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_FAILURE"):
                    p.run(Path(td) / "unused-master", Path(td))
            report = json.loads((Path(td) / "report.json").read_text())
            self.assertEqual(report["status"], "FAILED_PRESERVED")
            self.assertEqual(report["failures"][0]["error_type"], "RuntimeError")
            self.assertFalse(report["body_jepa_available"])

    def test_no_native_without_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(SystemExit):
                p.main(["--master", td, "--out", str(Path(td) / "out")])
            self.assertFalse((Path(td) / "out").exists())

    def test_no_export_and_no_runtime_gate(self):
        import inspect
        self.assertIn("NO_EXPORT", inspect.getsource(p.ExportFreeCosineTrainer._export))
        self.assertIn("NO_EXPORT", inspect.getsource(p.ExportFreeContrastiveTrainer._export))
        self.assertIn("NO_EXPORT", inspect.getsource(p.ExportFreeGroupedTrainer._export))
        source = inspect.getsource(p.run)
        self.assertIn('"runtime_jepa_weight": 0', source)
        self.assertIn('"body_jepa_available": False', source)
        self.assertIn('"production_activation": False', source)
        self.assertIn('"SYNTHETIC_FACT_METADATA_ONLY"', source)
        self.assertIn("grouped_source_enabled=True", source)


if __name__ == "__main__":
    unittest.main()
