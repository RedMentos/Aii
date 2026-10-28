"""Software-only proof of source disjointness and deterministic shadow optimizer."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
from scripts import c2_bilingual_routehead_shadow as S


class RouteHeadShadowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'specs').mkdir()
        for name in ('c2-bilingual-routehead-train64-20261028.json','c2-bilingual-transfer64-20261028.json'):
            (self.root/'specs'/name).write_bytes((S.ROOT/'specs'/name).read_bytes())
        self.old=[{'id':f'old-{i}','text':f'Original unique sentence {i}','label':S.ROUTES[i%4]} for i in range(96)]
        self.old_sha=S.digest(json.dumps(self.old,ensure_ascii=False,sort_keys=True).encode())
        raw=json.dumps({'schema':'c2-benchmark-v1','items_sha256':self.old_sha,'items':self.old}).encode()
        (self.root/'specs/c2-benchmark.json').write_bytes(raw)
        self.old_blob=S.git_blob(raw)

    def load(self):
        with patch.object(S,'ORIGINAL_SHA',self.old_sha),patch.object(S,'ORIGINAL_BLOB',self.old_blob):
            return S.cohorts(self.root)

    def test_registered_48_fit_16_val_and_disjoint_transfer(self):
        train,transfer=self.load()
        self.assertEqual(len(train),64);self.assertEqual(len(transfer),64)
        self.assertEqual(sum(x['split']=='fit' for x in train),48)
        self.assertEqual(sum(x['split']=='validation' for x in train),16)
        self.assertFalse({x['text'].casefold() for x in train}&{x['text'].casefold() for x in transfer})

    def test_frozen_train_blob_cannot_be_rehashed_to_hide_edit(self):
        p=self.root/'specs/c2-bilingual-routehead-train64-20261028.json'
        d=json.loads(p.read_text());d['items'][0]['text']='changed'
        d['items_sha256']=S.digest(json.dumps(d['items'],ensure_ascii=False,sort_keys=True).encode())
        p.write_text(json.dumps(d,ensure_ascii=False))
        with self.assertRaisesRegex(ValueError,'Git blob drift'):
            self.load()

    def test_training_overlap_rejected(self):
        train,_=self.load()
        self.old[0]['text']=train[0]['text']
        self.old_sha=S.digest(json.dumps(self.old,ensure_ascii=False,sort_keys=True).encode())
        raw=json.dumps({'schema':'c2-benchmark-v1','items_sha256':self.old_sha,'items':self.old}).encode()
        (self.root/'specs/c2-benchmark.json').write_bytes(raw)
        self.old_blob=S.git_blob(raw)
        with self.assertRaisesRegex(ValueError,'overlap'):
            self.load()

    def test_normalize_rejects_nan_and_zero_is_finite(self):
        a=S.normalize(np.array([[0.,0.,0.],[3.,4.,0.]]))
        self.assertTrue(np.isfinite(a).all())
        self.assertEqual(float(np.linalg.norm(a[1])),1.)
        with self.assertRaisesRegex(ValueError,'Finite'):
            S.normalize([[float('nan'),1.],[1.,2.]])

    def test_fixed_optimizer_deterministic_finite_decreasing_loss(self):
        rng=np.random.default_rng(13)
        x=S.normalize(rng.normal(size=(48,12)))
        y=np.tile(np.arange(4,dtype=np.int64),12)
        w,b,stats=S.fit(x,y)
        w2,b2,stats2=S.fit(x,y)
        self.assertTrue(np.array_equal(w,w2) and np.array_equal(b,b2))
        self.assertEqual(stats,stats2)
        self.assertLess(stats['loss_end'],stats['loss_start'])
        self.assertLessEqual(stats['max_applied_gradient_norm'],1.+1e-12)
        self.assertEqual(stats['trainable_parameter_count'],12*4+4)
        self.assertTrue(np.isfinite(w).all())

    def test_gradient_matches_finite_difference(self):
        rng=np.random.default_rng(3)
        x=S.normalize(rng.normal(size=(8,5)))
        y=np.array([0,1,2,3,0,1,2,3],dtype=np.int64)
        w=np.zeros((5,4));b=np.zeros(4)
        _,gw,gb=S.loss_grad(x,y,w,b)
        eps=1e-6
        w[0,2]+=eps;plus=S.loss_grad(x,y,w,b)[0]
        w[0,2]-=2*eps;minus=S.loss_grad(x,y,w,b)[0]
        self.assertAlmostEqual(gw[0,2],(plus-minus)/(2*eps),places=7)
        b[2]+=eps;plus=S.loss_grad(x,y,np.zeros((5,4)),b)[0]
        b[2]-=2*eps;minus=S.loss_grad(x,y,np.zeros((5,4)),b)[0]
        self.assertAlmostEqual(gb[2],(plus-minus)/(2*eps),places=7)

    def test_fit_rejects_validation_rows_and_wrong_shape(self):
        x=np.zeros((64,4));y=np.zeros(64,dtype=np.int64)
        with self.assertRaisesRegex(ValueError,'registered 48'):
            S.fit(x,y)
        with self.assertRaisesRegex(ValueError,'registered 48'):
            S.fit(x[:48],y[:47])

    def test_report_stratification_does_not_fit_test(self):
        _,rows=self.load()
        x=S.normalize(np.ones((64,6)))
        w=np.zeros((6,4));b=np.zeros(4)
        fake=types.ModuleType('scripts.c2_benchmark')
        fake.summarize=lambda rr,extra=None:{'n':len(rr),'accuracy':sum(r['pred']==r['label'] for r in rr)/len(rr)}
        with patch.dict(sys.modules,{'scripts.c2_benchmark':fake}):
            d=S.evaluate(rows,x,w,b,range(64))
        self.assertEqual(d['overall']['n'],64)
        self.assertEqual(d['per_language']['en']['n'],32)
        self.assertEqual(d['per_language']['de']['n'],32)

    def test_closed_report_refuses_overwrite(self):
        p=self.root/'report.json'
        S.save_json_new(p,{'jef_route_activation':False})
        with self.assertRaises(FileExistsError):
            S.save_json_new(p,{'jef_route_activation':True})
        self.assertFalse(json.loads(p.read_text())['jef_route_activation'])


if __name__=='__main__':unittest.main()