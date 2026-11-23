"""Numerical World math/refusal fixtures; no hardware or semantic claims."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from v13.config import initialize
from v13.runtime import Runtime
from v13.common import digest
from v13.store import telemetry_metrics
from v13.world_worker import action_features,normalized,optimize,train,DIM,gradient_check,loss_gradient,coverage,support,predict

class WorldMath(unittest.TestCase):
    def test_source_and_action_support_refuses_novelty_duplicates_and_legacy_artifacts(self):
        state=np.zeros((6,DIM));state[:,0]=np.sqrt(DIM);roles=['SOURCE_COPY']*3+['C3_LANGUAGE']*3
        u,ri,floor,count=coverage(state,roles,['a','b','c']*2)
        self.assertTrue(support(u[0],'C3_LANGUAGE',u,ri,floor,count)['in_support'])
        self.assertFalse(support(u[0],'B1_DETAIL',u,ri,floor,count)['in_support'])
        novel=np.zeros(DIM);novel[1]=1
        self.assertFalse(support(novel,'C3_LANGUAGE',u,ri,floor,count)['in_support'])
        dup=coverage(state,roles,['a']*6);self.assertFalse(support(u[0],'SOURCE_COPY',*dup)['in_support'])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.npz';p=np.zeros((DIM+4,16));q=np.eye(16)
            np.savez(path,projector=p,predictor=q)
            with self.assertRaises(ValueError):predict(state[0],'C3_LANGUAGE',path)
            np.savez(path,projector=p,predictor=q,support_states=u,support_roles=ri,support_floors=floor,action_source_counts=count,residual_spread=np.ones((4,16)))
            self.assertEqual(len(predict(state[0],'C3_LANGUAGE',path)['future_latent_prediction']),16)
            self.assertIsNone(predict(novel,'C3_LANGUAGE',path)['future_latent_prediction'])
            self.assertIsNone(predict(state[0],'B1_DETAIL',path)['future_latent_prediction'])
    def test_world_telemetry_retains_gate_measurements_without_content(self):
        clean=telemetry_metrics({'component':'world_predictor','objective':'world-digital-action-latent-v1','role':'SOURCE_COPY',
            'metrics':{'action_ablation_pass':True,'fixed_target_retention_mse':.01,'state_geometry_loss':.002},'digital_latent_error':.03,
            'input':'secret raw source','future_latent_prediction':[99.]*16})
        self.assertEqual(clean['component'],'world_predictor');self.assertEqual(clean['role'],'SOURCE_COPY')
        self.assertEqual(clean['metrics']['fixed_target_retention_mse'],.01);self.assertEqual(clean['digital_latent_error'],.03)
        self.assertNotIn('input',clean);self.assertNotIn('future_latent_prediction',clean)
    def test_measured_geometry_penalty_has_correct_nonzero_gradient(self):
        rng=np.random.default_rng(9);x=action_features(normalized(rng.normal(size=(8,DIM))),['SOURCE_COPY','C3_LANGUAGE']*4)
        y=normalized(rng.normal(size=(8,DIM)));anchor=rng.normal(size=(DIM+4,16))*.01;p=anchor+rng.normal(size=anchor.shape)*.003;q=np.eye(16);target=anchor[:DIM].copy()
        self.assertGreater(loss_gradient(x,y,p,q,target,anchor)[3]['state_geometry_loss'],0)
        self.assertLess(gradient_check(x,y,p,q,target,anchor),1e-5)
        before=anchor.copy();optimize(x,y,p,q,target,anchor,{'predictor_steps':3,'predictor_lr':.002,'max_update_norm':.02,'ema_decay':.99})
        np.testing.assert_array_equal(anchor,before)
    def test_actual_role_features_and_target_ema_map_only_state_rows(self):
        rng=np.random.default_rng(2);state=normalized(rng.normal(size=(8,DIM)));x=action_features(state,['SOURCE_COPY','C3_LANGUAGE']*4);y=normalized(rng.normal(size=(8,DIM)))
        p=rng.normal(size=(DIM+4,16))*.01;q=np.eye(16);target=p[:DIM].copy();anchor=p.copy()
        self.assertLess(gradient_check(x,y,p,q,target,anchor),1e-5)
        cfg={'predictor_steps':1,'predictor_lr':.002,'max_update_norm':.02,'ema_decay':.99};a,b,t,h=optimize(x,y,p,q,target,anchor,cfg)
        np.testing.assert_allclose(t,.99*target+.01*a[:DIM],rtol=0,atol=1e-15);np.testing.assert_array_equal(target,p[:DIM])
        self.assertEqual(x.shape,(8,DIM+4));np.testing.assert_array_equal(x[:,:DIM],state)
        self.assertLessEqual(h['max_applied_step_norm'],.02+1e-12)
    def test_degenerate_targets_cannot_pass_or_mix_source_action_splits(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);cfg=initialize(out)|{'predictor_steps':1};groups=[hashlib.sha256(str(i//2).encode()).hexdigest() for i in range(96)];state=np.ones((96,DIM))
            m=train({'config':cfg,'source_groups':groups,'action_roles':['SOURCE_COPY','C3_LANGUAGE']*48,'state_embeddings':state.tolist(),'outcome_embeddings':state.tolist()},out)
            self.assertFalse(m['noncollapse_pass']);self.assertFalse(m['commit_eligible']);self.assertTrue(set(m['train_source_groups']).isdisjoint(m['held_out_source_groups']))
    def test_unknown_roles_and_zero_measurements_are_refused(self):
        with self.assertRaises(ValueError):action_features(np.ones((1,DIM)),['SHELL'])
        with self.assertRaises(ValueError):normalized(np.zeros((1,DIM)))

class WorldBinding(unittest.TestCase):
    def test_world_feedback_requires_completed_action_and_never_retrieves_as_fact(self):
        with tempfile.TemporaryDirectory() as folder:
            r=Runtime(Path(folder))
            try:
                e=r.store.event(r.session,'Projekt Atlas Budget 120 Euro.')
                with self.assertRaises(ValueError):r.memory.feedback(e['event_id'],'world','observe','learn')
                f=r.world.forecast(e,'SOURCE_COPY');aid=r.store.start_action(e['event_id'],e['brain_generation_id'],forecast=f)
                mid=r.store.message(r.session,e['event_id'],'assistant');r.store.append_message(mid,'120 Euro.');r.store.finish_message(mid,'FINAL',{})
                r.store.finish_action(aid,'FINAL',{'role':'SOURCE_COPY','self_candidate_hash':digest('120 Euro.'),'action_duration_s':.01})
                r.memory.feedback(e['event_id'],'world','observe','learn');p=r.world.transition(aid)
                self.assertEqual(r.store.read_source(p['outcome_source_ref']),'120 Euro.');self.assertFalse(p['teacher_truth_authority'])
                count=r.store.one('SELECT COUNT(*) AS n FROM sources')['n']
                self.assertEqual(r.world.transition(aid)['packet_id'],p['packet_id']);self.assertEqual(r.store.one('SELECT COUNT(*) AS n FROM sources')['n'],count)
                observation=r.world.observe(aid);self.assertEqual(r.world.observe(aid),observation)
                self.assertEqual(r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='PredictionOutcome' AND event_id=?",(e['event_id'],))['n'],1)
                self.assertEqual(r.memory.recall('Projekt Atlas Budget 120 Euro.',r.session),[])
                with self.assertRaises(ValueError):r.learner.shadow_world()
                for kind,field,replacement in (('ActionIntent','permission','external'),('CorollaryCopy','action_id','unrelated')):
                    row=r.store.one('SELECT id,payload FROM packets WHERE kind=? AND event_id=?',(kind,e['event_id']));bad=json.loads(row['payload']);bad[field]=replacement
                    with r.store.tx() as c:c.execute('UPDATE packets SET payload=? WHERE id=?',(json.dumps(bad),row['id']))
                    with self.assertRaises(ValueError):r.world.transition(aid)
                    with r.store.tx() as c:c.execute('UPDATE packets SET payload=? WHERE id=?',(row['payload'],row['id']))
                # A changed persisted outcome cannot borrow the committed text.
                with r.store.tx() as c:c.execute("UPDATE actions SET outcome=? WHERE id=?",('{"role":"SOURCE_COPY","self_candidate_hash":"wrong"}',aid))
                with self.assertRaises(ValueError):r.world.transition(aid)
            finally:r.close()

if __name__=='__main__':unittest.main()
