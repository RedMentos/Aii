import math
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from dataclasses import replace
from v13.backends import ModelDeclaration, admission_problems
from v13.contracts import Origin, Event
from v13.eligibility import Eligibility
from v13.policy import Age0Policy, budget_steps
from v13.scheduler import Coordinator
from v13.storage import Repository, ValidationReport, ValidationFailed, StaleSnapshot
from v13.demo_learning import ScalarDemoLearner

def accept(values, base):
    return ValidationReport(True, 'unit-test-validator', ('fixture only',))

class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.base = self.repo.initialize({'demo.gist.readout':1., 'demo.detail.readout':2.}, 'v1')
        self.event = self.repo.append_experience(Origin.OBSERVED, 'test:input', {'text':'a'}, 'v1')
        self.clock = [100.]
        self.traces = Eligibility(clock=lambda:self.clock[0])
        self.coordinator = Coordinator()
        self.learner = ScalarDemoLearner(self.repo, self.traces, self.coordinator)
    def tearDown(self): self.repo.close()
    def activate(self):
        self.traces.activate('demo.gist.readout', self.event.id, 'v1', self.base.id)
    def step(self, budget=1, mod=1):
        return self.learner.step(self.event.id, {'demo.gist.readout':1.,'demo.detail.readout':100.}, mod, budget)
    def test_inactive_path_unchanged_and_active_persists(self):
        self.activate(); self.assertEqual(self.step().status,'committed')
        self.assertLess(self.repo.current().weights['demo.gist.readout'],1)
        self.assertEqual(self.repo.current().weights['demo.detail.readout'],2)
    def test_no_activation_no_update(self):
        self.assertEqual(self.step().status,'no_eligible_update')
        self.assertEqual(self.repo.current().id,self.base.id)
    def test_expired_trace_no_update(self):
        self.activate();self.clock[0]=131
        self.assertEqual(self.step().status,'no_eligible_update')
    def test_other_episode_cannot_borrow_trace(self):
        other=self.repo.append_experience(Origin.OBSERVED,'test:other',{},'v1')
        self.traces.activate('demo.gist.readout',other.id,'v1',self.base.id)
        self.assertEqual(self.step().status,'no_eligible_update')
    def test_stale_snapshot_trace_no_update(self):
        self.activate();self.repo.commit(self.base.weights,self.base.id,'v1',accept)
        self.assertEqual(self.step().status,'no_eligible_update')
    def test_stale_model_no_update(self):
        self.activate();self.repo.commit(self.base.weights,self.base.id,'v2',accept)
        self.assertEqual(self.step().status,'stale_experience_model')
    def test_budget_and_modulation_zero(self):
        self.activate();self.assertEqual(self.step(budget=0).status,'budget_zero')
        self.assertEqual(self.step(mod=0).status,'modulation_zero')
        self.assertEqual(self.repo.current().id,self.base.id)
    def test_invalid_budgets_and_signed_modulation_rejected(self):
        for x in (-1,1.1,math.nan,math.inf,True,'0.5'):
            with self.assertRaises(ValueError): budget_steps(x)
        with self.assertRaises(ValueError): self.step(mod=-1)
    def test_inference_prevents_training(self):
        self.activate()
        with self.coordinator.inference():
            self.assertEqual(self.step().status,'inference_priority')
        self.assertEqual(self.repo.current().id,self.base.id)
    def test_failed_validation_keeps_live_and_cache(self):
        self.repo.cache_put('k',{'x':1})
        with self.assertRaises(ValidationFailed):
            self.repo.commit({'demo.gist.readout':9}, self.base.id,'v1',
               lambda a,b:ValidationReport(False,'reject',('regression',)))
        self.assertEqual(self.repo.current().id,self.base.id)
        self.assertEqual(self.repo.cache_get('k'),{'x':1})
    def test_commit_invalidates_cache_rollback_creates_new_version(self):
        self.repo.cache_put('k',3); self.activate();self.step()
        current=self.repo.current();self.assertIsNone(self.repo.cache_get('k'))
        restored=self.repo.rollback(self.base.id,current.id)
        self.assertGreater(restored.id,current.id);self.assertEqual(restored.weights,self.base.weights)
    def test_stale_candidate_rejected(self):
        self.repo.commit(self.base.weights,self.base.id,'v1',accept)
        with self.assertRaises(StaleSnapshot): self.repo.commit(self.base.weights,self.base.id,'v1',accept)
    def test_synthetic_not_promoted_and_source_required(self):
        dream=self.repo.append_experience(Origin.SYNTHETIC,'test:dream',{},'v1',[self.event.id])
        with self.assertRaises(ValueError):
            self.repo.append_experience(Origin.OBSERVED,'test:repeat',{},'v1',[dream.id])
        self.assertEqual(len(self.repo.observed_evidence()),1)
        with self.assertRaises(ValueError): self.repo.append_experience(Origin.OBSERVED,'',{},'v1')
    def test_experience_and_snapshot_are_immutable(self):
        detached=self.event.payload();detached['text']='b'
        self.assertEqual(self.repo.experience(self.event.id).payload()['text'],'a')
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.db.execute('UPDATE experiences SET origin="synthetic"')
        with self.assertRaises(TypeError): self.base.weights['demo.gist.readout']=9
    def test_age_promotion_unavailable(self):
        with self.assertRaises(RuntimeError): Age0Policy().promote()
    def test_invalid_event_rejected(self):
        with self.assertRaises(ValueError): Event('id','made_up','test','e','v',1,0,'{}')

