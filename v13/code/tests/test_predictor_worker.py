"""Analytic local-gradient/EMA tests on explicit numerical fixtures only."""
from pathlib import Path
import tempfile
import unittest
import json
from unittest.mock import patch
import numpy as np
from v13.config import initialize
from v13.predictor_worker import gradient_check,loss_gradient,optimize,train
from v13.runtime import Runtime
from v13.common import Unavailable

class PredictorMath(unittest.TestCase):
    def test_gradient_and_exact_ema_one_step_without_target_gradient(self):
        rng=np.random.default_rng(91);x=rng.normal(size=(10,8));y=rng.normal(size=(10,8));p=rng.normal(size=(8,3))*.1;q=np.eye(3);target=p.copy();anchor=p.copy()
        self.assertLess(gradient_check(x,y,p,q,target,anchor),1e-5)
        with tempfile.TemporaryDirectory() as d:cfg=initialize(Path(d))|{'predictor_steps':1}
        a,b,t,_=optimize(x,y,p,q,target,anchor,cfg)
        np.testing.assert_allclose(t,cfg['ema_decay']*target+(1-cfg['ema_decay'])*a,rtol=0,atol=1e-15)
        np.testing.assert_array_equal(target,p);self.assertFalse(np.array_equal(a,p))
        _,gp,gq,_=loss_gradient(x,y,p,q,target,anchor);norm=np.sqrt(np.sum(gp*gp)+np.sum(gq*gq))*cfg['predictor_lr'];scale=min(1,cfg['max_update_norm']/norm)
        np.testing.assert_allclose(a,p-cfg['predictor_lr']*gp*scale)
    def test_temporal_pairs_split_by_source_and_collapsed_target_cannot_commit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);cfg=initialize(p)|{'predictor_steps':2};x=np.ones((36,2048));groups=[str(i//3) for i in range(36)]
            m=train({'config':cfg,'context_states':x.tolist(),'future_states':x.tolist(),'source_groups':groups},p)
            self.assertFalse(set(m['train_source_groups'])&set(m['held_out_source_groups']));self.assertFalse(m['noncollapse_pass']);self.assertFalse(m['commit_eligible'])
    def test_missing_source_coverage_cannot_train(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);cfg=initialize(p);x=np.ones((36,2048))
            with self.assertRaises(ValueError):train({'config':cfg,'context_states':x.tolist(),'future_states':x.tolist(),'source_groups':['same']*36},p)
            self.assertFalse((p/'candidate.npz').exists())

class PredictorFailurePersistence(unittest.TestCase):
    def test_missing_shared_prefix_aborts_with_json_evidence_and_no_commit(self):
        # Deliberately invalid test double exercises refusal, not native quality.
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                for i in range(12):
                    e=r.store.event(r.session,'Distinct observation '+str(i))
                    r.memory.feedback(e['event_id'],'prediction','observe','learn')
                r.cfg['learning_mode']='SHADOW_UPDATE';before=r.store.generation_id
                with patch.object(r.guard,'update',return_value='NORMAL'),patch.object(r.pool,'get_tap') as get:
                    get.return_value.tap.side_effect=[{'token_ids':[1],'vectors':[[0.]]},{'token_ids':[2],'vectors':[[0.]]}]
                    with self.assertRaises(Unavailable):r.learner.shadow_predictor('B1_DETAIL')
                u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1')
                self.assertEqual(u['status'],'ABORTED');self.assertIsNone(u['path'])
                proof=json.loads(u['manifest'])['causal_prefix_proof']
                self.assertIsNone(proof['max_prefix_error']);self.assertFalse(proof['pass'])
                self.assertEqual(before,r.store.generation_id);self.assertIsNone(r.learner.proc)
                self.assertEqual(r.store.integrity(True),[])
            finally:r.close()

if __name__=='__main__':unittest.main()
