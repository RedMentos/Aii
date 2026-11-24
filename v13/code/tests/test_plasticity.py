"""F7 control/restart fixtures; these assert no native training quality."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.common import dumps,file_hash,uid,now
from v13.runtime import Runtime
from v13.operator import Operator
from v13.plasticity import REVISION
from v13.store import telemetry_metrics

class PlasticityChecks(unittest.TestCase):
    def trial(self,r,component='route',retained=True,eligible=True,status=None,observe=True):
        id_=uid('upd');p=r.home/'checkpoints'/((('head-' if component=='route' else component+'-')+id_)+'.fixture');p.write_bytes(b'Unit fixture only; not a model quality proof')
        manifest={'component':component,'base_generation':r.store.generation_id,'metrics':{'retention_pass':retained,'commit_eligible':eligible,'max_applied_step_norm':.0199}}
        cfg=r.cfg|{'learning_mode':'SHADOW_UPDATE'}
        r.learner.plasticity.budget(component,cfg,id_,manifest)
        manifest['metrics'].update(effective_learning_rate=manifest['training_policy']['effective_learning_rate'],effective_max_update_norm=manifest['training_policy']['effective_max_update_norm'])
        with r.store.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(id_,r.store.generation_id,status or ('PENDING_APPROVAL' if eligible else 'EVALUATED_FAIL'),str(p.relative_to(r.home)),file_hash(p),dumps(manifest),now()))
        if observe:r.learner.plasticity.observe(id_)
        return id_,manifest,p
    def test_measured_gain_is_bounded_component_specific_and_used_without_config_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                base=r.store.generation_id;cfg=dict(r.cfg)
                for _ in range(8):self.trial(r,retained=False,eligible=False)
                state,_=r.learner.plasticity.state('route');self.assertEqual(state['retention_failures'],8)
                self.assertTrue(.5<state['plasticity_gain']<1.)
                m={'base_generation':base};effective=r.learner.plasticity.budget('route',r.cfg|{'learning_mode':'SHADOW_UPDATE'},uid('upd'),m)
                self.assertLess(effective['learning_rate'],cfg['learning_rate']);self.assertLess(effective['max_update_norm'],cfg['max_update_norm'])
                self.assertEqual(r.cfg,cfg);self.assertEqual(r.store.generation_id,base)
                self.assertEqual(r.learner.plasticity.state('wake')[0]['plasticity_gain'],1.)
                self.assertIsNone(state['native_shared_attention_drift']);self.assertIsNone(state['native_router_input_drift'])
                self.assertFalse(state['consolidation_ready'])
                self.assertFalse(m['training_policy']['native_parameter_authority'])
            finally:r.close()
    def test_restart_reconciles_unobserved_trial_once_and_abort_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                id_,_,_=self.trial(r,observe=False);self.trial(r,status='ABORTED',observe=False)
                r.close();r=Runtime(Path(td))
                report=json.loads(Operator(r).run(':plasticity route'));self.assertEqual(report['components']['route']['trials'],1)
                self.assertFalse(r.learner.plasticity.observe(id_));r.learner.plasticity.reconcile()
                self.assertEqual(r.learner.plasticity.state('route')[0]['trials'],1)
                self.assertEqual(len(r.store.rows("SELECT * FROM packets WHERE kind='PlasticityState'")),1)
                with self.assertRaises(ValueError):r.learner.plasticity.budget('route',r.cfg,uid('upd'),{'base_generation':r.store.generation_id})
            finally:r.close()
    def test_atomic_state_and_packet_publication_repairs_failed_crash_window(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                id_,_,_=self.trial(r,observe=False)
                r.store.db.execute("CREATE TRIGGER fixture_crash BEFORE INSERT ON packets WHEN NEW.kind='PlasticityState' BEGIN SELECT RAISE(ABORT,'simulated publication crash'); END")
                with self.assertRaises(Exception):r.learner.plasticity.observe(id_)
                self.assertEqual(r.learner.plasticity.state('route')[0]['trials'],0)
                r.store.db.execute('DROP TRIGGER fixture_crash');r.learner.plasticity.reconcile()
                self.assertEqual(r.learner.plasticity.state('route')[0]['trials'],1)
            finally:r.close()
    def test_corrupt_or_uninstrumented_trial_cannot_move_state(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                id_,m,p=self.trial(r,observe=False);p.write_bytes(b'corrupt')
                self.assertFalse(r.learner.plasticity.observe(id_));self.assertEqual(r.learner.plasticity.state('route')[0]['trials'],0)
                m.pop('training_policy')
                with r.store.tx() as c:c.execute('UPDATE updates SET manifest=?,hash=? WHERE id=?',(dumps(m),file_hash(p),id_))
                self.assertFalse(r.learner.plasticity.observe(id_));self.assertEqual(r.learner.plasticity.state('route')[0]['trials'],0)
            finally:r.close()
    def test_slow_reopening_and_stability_tag_cannot_grant_consolidation_authority(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                for _ in range(16):self.trial(r)
                stable,_=r.learner.plasticity.state('route');self.assertTrue(stable['consolidation_ready'])
                self.trial(r,eligible=False);reopened,_=r.learner.plasticity.state('route')
                self.assertGreater(reopened['plasticity_gain'],stable['plasticity_gain'])
                self.assertFalse(reopened['consolidation_ready']);self.assertEqual(r.store.components(),{})
                self.assertFalse(json.loads(Operator(r).run(':plasticity'))['shared_native_interference_measured'])
            finally:r.close()
    def test_private_input_is_not_in_monitor_telemetry(self):
        measured=telemetry_metrics({'component':'route','plasticity_gain':.9,'stability_score':.6,'trials':3,'saturation':.95,'consolidation_ready':False,'query':'private input'})
        self.assertEqual(measured['plasticity_gain'],.9);self.assertEqual(measured['trials'],3);self.assertNotIn('query',measured)
    def test_component_budget_binding_and_malformed_policy_cannot_poison_other_components(self):
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                id_,m,_=self.trial(r,observe=False);original=dumps(m)
                m['component']='wake'
                with r.store.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(m),id_))
                self.assertFalse(r.learner.plasticity.observe(id_));self.assertEqual(r.learner.plasticity.state('wake')[0]['trials'],0)
                m=json.loads(original);m['training_policy']={'revision':REVISION}
                with r.store.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(m),id_))
                report=r.learner.plasticity.report('halt');self.assertEqual(report['components']['halt']['trials'],0)
                with r.store.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(original,id_))
                self.assertTrue(r.learner.plasticity.observe(id_))
            finally:r.close()
