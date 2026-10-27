"""WP-BP3 / Z10: §91 MoE update order as enforced state (no model needed)."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from v13.runtime import Runtime
from v13 import moe_learning as ML

def calibration():
    m=ML.monitor();v=[{'router_kl':.01*(1+i%3),'topk_flip_rate':.05*(1+i%3),'router_input_norm_shift':.02,'residual_norm_shift':.03,
                       'expert_hist_shift':.02,'shared_drift':.03,'router_input_drift':.04} for i in range(12)]
    return m.calibrate(v)

def report(**kw):
    r={'window':[8,9],'arm':'active16','rank':8,'k':16,'delta_params':1000,'new_task_loss_start':5.,'new_task_loss_end':.4,
       'old_task_loss_delta':.05,'rollback_removed_delta':0.,'router':{'router_kl':.01,'topk_flip_rate':.05,'router_input_norm_shift':.02,'residual_norm_shift':.03},
       'body':{'model':'euromoe','revision':'96e19829'},'evidence_level':'test'}
    return r|kw

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.m=ML.MoELearning(self.r.store)
    def tearDown(self):self.r.close();self.tmp.cleanup()

class Order(Base):
    def test_phase_a_groups_free_everything_else_locked(self):
        self.assertTrue(self.m.check_job(['predictor','projector'])[0])
        ok,why=self.m.check_job(['expert_delta']);self.assertFalse(ok);self.assertIn('phase A retention evidence',' '.join(why))
        for g in ('router','shared','base'):self.assertFalse(self.m.check_job([g])[0])
    def test_expert_delta_after_phase_a_evidence_and_monitor(self):
        self.m.set_evidence(phase_a_retention_ok=True,route_monitor_active=True,retention_ok=True)
        self.assertTrue(self.m.check_job(['expert_delta'])[0])
        self.assertFalse(self.m.check_job(['expert_delta','router'])[0])   # router never joint
        ok,why=self.m.check_job(['router']);self.assertFalse(ok);self.assertIn('missed-routing',' '.join(why))
    def test_router_and_shared_only_shadow_even_with_evidence(self):
        self.m.set_evidence(phase_a_retention_ok=True,route_monitor_active=True,retention_ok=True,missed_routing=True,pre_router_bottleneck='PRE_ROUTER_BOTTLENECK')
        for g in ('router','shared'):
            ok,why=self.m.check_job([g]);self.assertFalse(ok);self.assertIn('SHADOW only',' '.join(why))
    def test_unknown_group_and_unknown_evidence_refused(self):
        self.assertFalse(self.m.check_job(['lora'])[0])
        with self.assertRaises(ValueError):self.m.set_evidence(nonsense=True)
    def test_off_mode_blocks_phases_beyond_a(self):
        o=ML.MoELearning(self.r.store,'off');o.set_evidence(phase_a_retention_ok=True,route_monitor_active=True,retention_ok=True)
        self.assertFalse(o.check_job(['expert_delta'])[0]);self.assertTrue(o.check_job(['predictor'])[0])
        with self.assertRaises(PermissionError):o.record_delta(report(),calibration())

class Deltas(Base):
    def test_good_report_becomes_shadow_ok_and_unlocks_retention(self):
        rec=self.m.record_delta(report(),calibration());self.assertEqual((rec['status'],rec['gate']),('DELTA_SHADOW_OK','PASS'))
        self.assertTrue(self.m.evidence()['retention_ok']);self.assertTrue(self.m.evidence()['route_monitor_active'])
    def test_rejections(self):
        cal=calibration()
        for kw,needle in ((dict(new_task_loss_end=4.),'did not learn'),(dict(rollback_removed_delta=.01),'rollback'),
                          (dict(old_task_loss_delta=.9),'old-task loss delta'),
                          (dict(router={'router_kl':.5,'topk_flip_rate':.05,'router_input_norm_shift':.02,'residual_norm_shift':.03}),'router_kl'),
                          (dict(body=None),'missing body')):
            rec=self.m.record_delta(report(**kw),cal);self.assertEqual(rec['status'],'DELTA_REJECTED',kw);self.assertIn(needle,' '.join(rec['why']))
        self.assertFalse(self.m.evidence()['retention_ok'])
    def test_uncalibrated_never_passes(self):
        rec=self.m.record_delta(report(),{'status':'UNCALIBRATED','thresholds':{}});self.assertEqual(rec['status'],'DELTA_REJECTED')
    def test_commit_needs_everything_and_active_mode(self):
        rec=self.m.record_delta(report(),calibration())
        r=self.m.commit(rec['id'],eligible=True,error=None,modulator='surprise',permission=True);self.assertEqual(r['missing'],['error signal'])
        r=self.m.commit(rec['id'],eligible=True,error=.4,modulator='surprise',permission=True);self.assertTrue(r['would_commit']);self.assertFalse(r['commit'])
        a=ML.MoELearning(self.r.store,'active')
        r=a.commit(rec['id'],eligible=True,error=.4,modulator='surprise',permission=True);self.assertEqual((r['commit'],r['status']),(True,'COMMITTED'))
        a.rollback(rec['id']);self.assertEqual(a.report()['deltas'][rec['id']]['status'],'ROLLED_BACK')
        self.assertFalse(a.commit(rec['id'],eligible=True,error=.4,modulator='surprise',permission=True)['commit'])
    def test_rejected_delta_cannot_commit(self):
        rec=self.m.record_delta(report(new_task_loss_end=4.),calibration());a=ML.MoELearning(self.r.store,'active')
        self.assertIn('retention',a.commit(rec['id'],eligible=True,error=.4,modulator='m',permission=True)['missing'])

class Select(unittest.TestCase):
    def test_top_k_by_hits_ties_low_index(self):
        self.assertEqual(ML.select_experts([0,5,5,1,9,0],3),[1,2,4]);self.assertEqual(ML.select_experts([1,1,1],2),[0,1]);self.assertEqual(ML.select_experts([3],0),[])

if __name__=='__main__':unittest.main()
