"""Run607 source-only adversarial and synthetic tests; no native inference."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import run607_cross_body_geometry as G


def fixture(shared=True):
    rng=np.random.default_rng(19)
    z=rng.normal(size=(40,9))
    x=z@rng.normal(size=(9,2048))
    y=(z if shared else rng.normal(size=(40,9)))@rng.normal(size=(9,1024))
    rows=[{"id":f"item-{i}","topic":("music" if i<35 else "weather") if i>=30 else "train",
           "text":f"Synthetic sentence {i}."} for i in range(40)]
    receipts={role:[{"token_count":8+i%4} for i in range(40)]
              for role in ("B1_DETAIL","B2_GIST")}
    return x,y,list(range(30)),list(range(30,40)),rows,{"receipts":receipts}


class Run607Geometry(unittest.TestCase):
    def test_original_frozen_input_is_immutable(self):
        self.assertEqual(G.blob_sha(G.COHORT),G.COHORT_BLOB)
        self.assertEqual(G.PERMUTATIONS,1000)
        self.assertEqual(G.GATES["B3_L1"],"FAIL")
        self.assertEqual(G.GATES["jepa_weight"],0)

    def test_shared_geometry_synthetic_controls(self):
        args=fixture(True)
        a=G.analyze(*args,permutations=100)
        b=G.analyze(*args,permutations=100)
        self.assertEqual(a,b)
        self.assertEqual(a["heldout_n"],10)
        self.assertEqual(a["within_topic_pairs"],20)
        self.assertEqual(a["cross_topic_pairs"],25)
        self.assertGreater(a["metrics"]["pearson_rsa"]["observed"],0.9)
        self.assertGreater(a["metrics"]["token_topic_partial_rsa"]["observed"],0.8)
        self.assertLessEqual(a["metrics"]["pearson_rsa"]["exploratory_permutation_p"],.05)

    def test_unpaired_synthetic_not_assumed_aligned(self):
        result=G.analyze(*fixture(False),permutations=20)
        self.assertLess(result["metrics"]["pearson_rsa"]["observed"],.9)
        self.assertEqual(result["permutations"],20)
        self.assertGreaterEqual(result["nearest_neighbor_agreement"],0.)

    def test_nonfinite_zero_and_degenerate_correlations_fail_closed(self):
        for x in (np.zeros((3,4)),np.array([[1.,2.],[float("nan"),1.]])):
            with self.assertRaises(ValueError):
                G.normalize(x)
        with self.assertRaises(ValueError):
            G.pearson([1,1,1],[1,2,3])
        with self.assertRaises(ValueError):
            G.analyze(*fixture(),permutations=0)

    def test_missing_and_tampered_raw_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            with self.assertRaises(FileNotFoundError):
                G.verify_closed_raw(folder)
            (folder/"RUN606_SHA256SUMS.txt").write_text("0"*64+"  ../escape\\n")
            with self.assertRaisesRegex(ValueError,"unsafe"):
                G.verify_closed_raw(folder)

    def test_error_report_retains_negative_gates(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"report.json"
            with self.assertRaises(FileNotFoundError):
                G.run(Path(d),out)
            r=json.loads(out.read_text())
            self.assertEqual(r["status"],"ERROR")
            self.assertEqual(r["gates"]["STEP2"],"UTILITY_FAIL")
            self.assertEqual(r["gates"]["Body_JEPA"],"UNAVAILABLE")
            self.assertFalse(r["prospective"])
            self.assertFalse(r["can_latent_inject"])
            self.assertFalse(r["canonical_architecture_complete"])


if __name__=="__main__":
    unittest.main()
