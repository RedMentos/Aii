"""WP-S4: LeJEPA SIGReg next to the EMA target, on explicit numerical fixtures only."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from v13.config import initialize
from v13.predictor_worker import ablation,collapse_telemetry,gradient_check,loss_gradient,optimize,sigreg,sigreg_directions,train

def fixture(seed=5,n=120,dim=32):
    # Low-rank latent dynamics plus noise; rows RMS-normalised like native taps.
    rng=np.random.default_rng(seed);lat=rng.normal(size=(n,4));mix=rng.normal(size=(4,dim))
    x=lat@mix+.5*rng.normal(size=(n,dim));y=(lat*.9)@mix+.5*rng.normal(size=(n,dim))
    return x/np.sqrt((x*x).mean(1,keepdims=True)),y/np.sqrt((y*y).mean(1,keepdims=True)),rng

class SigregMath(unittest.TestCase):
    def test_statistic_separates_gaussian_from_collapse(self):
        rng=np.random.default_rng(3);d=sigreg_directions(8,32,1);g=rng.normal(size=(2000,8))
        gauss=sigreg(g,d)[0];shrunk=sigreg(g*.01,d)[0];rank1=sigreg(np.outer(g[:,0],np.ones(8))/np.sqrt(8),d)[0]
        self.assertLess(gauss,.002);self.assertGreater(shrunk,50*gauss);self.assertGreater(rank1,10*gauss)
    def test_analytic_gradient_matches_finite_differences(self):
        x,y,rng=fixture(n=40);p=np.linalg.qr(rng.normal(size=(32,8)))[0];d=sigreg_directions(8,16,2)
        for mode in ('sigreg','both'):self.assertLess(gradient_check(x,y,p,np.eye(8),p.copy(),p.copy(),mode=mode,directions=d,sigreg_weight=1.),1e-5)
    def test_default_ema_path_is_unchanged(self):
        x,y,rng=fixture(n=30);p=np.linalg.qr(rng.normal(size=(32,8)))[0]
        loss,_,_,parts=loss_gradient(x,y,p,np.eye(8),p.copy(),p.copy())
        self.assertIn('variance_penalty',parts);self.assertNotIn('sigreg',parts)
    def test_sigreg_only_uses_online_stop_gradient_target(self):
        x,y,rng=fixture(n=30);p=np.linalg.qr(rng.normal(size=(32,8)))[0]
        a,_,t,h=optimize(x,y,p,np.eye(8),p.copy(),p.copy(),{'seed':1,'predictor_steps':3,'predictor_lr':.01,'max_update_norm':.02,'ema_decay':.99,'predictor_regularizer':'sigreg'})
        np.testing.assert_array_equal(a,t);self.assertEqual(h['regularizer'],'sigreg');self.assertIn('isotropy',h['collapse_telemetry'][0])
    def test_unknown_mode_is_rejected(self):
        x,y,rng=fixture(n=30);p=np.linalg.qr(rng.normal(size=(32,8)))[0]
        with self.assertRaises(ValueError):optimize(x,y,p,np.eye(8),p,p,{'seed':1,'predictor_steps':1,'predictor_lr':.01,'max_update_norm':.02,'ema_decay':.99,'predictor_regularizer':'none'})

class CollapseAblation(unittest.TestCase):
    def test_sigreg_recovers_shrunk_projector_where_ema_floor_does_not(self):
        x,y,rng=fixture();p=np.linalg.qr(rng.normal(size=(32,8)))[0]*.02
        self.assertLess(collapse_telemetry(x@p)['std_mean'],.05)
        cfg={'seed':7,'predictor_steps':240,'predictor_lr':.5,'max_update_norm':.2,'ema_decay':.99}
        r=ablation(x,y,p,np.eye(8),p.copy(),p.copy(),cfg)
        self.assertEqual(set(r),{'ema','sigreg','both'})
        self.assertLess(r['ema']['context_embedding']['std_mean'],.25)
        for mode in ('sigreg','both'):self.assertGreater(r[mode]['context_embedding']['std_mean'],.5)
        self.assertGreater(r['sigreg']['context_embedding']['isotropy'],.4)
        self.assertGreater(r['sigreg']['target_embedding']['std_mean'],.5)
    def test_collapse_telemetry_reports_rank_and_isotropy(self):
        rng=np.random.default_rng(0);iso=collapse_telemetry(rng.normal(size=(4000,8)));flat=collapse_telemetry(np.outer(rng.normal(size=500),np.ones(8)))
        self.assertGreater(iso['isotropy'],.95);self.assertEqual(iso['effective_rank'],8)
        self.assertLess(flat['isotropy'],.2);self.assertEqual(flat['effective_rank'],1)
        self.assertEqual(collapse_telemetry(np.zeros((5,4)))['effective_rank'],0)

class SigregTrainJob(unittest.TestCase):
    def test_worker_job_records_mode_and_telemetry(self):
        rng=np.random.default_rng(11);x=rng.normal(size=(36,2048));y=x+.2*rng.normal(size=(36,2048));groups=[str(i//3) for i in range(36)]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);cfg=initialize(p)|{'predictor_steps':4,'predictor_regularizer':'both'}
            m=train({'config':cfg,'context_states':x.tolist(),'future_states':y.tolist(),'source_groups':groups},p)
        self.assertEqual(m['regularizer'],'both');self.assertTrue(m['gradient_check']);self.assertTrue(m['deterministic_repeat'])
        self.assertIn('isotropy',m['after']['context_embedding']);self.assertIn('sigreg',m['history']['collapse_telemetry'][0])

if __name__=='__main__':unittest.main()
