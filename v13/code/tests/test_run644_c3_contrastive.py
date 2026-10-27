"""Run644 frozen disjoint negative training contract, no native model dependency."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts import run644_c3_contrastive as S
from scripts import run642_c3_protocol_locality as B
from scripts import run632_c3_lfm350_native as R

COHORT = Path(__file__).resolve().parents[1] / (
    "docs/proofs/continuation-20261027/run644-c3-contrastive/COHORT.json")


class Run644Contract(unittest.TestCase):
    def test_frozen_disjoint_four_negative_rows(self):
        c = S.verify_cohort(COHORT)
        self.assertEqual(len(c["contrastive_rows"]), 4)
        self.assertEqual(c["contrastive_rows"], list(S.CONTRASTIVE))
        self.assertEqual({r["target"] for r in c["contrastive_rows"]}, {"not specified"})
        self.assertFalse(any("Cedar" in r["prompt"] for r in c["contrastive_rows"]))
        self.assertEqual(c["config"], B.CONFIG)
        self.assertEqual(c["locality_anchor_prompts"], list(B.LOCALITY_ANCHORS))
        self.assertEqual(c["baseline"]["historical_near_miss_leaks"], 2)
        self.assertEqual(c["negative_gates"], B.H.GATES)
        self.assertEqual(c["production_weight_authority"], 0)

    def test_frozen_locality_uses_only_original_alder_rows(self):
        rows = [{"prompt": p, "target": t} for p, t in R.TRAIN] + list(S.CONTRASTIVE)
        self.assertEqual(S.locality_prompts(rows, 2), list(B.LOCALITY_ANCHORS))
        with self.assertRaisesRegex(ValueError, "six training rows"):
            S.locality_prompts(rows[:-1], 2)
        wrong = [dict(r) for r in rows]
        wrong[-1]["target"] = "83"
        with self.assertRaisesRegex(ValueError, "contrastive rows"):
            S.locality_prompts(wrong, 2)
        wrong = [dict(r) for r in rows]
        wrong[0]["target"] = "wrong"
        with self.assertRaises(ValueError):
            S.locality_prompts(wrong, 2)

    def test_any_cohort_mutation_rejected_before_native(self):
        original = json.loads(COHORT.read_text())
        changes = [
            lambda c: c["contrastive_rows"][0].update(target="violet"),
            lambda c: c["contrastive_rows"][0].update(prompt="In the fictional Cedar protocol, what is the marker color?"),
            lambda c: c["config"].update(learning_steps=64),
            lambda c: c["baseline"].update(adapter_sha256="0"*64),
            lambda c: c["near_miss_rows"][0].update(target="violet"),
            lambda c: c.update(production_weight_authority=1),
        ]
        for change in changes:
            c = json.loads(json.dumps(original)); change(c)
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "cohort.json"
                p.write_text(json.dumps(c))
                with self.assertRaisesRegex(ValueError, "cohort bytes"):
                    S.verify_cohort(p)

    def test_legacy_negative_utility_not_promoted(self):
        c = S.verify_cohort(COHORT)
        self.assertEqual(c["historical_run639"], B.BASELINE)
        self.assertEqual(c["historical_run638"], B.H.BASELINE)
        self.assertEqual(c["baseline"]["historical_fulltext_baseline_parity"], "5/6")
        self.assertFalse(c["age_change"] or c["approval_change"])
        self.assertEqual(c["acceptance"]["near_miss_max_hits"], 0)

    def test_optimizer_incomplete_proof_rejected(self):
        with self.assertRaises(ValueError):
            S.verify_training_result({"artifact": None, "files": None})


if __name__ == "__main__":
    unittest.main()
