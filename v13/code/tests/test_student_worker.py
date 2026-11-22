"""A3 numerical/refusal tests; numerical fixtures are not native proofs."""
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from v13.config import initialize
from v13.runtime import Runtime
from v13.common import Cancelled
from v13.common import atomic_write,dumps,file_hash
from v13.contracts import packet
from v13.student_worker import raw_features,split,objective,gradient_check,optimize,train

class StudentMath(unittest.TestCase):
    def test_analytic_alignment_and_reconstruction_gradients(self):
        rng=np.random.default_rng(14);x=rng.normal(size=(10,8));t=rng.normal(size=(10,3));p=rng.normal(size=(8,3))*.1;r=rng.normal(size=(3,8))*.1
        self.assertLess(gradient_check(x,t,p,r),1e-5)
        cfg={'student_steps':1,'student_lr':.01,'max_update_norm':.02};a,b,h=optimize(x,t,p,r,cfg)
        self.assertLess(objective(x,t,a,b)[0],objective(x,t,p,r)[0]);self.assertLessEqual(h['max_applied_step_norm'],.02+1e-12)
        _,gp,gr,_=objective(x,t,p,r,alignment=0.,reconstruction=0.)
        np.testing.assert_array_equal(gr,np.zeros_like(r));np.testing.assert_allclose(gp,2e-4*p/p.size)
    def test_raw_utf8_stem_is_stable_and_rejects_silent_truncation(self):
        a=raw_features('Äpfel 🍎 kosten 120 Euro.');np.testing.assert_array_equal(a,raw_features('Äpfel 🍎 kosten 120 Euro.'))
        self.assertEqual(len(a),512);self.assertAlmostEqual(float(np.linalg.norm(a)),1.)
        self.assertFalse(np.array_equal(a,raw_features('Äpfel 🍎 kosten 240 Euro.')))
        for text in ('','ä'*2049):
            with self.assertRaises(ValueError):raw_features(text)
    def test_source_partition_stays_fixed_when_more_sources_arrive(self):
        groups=[hashlib.sha256(str(i).encode()).hexdigest() for i in range(96)];a,b=split(groups[:64]);c,d=split(groups)
        self.assertFalse(set(a)&set(b));self.assertEqual(set(a)|set(b),set(range(64)))
        self.assertTrue(set(a)<=set(c));self.assertTrue(set(b)<=set(d))
        with self.assertRaises(ValueError):split([groups[0]]*64)
    def test_constant_teacher_cannot_promote_collapsed_student(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);cfg=initialize(out)|{'student_steps':2};texts=['Projekt Test: Budget '+str(i)+' Euro.' for i in range(64)]
            groups=[hashlib.sha256(s.encode()).hexdigest() for s in texts];targets=np.ones((64,3072))
            m=train({'config':cfg,'texts':texts,'source_groups':groups,'teacher_embeddings':targets.tolist()},out)
            self.assertFalse(m['noncollapse_pass']);self.assertFalse(m['commit_eligible']);self.assertTrue(m['gradient_check'])
    def test_invalid_teacher_shapes_have_no_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);texts=['Budget '+str(i) for i in range(64)];groups=[hashlib.sha256(s.encode()).hexdigest() for s in texts]
            with self.assertRaises(ValueError):train({'config':initialize(p),'texts':texts,'source_groups':groups,'teacher_embeddings':[[1.]]*64},p)
            self.assertFalse((p/'candidate.npz').exists())

class StudentAuthority(unittest.TestCase):
    def test_latest_record_permission_revokes_training_admission(self):
        with tempfile.TemporaryDirectory() as folder:
            r=Runtime(Path(folder))
            try:
                events=[]
                for i in range(32):
                    e=r.store.event(r.session,'Budget '+str(i));r.memory.feedback(e['event_id'],'alignment','observe','learn');events.append(e)
                r.memory.feedback(events[-1]['event_id'],'alignment','observe','record');r.cfg['learning_mode']='SHADOW_UPDATE'
                with patch.object(r.guard,'update',return_value='NORMAL'):
                    with self.assertRaises(ValueError):r.learner.shadow_student()
                self.assertEqual(r.store.rows('SELECT * FROM updates'),[])
            finally:r.close()
    def test_percept_feature_tamper_is_detected_and_cannot_gain_routing_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            r=Runtime(Path(folder))
            try:
                e=r.store.event(r.session,'Budget 120 Euro');path=r.home/'data/blobs/a3-fixture.json';atomic_write(path,dumps({'fixture':'not a native proof'}))
                p=packet('PerceptPacket','A3_STUDENT',e['event_id'],e['brain_generation_id'],[e['source_ref']],source_ref=e['source_ref'],segments=[],modality='text',student_feature_path=str(path.relative_to(r.home)),student_feature_sha256=file_hash(path))
                r.store.add_packet('PerceptPacket',p);self.assertEqual(r.store.integrity(True),[])
                atomic_write(path,'tampered');self.assertTrue(any('Percept-Artefakt' in x for x in r.store.integrity(True)))
                result=r.learner.compare_student_route(e,{'route':'detail'})
                self.assertEqual(result['status'],'UNAVAILABLE');self.assertEqual(result['routing_authority'],0)
                self.assertEqual(r.store.rows("SELECT * FROM packets WHERE kind='StudentEvaluation'"),[])
            finally:r.close()
    def test_record_only_and_observation_feedback_never_add_fact_recall(self):
        with tempfile.TemporaryDirectory() as folder:
            r=Runtime(Path(folder))
            try:
                e=r.store.event(r.session,'Projekt Atlas Budget 120 Euro.')
                r.memory.feedback(e['event_id'],'alignment','observe','learn')
                self.assertEqual(r.memory.recall('Projekt Atlas Budget 120 Euro.',r.session),[])
                with self.assertRaises(ValueError):r.learner.shadow_student()
                with self.assertRaises(ValueError):r.memory.feedback(e['event_id'],'alignment','true','learn')
                self.assertEqual(r.store.rows('SELECT * FROM updates'),[])
            finally:r.close()
    def test_preempted_collection_aborts_without_activation(self):
        with tempfile.TemporaryDirectory() as folder:
            r=Runtime(Path(folder))
            try:
                for i in range(64):
                    e=r.store.event(r.session,'Budget '+str(i));r.memory.feedback(e['event_id'],'alignment','observe','learn')
                r.cfg['learning_mode']='SHADOW_UPDATE';r.cancel_event.set();before=r.store.generation_id
                with patch.object(r.guard,'update',return_value='NORMAL'):
                    with self.assertRaises(Cancelled):r.learner.shadow_student()
                self.assertEqual(r.store.one('SELECT status FROM updates')['status'],'ABORTED')
                self.assertEqual(before,r.store.generation_id);self.assertIsNone(r.learner.proc)
            finally:r.close()

if __name__=='__main__':unittest.main()
