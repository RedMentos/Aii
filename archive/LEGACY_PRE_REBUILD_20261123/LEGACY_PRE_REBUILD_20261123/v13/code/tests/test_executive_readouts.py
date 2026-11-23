"""Numerical and persistence tests; these fixtures are not native-model evidence."""
import json
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from v13.config import initialize
from v13.runtime import Runtime
from v13.operator import Operator
from v13.readout_worker import train,infer,partitions

class Numerical(unittest.TestCase):
    def data(self,component,p):
        k=4 if component=='wake' else 2;x=np.repeat(np.eye(k),6,axis=0);y=np.repeat(np.arange(k),6)
        return {'component':component,'config':initialize(p),'embeddings':x.tolist(),'labels':y.tolist(),
                'scaffold_labels':[1]*len(y) if component=='halt' else y.tolist(),'context_hashes':[str(i) for i in range(len(y))]}
    def test_calibration_partition_is_disjoint_and_test_does_not_fit_parameters(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);inp=self.data('wake',p);a=p/'a';b=p/'b';a.mkdir();b.mkdir();m=train(inp,a)
            ti,ci,vi=partitions(np.asarray(inp['labels']),4)
            self.assertEqual(len(set(ti)|set(ci)|set(vi)),len(inp['labels']));self.assertFalse(set(ci)&set(vi))
            for i in vi:inp['embeddings'][i]=[-q for q in inp['embeddings'][i]]
            failed=train(inp,b)
            with np.load(a/'candidate.npz') as x,np.load(b/'candidate.npz') as y:
                self.assertTrue(np.array_equal(x['weights'],y['weights']));self.assertEqual(float(x['temperature']),float(y['temperature']))
            self.assertTrue(m['commit_eligible']);self.assertFalse(failed['commit_eligible'])
            self.assertTrue(m['gradient_check']);self.assertLess(m['held_out']['after']['brier'],m['held_out']['uncalibrated']['brier'])
            self.assertFalse(infer([-1,0,0,0],a/'candidate.npz')['in_support'])
    def test_halt_pareto_and_hard_example_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);inp=self.data('halt',p);m=train(inp,p)
            self.assertTrue(m['commit_eligible']);self.assertEqual(m['missed_continue'],0);self.assertLess(m['cost_after'],m['cost_before'])
            # A scaffold already perfect at minimum labelled cost leaves no Pareto gain.
            inp['scaffold_labels']=inp['labels'];m=train(inp,p);self.assertFalse(m['commit_eligible'])
    def test_duplicate_contexts_and_missing_class_rejected_before_update(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);inp=self.data('wake',p);inp['context_hashes'][-1]=inp['context_hashes'][0]
            with self.assertRaises(ValueError):train(inp,p)
            self.assertFalse((p/'candidate.npz').exists())

class Labels(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_feedback_requires_decision_and_stays_out_of_fact_memory(self):
        r=self.r;e=r.store.event(r.session,'Projekt Aurora Budget vergleichen')
        with self.assertRaises(ValueError):r.memory.feedback(e['event_id'],'wake','both','learn')
        p=r.learner.decide('wake',e,'both',time.monotonic()+5)
        m=r.memory.feedback(e['event_id'],'wake','both','learn')
        self.assertEqual(r.memory.recall('Projekt Aurora Budget vergleichen',r.session),[])
        record=r.store.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=?",(e['event_id'],));self.assertEqual(json.loads(record['payload'])['decision_packet_id'],p['packet_id'])
        session=r.session;r.close();self.r=Runtime(Path(self.tmp.name));self.assertEqual(self.r.session,session)
        self.assertIsNotNone(self.r.store.one('SELECT id FROM memories WHERE id=?',(m,)))
    def test_record_mode_has_no_readout_updates_and_bad_labels_rejected(self):
        r=self.r
        with self.assertRaises(ValueError):r.learner.shadow_readout('wake')
        self.assertEqual(r.store.rows('SELECT * FROM updates'),[])
        e=r.store.event(r.session,'Test');r.learner.decide('wake',e,'none',time.monotonic()+1)
        with self.assertRaises(ValueError):r.memory.feedback(e['event_id'],'wake','delete','learn')
        with self.assertRaises(ValueError):Operator(r).run(':learn mystery')
    def test_halt_rejects_missing_or_foreign_trajectory(self):
        e=self.r.store.event(self.r.session,'Test')
        with self.assertRaises(ValueError):self.r.learner.decide('halt',e,'halt',time.monotonic()+1)
    def test_readout_telemetry_preserves_numeric_evidence_without_context_text(self):
        from v13.store import telemetry_metrics
        x=telemetry_metrics({'component':'wake','prediction':{'confidence':.8,'in_support':True,'probabilities':[.8,.1,.05,.05]},'context_ref':{'sha256':'a'*64},'text':'secret'})
        self.assertEqual(x['prediction']['confidence'],.8);self.assertNotIn('text',x)

if __name__=='__main__':unittest.main()
