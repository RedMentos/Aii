"""Run614 frozen new cohort, native contract and software-only adversarial tests."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import run614_independent_native_paraphrase as R


class IndependentNativeCohort(unittest.TestCase):
    def test_new_cohort_is_frozen_source_disjoint_and_paired(self):
        d = R.load_cohort()
        rows = d["prompts"]
        self.assertEqual(len(rows), 80)
        self.assertEqual(len({r["id"] for r in rows}), 80)
        self.assertEqual(len({r["text"] for r in rows}), 80)
        self.assertEqual(set(R.TRAIN_TOPICS) & set(R.TEST_TOPICS), set())
        self.assertEqual(sum(r["topic"] in R.TRAIN_TOPICS for r in rows), 60)
        self.assertEqual(sum(r["topic"] in R.TEST_TOPICS for r in rows), 20)
        self.assertEqual(R.COHORT_BLOB, "7068267d41a1719abea3a54c84b1d0223444df1d")

    def test_changed_cohort_fails_before_native_capture(self):
        d = R.load_cohort()
        d["prompts"][0]["text"] += " TAMPERED"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "wrong.json"
            p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError, "blob changed"):
                R.load_cohort(p)

    def test_wrong_state_shapes_and_nonfinite_fail_closed(self):
        rows = R.load_cohort()["prompts"]
        x = np.ones((80, 2048))
        y = np.ones((80, 1024))
        with self.assertRaisesRegex(ValueError, "states invalid"):
            R.evaluate(x[:, :2047], y, rows)
        y[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "states invalid"):
            R.evaluate(x, y, rows)
        y[0, 0] = 1.
        with self.assertRaisesRegex(ValueError, "states invalid"):
            R.evaluate(x, y, rows, controls=199)

    def test_new_cohort_software_metric_shape_and_no_authority(self):
        rows = R.load_cohort()["prompts"]
        rng = np.random.default_rng(17)
        x = rng.standard_normal((80, 2048))
        y = rng.standard_normal((80, 1024))
        m = R.evaluate(x, y, rows)
        self.assertEqual(m["train_n"], 60)
        self.assertEqual(m["heldout_n"], 20)
        self.assertEqual(m["shuffles"], 200)
        self.assertEqual(set(m["metrics"]), {
            "lexical", "mapped_native", "b1_only", "b2_only", "fixed_fusion"})
        for scores in m["metrics"].values():
            self.assertGreaterEqual(scores["top1"], 0)
            self.assertLessEqual(scores["top1"], 1)
            self.assertGreater(scores["mrr"], 0)
            self.assertLessEqual(scores["mrr"], 1)
        self.assertGreater(m["empirical_p_b2_only"], 0)
        self.assertLessEqual(m["empirical_p_b2_only"], 1)
        self.assertEqual(R.GATES["STEP2"], "UTILITY_FAIL")
        self.assertEqual(R.GATES["B3_L1"], "FAIL")
        self.assertEqual(R.GATES["Body_JEPA"], "UNAVAILABLE")
        self.assertEqual(R.GATES["jepa_weight"], 0)

    def test_frozen_source_ids_cannot_match_self(self):
        rows = R.load_cohort()["prompts"]
        test = np.array([i for i, r in enumerate(rows) if r["topic"] in R.TEST_TOPICS])
        from scripts import run613_cross_body_fusion_offline as F
        opp = F.opposite_indices(rows, test)
        self.assertEqual(len(opp), 20)
        self.assertTrue(all(opp[opp[i]] == i and opp[i] != i for i in range(20)))


if __name__ == "__main__":
    unittest.main()
