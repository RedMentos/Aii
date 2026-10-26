"""Run613 model-free adversarial tests for fixed posthoc native fusion audit."""
import numpy as np
import tempfile
from pathlib import Path
import unittest

from scripts import run608_cross_body_paraphrase_native as R608
from scripts import run613_cross_body_fusion_offline as F


class FrozenFusion(unittest.TestCase):
    def test_original_authority_never_promoted(self):
        self.assertEqual(F.ARTIFACT_ID, 12688049715)
        self.assertEqual(F.SHUFFLES, 200)
        self.assertEqual(F.GATES["STEP2"], "UTILITY_FAIL")
        self.assertEqual(F.GATES["B3_L1"], "FAIL")
        self.assertEqual(F.GATES["Body_JEPA"], "UNAVAILABLE")
        self.assertEqual(F.GATES["jepa_weight"], 0)

    def test_score_excludes_self_and_breaks_ties_by_first_index(self):
        a = np.array([[999., 1., 1.], [0., 999., 1.], [1., 0., 999.]])
        out = F.score(a, np.array([1, 2, 0]))
        self.assertEqual(out["top1"], 1.)
        self.assertEqual(out["mrr"], 1.)

    def test_fusion_is_fixed_half_half_and_constant_rows_are_safe(self):
        a = np.array([[0., 2., 4.], [1., 0., 1.], [2., 4., 0.]])
        b = np.array([[0., 4., 2.], [1., 0., 1.], [4., 2., 0.]])
        fused = F.fusion(a, b)
        self.assertAlmostEqual(fused[0, 1], .5)
        self.assertAlmostEqual(fused[0, 2], .5)
        self.assertEqual(fused[1, 0], 0.)
        self.assertEqual(fused[1, 2], 0.)
        self.assertTrue(np.isfinite(fused).all())
        with self.assertRaises(ValueError):
            F.fusion(a, b[:2])

    def test_wrong_outer_sha_fails_before_zip_processing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fake.zip"
            p.write_bytes(b"not original Run608")
            with self.assertRaisesRegex(ValueError, "outer SHA"):
                F.read_original(p)

    def test_cohort_and_train_test_source_binding(self):
        rows = R608.load_cohort()["prompts"]
        train = np.array([i for i, r in enumerate(rows) if r["topic"] in R608.TRAIN_TOPICS])
        test = np.array([i for i, r in enumerate(rows) if r["topic"] in R608.TEST_TOPICS])
        self.assertEqual(len(train), 60)
        self.assertEqual(len(test), 20)
        data = {"x_b1": np.ones((80, 2048)), "y_b2": np.ones((80, 1024)),
                "train_idx": train, "test_idx": test,
                "prompt_ids": np.array([r["id"] for r in rows])}
        self.assertEqual(F.validate_arrays(data, rows)[0].shape, (80, 2048))
        wrong = dict(data, test_idx=train[:20])
        with self.assertRaisesRegex(ValueError, "invalid"):
            F.validate_arrays(wrong, rows)
        wrong = dict(data, prompt_ids=np.array(["other"] * 80))
        with self.assertRaisesRegex(ValueError, "invalid"):
            F.validate_arrays(wrong, rows)
        y = data["y_b2"].copy()
        y[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "invalid"):
            F.validate_arrays(dict(data, y_b2=y), rows)
        with self.assertRaisesRegex(ValueError, "invalid"):
            F.validate_arrays(dict(data, x_b1=np.ones((80, 2047))), rows)

    def test_opposite_pairs_are_heldout_only(self):
        rows = R608.load_cohort()["prompts"]
        test = np.array([i for i, r in enumerate(rows) if r["topic"] in R608.TEST_TOPICS])
        opposite = F.opposite_indices(rows, test)
        self.assertEqual(len(opposite), 20)
        self.assertTrue(all(opposite[opposite[i]] == i for i in range(20)))


if __name__ == "__main__":
    unittest.main()
