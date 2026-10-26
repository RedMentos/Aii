"""Run606 synthetic protocol-only tests; no model downloads or gate promotion."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run606_cross_body_latent_shadow as S


class Run606Shadow(unittest.TestCase):
    def test_frozen_cohort_and_disjoint_topics(self):
        d=S.load_cohort()
        self.assertEqual(S.git_blob_sha(S.COHORT),S.COHORT_BLOB)
        self.assertEqual(len(d['prompts']),40)
        self.assertEqual(len([r for r in d['prompts'] if r['topic'] in d['train_topics']]),30)
        self.assertEqual(len([r for r in d['prompts'] if r['topic'] in d['test_topics']]),10)
        self.assertFalse(set(d['train_topics']) & set(d['test_topics']))

    def test_normalization_rejects_nonfinite_zero_and_bad_shape(self):
        for x in (np.zeros((2,3)),np.array([[1.,np.nan],[1.,2.]]),np.array([1.,2.])):
            with self.subTest(shape=x.shape),self.assertRaises(ValueError):
                S.normalize(x)

    def test_heldout_ridge_controls_are_reproducible(self):
        rng=np.random.default_rng(17)
        z=rng.normal(size=(40,12))
        x=z@rng.normal(size=(12,2048))
        y=z@rng.normal(size=(12,1024))
        a=S.evaluate(x,y,list(range(30)),list(range(30,40)),controls=20)
        b=S.evaluate(x,y,list(range(30)),list(range(30,40)),controls=20)
        self.assertEqual(a,b)
        self.assertEqual(a['train_n'],30)
        self.assertEqual(a['test_n'],10)
        self.assertEqual(a['shuffled']['n'],20)
        self.assertGreaterEqual(a['observed']['top1'],0.)
        self.assertLessEqual(a['observed']['top1'],1.)
        self.assertEqual(a['heldout_chance_top1'],.1)
        self.assertEqual(a['alpha'],1.)

    def test_ridge_rejects_overlap_and_wrong_dimensions(self):
        x=np.ones((40,2048));y=np.ones((40,1024))
        with self.assertRaises(ValueError):
            S.evaluate(x,y,[0,1,2,3],[3,4],controls=2)
        with self.assertRaises(ValueError):
            S.evaluate(x[:,:10],y,list(range(30)),list(range(30,40)),controls=2)

    def test_capture_rejects_fake_authority_and_nonfinite_rows(self):
        class FakeRunner:
            instances=[]
            bad=False
            nonfinite=False
            def __init__(self,home,role,model,cfg,purpose):
                self.role=role;self.unloaded=False;FakeRunner.instances.append(self)
            def tap(self,text,cancel,deadline,max_tokens):
                dim=2048
                v=[float('nan')]*dim if self.nonfinite else [1.]*dim
                return {'token_ids':[1,2],'vectors':[v,v],
                        'metrics':{'role':self.role,'tap_id':'lfm2.result_norm.final.v1',
                        'embedding_dim':dim,'CAN_LATENT_TAP':not self.bad,
                        'CAN_LATENT_INJECT':False,'CAN_TRAIN_BODY':False}}
            def unload(self):self.unloaded=True
        rows=[{'id':'synthetic-1','text':'A synthetic test sentence.'}]
        with tempfile.TemporaryDirectory() as d,patch.object(S,'LlamaRunner',FakeRunner):
            x,receipts=S.capture(Path(d)/'m',Path(d)/'server','B1_DETAIL','body',rows,Path(d)/'run')
            self.assertEqual(x.shape,(1,2048))
            self.assertEqual(receipts[0]['token_count'],2)
            self.assertTrue(FakeRunner.instances[-1].unloaded)
            for attr in ('bad','nonfinite'):
                setattr(FakeRunner,attr,True)
                with self.subTest(attr=attr),self.assertRaises(ValueError):
                    S.capture(Path(d)/'m',Path(d)/'server','B1_DETAIL','body',rows,Path(d)/'run')
                self.assertTrue(FakeRunner.instances[-1].unloaded)
                setattr(FakeRunner,attr,False)

    def test_missing_native_server_preserves_error_report(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out.json'
            with self.assertRaisesRegex(ValueError,'server missing'):
                S.run(Path(d),out,Path(d)/'states.npz')
            report=json.loads(out.read_text())
            self.assertEqual(report['status'],'ERROR')
            self.assertEqual(report['gates']['jepa_weight'],0)
            self.assertFalse(report['b3_promoted'])


if __name__=='__main__':
    unittest.main()
