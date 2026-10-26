"""Run608 synthetic protocol-only tests; frozen real model cohort never trained here."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import run608_cross_body_paraphrase_native as S


def synthetic():
    rng=np.random.default_rng(608)
    latent=rng.normal(size=(40,6))
    ax=rng.normal(size=(6,2048));ay=rng.normal(size=(6,1024))
    rows=[];x=[];y=[]
    topics=list(S.TRAIN_TOPICS+S.TEST_TOPICS)
    for k in range(40):
        topic=topics[k//5]
        for variant in ("A","B"):
            rows.append({"id":f"{topic}-{k%5+1}-{variant}","fact_id":f"{topic}-{k%5+1}",
                         "topic":topic,"variant":variant,"text":"alpha" if variant=="A" else "beta"})
            x.append(latent[k]@ax+rng.normal(0,.001,2048))
            y.append(latent[k]@ay+rng.normal(0,.001,1024))
    return np.array(x),np.array(y),list(range(60)),list(range(60,80)),rows


class Run608NativeParaphrase(unittest.TestCase):
    def test_frozen_new_cohort_and_disjoint_facts(self):
        d=S.load_cohort()
        self.assertEqual(S.R606.git_blob_sha(S.COHORT),S.COHORT_BLOB)
        self.assertEqual(len(d["prompts"]),80)
        self.assertEqual(len({r["fact_id"] for r in d["prompts"]}),40)
        self.assertEqual(len([r for r in d["prompts"] if r["topic"] in S.TRAIN_TOPICS]),60)
        self.assertEqual(len([r for r in d["prompts"] if r["topic"] in S.TEST_TOPICS]),20)
        self.assertFalse(set(d["train_topics"])&set(d["test_topics"]))

    def test_shared_synthetic_semantic_proxy_and_shuffled_controls(self):
        args=synthetic()
        a=S.evaluate(*args,controls=30)
        b=S.evaluate(*args,controls=30)
        self.assertEqual(a,b)
        self.assertGreater(a["observed"]["opposite_paraphrase_top1"],.5)
        self.assertEqual(a["chance_opposite"],1/19)
        self.assertEqual(a["chance_exact"],1/20)
        self.assertEqual(a["shuffled"]["n"],30)
        self.assertEqual(a["train_n"],60)
        self.assertEqual(a["heldout_n"],20)
        self.assertGreater(a["observed"]["opposite_paraphrase_top1"],a["lexical_jaccard_opposite_top1"])

    def test_wrong_source_dimensions_split_and_nonfinite_refused(self):
        x,y,tr,te,rows=synthetic()
        for xx,yy,ttrain,ttest in (
            (x[:,:20],y,tr,te),(x,y[:,:20],tr,te),
            (x,y,tr[:-1],te),(x,y,tr,list(range(59,79))),
            (np.full_like(x,np.nan),y,tr,te)):
            with self.subTest(dim=(xx.shape,yy.shape)),self.assertRaises(ValueError):
                S.evaluate(xx,yy,ttrain,ttest,rows,controls=2)

    def test_missing_opposite_is_refused(self):
        x,y,tr,te,rows=synthetic()
        rows[61]["fact_id"]="unmatched"
        with self.assertRaisesRegex(ValueError,"opposite"):
            S.evaluate(x,y,tr,te,rows,controls=2)

    def test_jaccard_excludes_self_exact_candidate(self):
        rows=[{"text":"red violin melody"},{"text":"quiet string tune"},
              {"text":"wind storm clouds"},{"text":"wet weather sky"}]
        # Query 0 cannot select itself even with identical lexical tokens.
        score=S.lexical_top1(rows,[0,1,2,3],np.array([1,0,3,2]))
        self.assertTrue(0<=score<=1)

    def test_missing_server_preserves_error_and_negative_gates(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"report.json"
            with self.assertRaisesRegex(ValueError,"server missing"):
                S.run(Path(d),out,Path(d)/"states.npz")
            r=json.loads(out.read_text())
            self.assertEqual(r["status"],"ERROR")
            self.assertEqual(r["gates"]["STEP2"],"UTILITY_FAIL")
            self.assertEqual(r["gates"]["B3_L1"],"FAIL")
            self.assertEqual(r["gates"]["jepa_weight"],0)
            self.assertFalse(r["can_latent_inject"])
            self.assertFalse(r["canonical_architecture_complete"])


if __name__=="__main__":
    unittest.main()
