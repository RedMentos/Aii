"""Run152 A3 held-out isolation and train-only support floor regressions."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'
if not SCRIPT.exists():SCRIPT=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPT))
from a3_trainonly_support_floor_run152 import train_only_floor,run,publish_exclusive


def clustered(seed=15225,n=40):
    rng=np.random.default_rng(seed);base=rng.normal(size=512);base/=np.linalg.norm(base)
    x=base[None,:]+rng.normal(scale=.018,size=(n,512))
    return x/np.linalg.norm(x,axis=1)[:,None]


class A3TrainOnly(unittest.TestCase):
    def test_01_train_only_deterministic(self):
        x=clustered();a=train_only_floor(x);b=train_only_floor(x.copy())
        self.assertEqual(a,b);self.assertFalse(a['threshold_uses_heldout'])
        self.assertGreaterEqual(a['support_floor'],.5);self.assertLessEqual(a['support_floor'],.99)

    def test_02_legacy_heldout_leak_is_real(self):
        x=clustered();near=x[:8]+np.random.default_rng(15226).normal(scale=.005,size=(8,512))
        near/=np.linalg.norm(near,axis=1)[:,None]
        far=np.random.default_rng(100).normal(size=(8,512));far/=np.linalg.norm(far,axis=1)[:,None]
        legacy=lambda h:float(max(.5,min(.99,np.min(np.max(h@x.T,axis=1))-.02)))
        self.assertNotEqual(legacy(near),legacy(far))
        self.assertEqual(train_only_floor(x),train_only_floor(x))

    def test_03_reject_zero_nan_and_duplicate_vectors(self):
        x=clustered();cases=[x[:12],np.zeros_like(x),x.copy(),x.copy()]
        cases[2][0,0]=np.nan;cases[3][0]=cases[3][1]
        for a in cases:
            with self.assertRaises(ValueError):train_only_floor(a)

    def test_04_reject_wrong_dimension(self):
        with self.assertRaisesRegex(ValueError,'train_shape'):train_only_floor(np.ones((30,16)))

    def test_05_run_never_featurizes_heldout_text(self):
        texts=[f'source {i} stable' for i in range(40)];groups=[f'group_{i}' for i in range(40)]
        calls=[]
        def feature(text):
            calls.append(text);v=np.zeros(512);i=int(text.split()[1]);v[i]=1.;v[100+i]=.4;return v/np.linalg.norm(v)
        fake=types.ModuleType('v13.student_worker')
        fake.raw_features=feature;fake.split=lambda g:(np.arange(30),np.arange(30,40))
        with patch.dict(sys.modules,{'v13':types.ModuleType('v13'),'v13.student_worker':fake}):
            raw=json.dumps({'texts':texts,'source_groups':groups}).encode();r=run(raw)
        self.assertEqual(calls,texts[:30]);self.assertEqual(r['train_sources'],30)
        self.assertEqual(r['heldout_sources'],10);self.assertEqual(r['gate'],'UNVERIFIED')
        self.assertEqual(r['input_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertNotIn('source 0',json.dumps(r))

    def test_06_publish_exclusive_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'proof.json';publish_exclusive(p,b'{"status":"FIRST"}\n')
            with self.assertRaises(FileExistsError):publish_exclusive(p,b'{"status":"SECOND"}\n')
            self.assertEqual(p.read_bytes(),b'{"status":"FIRST"}\n')

    def test_07_bad_json_and_text_limits(self):
        with self.assertRaises(Exception):run(b'not json')
        with self.assertRaises(ValueError):run(json.dumps({'texts':['x']*31,'source_groups':['g']*31}).encode())
        with self.assertRaises(ValueError):run(json.dumps({'texts':['x'*4097]*40,'source_groups':[str(i) for i in range(40)]}).encode())

    def test_08_original_worker_integration_if_available(self):
        try:from v13.student_worker import raw_features,split
        except ImportError:self.skipTest('full A3 student worker unavailable in local scratch')
        texts=[f'project rule {i} describes value {i*i}' for i in range(48)]
        groups=[f'project_{i}' for i in range(48)]
        raw=json.dumps({'texts':texts,'source_groups':groups},sort_keys=True).encode()
        r=run(raw)
        self.assertEqual(r['train_sources']+r['heldout_sources'],48)
        self.assertFalse(r['threshold']['threshold_uses_heldout'])
        self.assertEqual(r['student_parameter_updates'],0)

if __name__=='__main__':unittest.main()
