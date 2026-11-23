"""Cue math/authority fixtures; synthetic vectors make no native quality claim."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from v13.config import DEFAULTS
from v13.runtime import Runtime
from v13.retrieval_worker import train,infer,pair_features,topic_view,admissible,DIM
from v13.store import telemetry_metrics

def dataset():
    x=[];y=[];groups=[];ids=[]
    for i in range(40):
        for j in range(8):
            label=int(j<4);x.append([1.,.8 if label else .2,.9 if label else .1,0.,0.,1.,1.]+[.002 if label else -.002]*(DIM-7));y.append(label);groups.append('memory-'+str(i));ids.append(hashlib.sha256(f'{i}:{j}'.encode()).hexdigest())
    return {'config':DEFAULTS,'features':x,'labels':y,'memory_groups':groups,'pair_ids':ids}

class RetrievalMath(unittest.TestCase):
    def test_disjoint_memory_groups_gradient_ablation_reload_and_retention(self):
        with tempfile.TemporaryDirectory() as td:
            req=dataset();m=train(req,td);self.assertTrue(m['commit_eligible']);self.assertTrue(m['gradient_check']);self.assertTrue(m['semantic_ablation_pass'])
            partitions=[{req['memory_groups'][i] for i in ids} for ids in m['partition'].values()]
            self.assertTrue(all(not a&b for i,a in enumerate(partitions) for b in partitions[i+1:]))
            path=Path(td)/'candidate.npz';self.assertEqual(infer(req['features'][0],path)['decision'],'admit');self.assertEqual(infer(req['features'][4],path)['decision'],'reject')
            self.assertEqual(infer([1.,.8,.9,0.,0.,0.,0.]+req['features'][0][7:],path)['decision'],'baseline')
            active=Path(td)/'active.npz';active.write_bytes(path.read_bytes());req['active_checkpoint']=str(active);again=train(req,td)
            self.assertGreater(again['retained_test']['n'],0);self.assertTrue(again['retention_pass'])
            req['labels']=[1-v for v in req['labels']];failed=train(req,td);self.assertFalse(failed['retained_test']['pass']);self.assertFalse(failed['commit_eligible'])
    def test_invalid_native_features_duplicate_pairs_and_one_memory_refuse(self):
        vec=np.ones(3072)
        self.assertEqual(len(pair_features('Projekt Alpha Mittel','Projekt Alpha Budget',vec,vec,vec,vec)),DIM)
        for bad in ([],np.zeros(3072),np.ones(32),np.full(3072,float('nan'))):
            with self.assertRaises(ValueError):pair_features('x','y',bad,vec,vec,vec)
        with tempfile.TemporaryDirectory() as td:
            req=dataset();req['pair_ids'][1]=req['pair_ids'][0]
            with self.assertRaises(ValueError):train(req,td)
            req=dataset();req['memory_groups']=['one']*len(req['labels'])
            with self.assertRaises(ValueError):train(req,td)
    def test_entity_guard_topic_transform_and_private_telemetry(self):
        self.assertFalse(admissible('Projekt Alpha Mittel','Projekt Beta Budget'))
        self.assertEqual(topic_view('Projekt Alpha Budget'),'Budget')
        p=telemetry_metrics({'component':'memory_retrieval','prediction':{'probability':.9,'decision':'admit','actual_text':'private'}})
        self.assertEqual(p['prediction']['probability'],.9);self.assertNotIn('actual_text',p['prediction'])

class RetrievalAuthority(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def memory(self,key='Projekt Alpha Budget'):
        e=self.r.store.event(self.r.session,key);return self.r.memory.feedback(e['event_id'],'fact','120 Euro',key=key)
    def test_feedback_is_query_source_bound_and_never_creates_fact(self):
        mid=self.memory();e=self.r.store.event(self.r.session,'Wie hoch sind die Mittel für Projekt Alpha?')
        before=len(self.r.store.rows('SELECT * FROM memories'));self.r.memory.retrieval_feedback(e['event_id'],mid,'relevant','learn')
        self.assertEqual(len(self.r.store.rows('SELECT * FROM memories')),before);self.assertEqual(len(self.r.learner.retrieval_labels()),1)
        self.r.memory.retrieval_feedback(e['event_id'],mid,'irrelevant','record');self.assertEqual(self.r.learner.retrieval_labels(),[])
        with self.assertRaises(ValueError):self.r.learner.shadow_retrieval()
    def test_source_mutation_scope_and_provisional_input_refuse(self):
        mid=self.memory();other=self.r.store.new_session();e=self.r.store.event(other,'Mittel')
        with self.assertRaises(ValueError):self.r.memory.retrieval_feedback(e['event_id'],mid,'relevant')
        with self.assertRaises(ValueError):self.r.store.event(self.r.session,'Mittel',authority='PROVISIONAL')
        e=self.r.store.event(self.r.session,'Mittel');e['authority']='PROVISIONAL'
        with self.r.store.tx() as c:c.execute('UPDATE events SET packet=? WHERE id=?',(json.dumps(e),e['event_id']))
        with self.assertRaises(ValueError):self.r.memory.retrieval_feedback(e['event_id'],mid,'relevant')
        with self.r.store.tx() as c:c.execute('UPDATE memories SET key_text=? WHERE id=?',('anderer Inhalt',mid))
        with self.assertRaises(ValueError):self.r.memory.candidate(mid,self.r.session)
    def test_semantic_admit_reject_baseline_and_cross_entity_guard(self):
        mid=self.memory();seen=[]
        def admit(m):seen.append(m['id']);return {'decision':'admit','probability':.95}
        self.assertEqual(self.r.memory.recall('Projekt Alpha Mittel',self.r.session),[])
        got=self.r.memory.recall('Projekt Alpha Mittel',self.r.session,admit);self.assertEqual(got[0]['id'],mid);self.assertEqual(got[0]['value'],'120 Euro')
        self.assertEqual(self.r.memory.recall('Projekt Beta Mittel',self.r.session,admit),[]);self.assertEqual(seen,[mid])
        self.assertEqual(self.r.memory.recall('Projekt Alpha Budget',self.r.session,lambda m:{'decision':'reject','probability':.01}),[])
        self.assertEqual(self.r.memory.recall('Projekt Alpha Budget',self.r.session,lambda m:None)[0]['id'],mid)
    def test_report_binds_only_approved_supported_relevance_and_exact_value(self):
        mid=self.memory();m=self.r.memory.recall('Projekt Alpha Budget',self.r.session)[0]
        self.assertEqual(self.r.memory.report_context('Projekt Alpha Mittel',[m]),[{'topic':'Projekt Alpha Budget','correction':'120 Euro'}])
        m['retrieval_policy']={'decision':'admit','probability':.9,'in_support':True}
        linked=self.r.memory.report_context('Projekt Alpha Mittel',[m])[0]
        self.assertEqual(linked['matched_query'],'Projekt Alpha Mittel');self.assertEqual(linked['correction'],'120 Euro')
        m['value']='generated replacement'
        with self.assertRaises(ValueError):self.r.memory.report_context('Projekt Alpha Mittel',[m])
    def test_inadmissible_entities_do_not_exhaust_semantic_candidate_budget(self):
        mid=self.memory()
        for i in range(40):self.memory('Projekt Beta'+str(i)+' Budget')
        self.r.cfg['retrieval_candidates']=1
        hits=self.r.memory.recall('Projekt Alpha Mittel',self.r.session,lambda m:{'decision':'admit','probability':.9})
        self.assertEqual([m['id'] for m in hits],[mid])
    def test_preempted_training_aborts_without_generation_change(self):
        mid=self.memory()
        for i in range(48):
            e=self.r.store.event(self.r.session,'Projekt Alpha Frage '+str(i));self.r.memory.retrieval_feedback(e['event_id'],mid,'relevant' if i%2 else 'irrelevant','learn')
        self.r.cfg['learning_mode']='SHADOW_UPDATE';base=self.r.store.generation_id;self.r.cancel_event.set()
        from v13.common import Cancelled
        with self.assertRaises(Cancelled):self.r.learner.shadow_retrieval()
        u=self.r.store.one('SELECT * FROM updates');self.assertEqual(u['status'],'ABORTED');self.assertEqual(self.r.store.generation_id,base)

if __name__=='__main__':unittest.main()
