"""WP-V2 learning invariants restored from blueprint v4/v5 (2026-10-09).

No LoRA/merge path exists in this build, so the v4 "no double LoRA after merge"
invariant has nothing to check yet; it must be added with the first merge path.
"""
import unittest
import numpy as np
from v13 import predictor_worker as pw
from v13.config import DEFAULTS

class PredictorInvariants(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(7);self.x=rng.normal(size=(24,6));self.y=rng.normal(size=(24,6))
        self.p=rng.normal(size=(6,4))*.3;self.q=rng.normal(size=(4,4))*.3;self.t=self.p.copy();self.a=self.p.copy()
        self.cfg=dict(DEFAULTS)|{'predictor_steps':5,'predictor_regularizer':'ema'}
    def test_optimizer_is_isolated_from_its_inputs(self):
        before=[v.copy() for v in (self.x,self.y,self.p,self.q,self.t,self.a)]
        pw.optimize(self.x,self.y,self.p,self.q,self.t,self.a,self.cfg)
        for old,new in zip(before,(self.x,self.y,self.p,self.q,self.t,self.a)):self.assertTrue(np.array_equal(old,new))
    def test_target_is_stop_gradient_ema_and_moves(self):
        cfg=self.cfg|{'predictor_steps':1};t=self.t+.5
        p,q,target,h=pw.optimize(self.x,self.y,self.p,self.q,t,self.a,cfg)
        self.assertTrue(np.allclose(target,cfg['ema_decay']*t+(1-cfg['ema_decay'])*p))
        self.assertFalse(np.array_equal(target,t))
        self.assertLess(np.abs(target-t).max(),np.abs(p-t).max())
        self.assertEqual(len(pw.loss_gradient(self.x,self.y,self.p,self.q,t,self.a)),4)  # gradients for p and q only
        self.assertLessEqual(h['max_applied_step_norm'],cfg['max_update_norm']*1.000001)
    def test_loss_is_never_negative_even_for_bad_outcomes(self):
        rng=np.random.default_rng(3)
        for mode in ('ema','sigreg','both'):
            for _ in range(20):
                x,y=rng.normal(size=(2,16,6))*rng.uniform(.01,50);p,t,a=rng.normal(size=(3,6,4));q=rng.normal(size=(4,4))
                kw=pw.regularizer_kwargs(self.cfg|{'predictor_regularizer':mode},4,0)
                loss,_,_,parts=pw.loss_gradient(x,y,p,q,t,a,**kw)
                self.assertGreaterEqual(loss,0.);self.assertTrue(all(v>=0 for v in parts.values()),parts)


class DataMixBeforeTraining(unittest.TestCase):
    """Ablation §99 follow-up: the data mix holds before every weight-training job (WP-AG6 stage + train)."""
    def test_item_origin_and_mix(self):
        from v13 import guards as G
        h=[{'kind':'fact','prompt':str(i),'target':'x','source_ref':{'label':None}} for i in range(9)]
        own=[{'kind':'rated_answer','target':'m'+str(i)} for i in range(5)];dream=[{'kind':'fact','source_ref':{'label':'DREAM_HYPOTHESIS'}}]
        self.assertEqual([G.item_origin(x) for x in (h[0],own[0],dream[0],{'origin':'seed'},{'label_source':'own_final_answer'})],['human','self','dream','seed','self'])
        kept,rep=G.mix_for_training(h+own+dream+[{'origin':'seed'}])
        self.assertEqual(rep['after']['human'],9);self.assertLessEqual(rep['after']['self'],1);self.assertEqual(rep['after']['seed'],0);self.assertTrue(rep['check']['pass'])
        kept,rep=G.mix_for_training(own);self.assertEqual(kept,[]);self.assertFalse(rep['check']['pass'])
    def test_weight_consolidation_refuses_self_only_and_trims_mixed(self):
        import tempfile
        from pathlib import Path
        from v13.runtime import Runtime
        from v13.agi.weights import WeightConsolidation
        with tempfile.TemporaryDirectory() as t:
            r=Runtime(Path(t))
            try:
                w=WeightConsolidation(r.store,r.cfg|{'learning_mode':'SHADOW'})
                w.candidates=lambda require_replay_pass=True,**kw:[]
                w.rated_candidates=lambda:[{'memory_id':'rating:'+str(i),'kind':'rated_answer','prompt':'q','target':'a'+str(i),'source_ref':{}} for i in range(3)]
                self.assertEqual(w.stage(origin='USER',include_rated=True)['status'],'DATA_MIX_FAIL')
                w.candidates=lambda require_replay_pass=True,**kw:[{'memory_id':'m'+str(i),'kind':'fact','prompt':'k'+str(i),'target':'v','source_ref':{}} for i in range(9)]
                out=w.stage(origin='USER',include_rated=True);b=w.batch(out['batch_id'])
                self.assertEqual(sum(1 for i in b['items'] if i['kind']=='rated_answer'),1);self.assertTrue(b['data_mix']['check']['pass'])
                def poison(st):st['batches'][out['batch_id']]['items']+=[{'kind':'sdft','origin':'dream','target':'z'}]*5
                w.box.mutate(poison);self.assertEqual(w.train(out['batch_id'])['status'],'DATA_MIX_FAIL')
            finally:r.close()

if __name__=='__main__':unittest.main()