class RestartTests(unittest.TestCase):
    def test_restart_preserves_data_not_eligibility(self):
        with tempfile.TemporaryDirectory() as d:
            p=str(Path(d)/'x.db')
            with Repository(p) as r:
                b=r.initialize({'demo.gist.readout':1},'v1')
                e=r.append_experience(Origin.OBSERVED,'test:source',{'a':3},'v1')
            with Repository(p) as r:
                self.assertEqual(r.current().id,b.id)
                self.assertEqual(r.experience(e.id).payload(),{'a':3})
                self.assertIsNone(Eligibility().get('demo.gist.readout',e.id,'v1',b.id))
    def test_request_during_slice_is_seen_before_next_slice(self):
        c=Coordinator();entered=threading.Event();release=threading.Event();ran=[]
        def learn():
            c.training_slice(lambda cancel:(entered.set(),release.wait(2),ran.append(cancel())))
        t=threading.Thread(target=learn);t.start();self.assertTrue(entered.wait(2))
        announced=threading.Event()
        def infer():
            with c.inference(): announced.set()
        u=threading.Thread(target=infer);u.start()
        # Wait boundedly for the request flag, not for inference lock acquisition.
        self.assertTrue(c._inference_requested.wait(2));release.set()
        t.join(2);u.join(2)
        self.assertFalse(t.is_alive());self.assertFalse(u.is_alive())
        self.assertEqual(ran,[True]);self.assertTrue(announced.is_set())

class ManifestTests(unittest.TestCase):
    def test_same_model_unknown_backend_and_missing_hooks_rejected(self):
        a=ModelDeclaration('x','rev','x','moe',True,'unknown',4,2)
        j=replace(a,model_id='j',family='j',architecture='dense')
        issues=admission_problems(a,a,j)
        self.assertTrue(any('different' in s for s in issues))
        self.assertTrue(any('hidden_export' in s for s in issues))
        self.assertTrue(any('backend' in s for s in issues))
    def test_dense_does_not_count_as_second_moe(self):
        a=ModelDeclaration('a','rev','a','moe',True,'test',4,2)
        b=replace(a,model_id='b',family='b',architecture='dense',native_top_k=1)
        j=replace(b,model_id='j',family='j')
        self.assertTrue(any('detail: requires genuine MoE' in s for s in admission_problems(a,b,j)))

if __name__=='__main__': unittest.main()
