"""Run642 source-only contract: exact new locality intervention, no Cedar/eval leakage."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import run642_c3_protocol_locality as S
from scripts import run639_c3_kl_anchor as B
from scripts import run632_c3_lfm350_native as R

COHORT = Path(__file__).resolve().parents[1] / (
    "docs/proofs/continuation-20261027/run642-c3-protocol-locality/COHORT.json")


class Run642Contract(unittest.TestCase):
    def test_frozen_cohort_and_exact_four_disjoint_anchors(self):
        c = S.verify_cohort(COHORT)
        self.assertEqual(c["config"]["locality_swaps"], 2)
        self.assertEqual(len(S.LOCALITY_ANCHORS), 4)
        self.assertEqual(S.locality_prompts(
            [{"prompt": p, "target": t} for p, t in R.TRAIN], 2),
            list(S.LOCALITY_ANCHORS))
        self.assertTrue(all("Pine" in x or "Maple" in x
                            for x in S.LOCALITY_ANCHORS))
        self.assertFalse(any("Cedar" in x for x in S.LOCALITY_ANCHORS))
        self.assertEqual(B.verify_cohort(S.ORIGINAL_COHORT)["config"]["locality_swaps"], 0)

    def mutate(self, change):
        c = json.loads(COHORT.read_text())
        change(c)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "mutated.json"
            p.write_text(json.dumps(c))
            with self.assertRaisesRegex(ValueError, "cohort bytes"):
                S.verify_cohort(p)

    def test_mutated_cohort_cannot_change_config(self):
        self.mutate(lambda c: c["config"].update(locality_swaps=3))

    def test_mutated_cohort_cannot_train_on_cedar(self):
        self.mutate(lambda c: c["locality_anchor_prompts"].append(
            "In the fictional Cedar protocol, what is the marker color?"))

    def test_mutated_cohort_cannot_replace_baseline(self):
        self.mutate(lambda c: c["baseline"].update(adapter_sha256="0"*64))

    def test_source_baseline_is_pinned_run639_not_relabelled(self):
        c = S.verify_cohort(COHORT)
        self.assertEqual(c["baseline"]["historical_near_miss_leaks"], 2)
        self.assertEqual(c["baseline"]["historical_fulltext_baseline_parity"], "5/6")
        self.assertEqual(c["historical_run638"], B.BASELINE)
        self.assertEqual(c["negative_gates"], B.GATES)
        self.assertEqual(c["production_weight_authority"], 0)
        self.assertFalse(c["age_change"] or c["approval_change"])

    def test_locality_requires_exact_original_rows_and_k(self):
        rows = [{"prompt": p, "target": t} for p, t in R.TRAIN]
        with self.assertRaisesRegex(ValueError, "frozen locality"):
            S.locality_prompts(rows, 1)
        with self.assertRaisesRegex(ValueError, "frozen locality"):
            S.locality_prompts([dict(rows[0], target="wrong"), rows[1]], 2)
        with self.assertRaisesRegex(ValueError, "frozen locality"):
            S.locality_prompts([dict(rows[0], prompt=rows[0]["prompt"].replace("Alder", "Cedar")), rows[1]], 2)

    def test_reject_incomplete_optimizer_proof(self):
        with self.assertRaises(ValueError):
            S.verify_training_result({"artifact": None, "files": None})
        fake = {"artifact": "candidate", "files": {"gguf": "x"},
                "metrics": {"steps": 31, "jepa_weight": 0,
                            "anchor_weight": 1., "rank": 2,
                            "alpha": 4, "targets": ["v_proj", "out_proj"],
                            "trainable_parameter_count": 83968,
                            "loss_history": [{"step": 31}]}}
        with self.assertRaisesRegex(ValueError, "config mismatch"):
            S.verify_training_result(fake)


if __name__ == "__main__":
    unittest.main()
