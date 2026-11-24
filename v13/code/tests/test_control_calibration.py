"""Numerical calibration/refusal fixtures; no native quality claims."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from v13.control_calibration_worker import observation,features,loss_gradient,gradient_check,train,infer
from v13.config import DEFAULTS
from v13.runtime import Runtime
from v13.store import telemetry_metrics

def control(route='both',confidence=1.):return {'success':True,'confidence':confidence,'validation':{'negation':False,'ungrounded':[]},'function_calls':[{'name':'select_processing','arguments':{'route':route}}]}
def dataset():
    return {'config':DEFAULTS,'observations':[{'route':'both','raw_confidence':1.} for _ in range(128)],'correct_labels':[int(i%4==3) for i in range(128)],'source_groups':[hashlib.sha256(str(i).encode()).hexdigest() for i in range(128)]}

class CalibrationMath(unittest.TestCase):
    def test_observations_require_valid_native_route_and_preserve_first_proposal(self):
        self.assertEqual(observation(control())['route'],'both')
        for bad in (control(confidence=float('nan')),control(confidence=True),control(route='SHELL'),control()|{'success':False},control()|{'validation':{'negation':True}},control()|{'function_calls':[None]}):
            with self.assertRaises(ValueError):observation(bad)
        c=control();c['function_calls'].extend(control('detail')['function_calls'])
        self.assertEqual(observation(c)['route'],'both');self.assertTrue(observation(c)['ambiguous']);self.assertEqual(observation(c)['proposal_count'],2)
    def test_gradient_has_finite_difference_evidence(self):
        x=features(dataset()['observations'][:8]);y=np.array(dataset()['correct_labels'][:8]);w=np.arange(6)*.1
        self.assertLess(gradient_check(x,y,w),1e-6)
        self.assertTrue(np.isfinite(loss_gradient(x,y,w)[0]))
    def test_source_partitions_calibration_support_and_active_retention(self):
        with tempfile.TemporaryDirectory() as td:
            req=dataset();m=train(req,td);self.assertTrue(m['commit_eligible']);self.assertLess(m['after']['brier'],m['native_baseline']['brier'])
            parts=[set(v) for v in m['partition'].values()];self.assertTrue(all(not a&b for i,a in enumerate(parts) for b in parts[i+1:]));self.assertEqual(set.union(*parts),set(range(128)))
            path=Path(td)/'candidate.npz';p=infer(control(),path);self.assertLess(p['calibrated_confidence'],.6)
            self.assertIsNone(infer(control('detail'),path)['calibrated_confidence']);self.assertIsNone(infer(control(confidence=.3),path)['calibrated_confidence'])
            active=Path(td)/'active.npz';active.write_bytes(path.read_bytes());req['active_checkpoint']=str(active);after=train(req,td)
            self.assertTrue(after['retention_pass']);self.assertTrue(after['checkpoint_reload'])
    def test_duplicate_or_one_class_holdout_cannot_train(self):
        with tempfile.TemporaryDirectory() as td:
            req=dataset();req['source_groups'][1]=req['source_groups'][0]
            with self.assertRaises(ValueError):train(req,td)
            req=dataset();req['correct_labels']=[1]*128
            with self.assertRaises(ValueError):train(req,td)
            self.assertFalse((Path(td)/'candidate.npz').exists())
    def test_changed_corpus_cannot_drop_old_cases_or_regress_a_route(self):
        with tempfile.TemporaryDirectory() as td:
            req=dataset();first=train(req,td);path=Path(td)/'candidate.npz';active=Path(td)/'active.npz';active.write_bytes(path.read_bytes())
            req['active_checkpoint']=str(active);req['source_groups']=[hashlib.sha256(('new '+str(i)).encode()).hexdigest() for i in range(128)]
            req['correct_labels']=[int(i%4!=3) for i in range(128)]
            second=train(req,td);self.assertEqual(second['retained_test']['n'],len(first['partition']['test']))
            self.assertFalse(second['retained_test']['pass']);self.assertFalse(second['commit_eligible'])
            self.assertFalse(second['retained_test']['per_route']['both']['pass'])
            with np.load(active,allow_pickle=False) as old,np.load(path,allow_pickle=False) as new:
                self.assertTrue(set(old['retention_ids'])<=set(new['retention_ids']))
                self.assertGreater(len(new['retention_ids']),len(old['retention_ids']))
            self.assertTrue(second['retained_support_preserved'])
    def test_legacy_inference_remains_usable_but_missing_old_targets_refuse_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'legacy.npz';np.savez(path,weights=np.zeros(6),temperature=1.,confidence_ranges=np.array([[0.,0.],[0.,0.],[0.,0.],[1.,1.]]),route_counts=np.array([0,0,0,10]),format=np.asarray('native-route-calibration-v1'))
            self.assertTrue(infer(control(),path)['in_support'])
            with self.assertRaisesRegex(ValueError,'fixed old-case retention'):train(dataset()|{'active_checkpoint':str(path)},td)
            self.assertFalse((Path(td)/'candidate.npz').exists())
    def test_calibration_telemetry_retains_probability_but_no_control_reasoning(self):
        v=telemetry_metrics({'component':'control_calibration','prediction':{'calibrated_confidence':.3,'calibration_scope':'HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY','raw_confidence':1.},'native_control':{'reasoning':'private native output'}})
        self.assertEqual(v['prediction']['calibrated_confidence'],.3);self.assertNotIn('native_control',v)

class CalibrationAdmission(unittest.TestCase):
    def test_shadow_observation_budget_is_distinct_bounded_and_saved_on_failure(self):
        from unittest.mock import patch
        from v13.common import Limits
        from v13.config import save_config,validate
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td));deadlines=[]
            try:
                for i in range(32):
                    e=r.store.event(r.session,'Observation budget source '+str(i));r.memory.feedback(e['event_id'],'route','both','learn')
                r.cfg.update(learning_mode='SHADOW_UPDATE',calibration_observation_seconds=17.)
                save_config(r.home,r.cfg);self.assertEqual(r.cfg['control_seconds'],4.)
                for invalid in (.19,30.01,True):
                    with self.assertRaises(ValueError):validate(r.cfg|{'calibration_observation_seconds':invalid})
                def actual_attempt(text,cancel,deadline):
                    import time
                    deadlines.append(deadline-time.monotonic())
                    r.needle.last_metrics={'status':'DEADLINE','operation':'CONTROL','duration_s':.125}
                    raise Limits('unit isolated native deadline')
                base=r.store.generation_id
                with patch.object(r.needle,'control',side_effect=actual_attempt):
                    with self.assertRaises(Limits):r.learner.shadow_control_calibration()
                self.assertEqual(len(deadlines),1);self.assertGreater(deadlines[0],16.9);self.assertLessEqual(deadlines[0],17.)
                u=r.store.one('SELECT * FROM updates');m=json.loads(u['manifest'])
                self.assertEqual(u['status'],'ABORTED');self.assertEqual(m['job_budget_seconds'],600)
                self.assertEqual(m['observation_budget_seconds'],17.);self.assertEqual(r.store.generation_id,base)
                self.assertEqual(m['native_observations'],[]);a=m['native_attempts'][0]
                self.assertEqual(a['error_type'],'Limits');self.assertEqual(a['status'],'FAILED')
                self.assertEqual(a['native_metrics']['status'],'DEADLINE');self.assertIn(a['source_id'],m['source_ids'])
                first=json.loads(r.store.one('SELECT packet FROM events WHERE id=?',(a['event_id'],))['packet'])
                self.assertEqual(r.store.read_source(first['source_ref']),'Observation budget source 0')
                self.assertFalse(list((r.home/'checkpoints').glob('control_calibration-*.npz')))
                r.close();r=Runtime(Path(td));self.assertEqual(r.cfg['calibration_observation_seconds'],17.)
            finally:r.close()
    def test_consumer_timeout_abstains_without_manufacturing_native_prediction(self):
        from tests.integration_control_calibration import consumer_policy
        text='Hallo Gast 1.'
        info={'source':'BOOT_SCAFFOLD','control_unavailable':'Zeitbudget erreicht','native_control_metrics':{'status':'DEADLINE'}}
        p=consumer_policy(text,'simple',info,None)
        self.assertTrue(p['policy_ok']);self.assertIsNone(p['native_proposal']);self.assertFalse(p['native_available'])
        self.assertFalse(consumer_policy(text,'both',info,None)['policy_ok'])
        self.assertFalse(consumer_policy(text,'simple',info,{'in_support':True,'calibrated_confidence':1.})['policy_ok'])
        self.assertFalse(consumer_policy(text,'simple',{'source':'BOOT_SCAFFOLD'},None)['policy_ok'])
    def test_configurable_source_bound_survives_restart_and_latest_record_revokes(self):
        from v13.config import save_config,validate
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                for i in range(270):
                    e=r.store.event(r.session,'Calibration source '+str(i));r.memory.feedback(e['event_id'],'route','both','learn')
                self.assertEqual(len(r.learner.control_labels()),256)
                r.cfg['calibration_sources']=40;save_config(r.home,r.cfg)
                last=r.learner.control_labels()[-1][1]
                r.memory.feedback(last['event_id'],'route','both','record')
                labels=r.learner.control_labels();self.assertEqual(len(labels),40)
                self.assertNotIn(last['source_ref']['sha256'],[e['source_ref']['sha256'] for _,e in labels])
                r.close();r=Runtime(Path(td));self.assertEqual(r.cfg['calibration_sources'],40)
                self.assertEqual(len(r.learner.control_labels()),40)
                for invalid in (31,513,True):
                    with self.assertRaises(ValueError):validate(r.cfg|{'calibration_sources':invalid})
                self.assertEqual(r.store.rows('SELECT * FROM updates'),[])
            finally:r.close()
    def test_record_mode_refuses_and_latest_record_permission_revokes_source(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                with self.assertRaises(ValueError):r.learner.shadow_control_calibration()
                for i in range(32):
                    e=r.store.event(r.session,'Quelldatum '+str(i));r.memory.feedback(e['event_id'],'route','both','learn');r.memory.feedback(e['event_id'],'route','both','record')
                r.cfg['learning_mode']='SHADOW_UPDATE'
                with self.assertRaises(ValueError):r.learner.shadow_control_calibration()
                self.assertEqual(r.store.rows('SELECT * FROM updates'),[])
            finally:r.close()
    def test_preempted_collection_is_aborted_with_no_generation_change(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                for i in range(32):
                    e=r.store.event(r.session,'Quelle '+str(i));r.memory.feedback(e['event_id'],'route','both','learn')
                r.cfg['learning_mode']='SHADOW_UPDATE';base=r.store.generation_id;r.cancel_event.set()
                from v13.common import Cancelled
                with self.assertRaises(Cancelled):r.learner.shadow_control_calibration()
                u=r.store.one('SELECT * FROM updates');self.assertEqual(u['status'],'ABORTED');self.assertEqual(r.store.generation_id,base);self.assertEqual(json.loads(u['manifest'])['native_observations'],[])
            finally:r.close()
