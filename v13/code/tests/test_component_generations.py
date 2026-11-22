"""Atomic multi-component generations, legacy compatibility and rollback ordering."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.common import atomic_write,dumps,file_hash,now,uid
from v13.config import initialize
from v13.store import Store

class Generations(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.cfg=initialize(self.home);self.s=Store(self.home)
        self.models={'C2_CONTROL':'encoder','B1_DETAIL':'body','B2_GIST':'body'}
        self.s.ensure_generation_snapshot(self.cfg,self.models)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def candidate(self,kind,base=None,**extra):
        u=uid('upd');path='checkpoints/'+('head' if kind=='route' else kind)+'-'+u+'.npz';atomic_write(self.home/path,u)
        manifest={'commit_eligible':True,'component':kind,'encoder_revision':'encoder'}|extra
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(u,base or self.s.generation_id,'PENDING_APPROVAL',path,file_hash(self.home/path),dumps(manifest),now()))
        return u,path
    def test_independent_updates_restart_and_reverse_rollback_preserve_rules(self):
        route,p=self.candidate('route');self.s.switch_generation(route,self.cfg,self.models)
        wake,q=self.candidate('wake');self.s.switch_generation(wake,self.cfg,self.models)
        route2,p2=self.candidate('route');self.s.switch_generation(route2,self.cfg,self.models)
        self.assertEqual(set(self.s.generation()['hashes']),{p2,q})
        self.s.close();self.s=Store(self.home)
        with self.assertRaises(ValueError):self.s.rollback(wake)
        rid=self.s.request('RULES',{'base_rule':self.s.generation()['rule_version'],'after':['kurz']});self.s.approve_rule(rid,self.cfg,self.models)
        self.s.rollback(route2);self.assertEqual(set(self.s.generation()['hashes']),{p,q})
        self.s.rollback(wake);self.assertEqual(set(self.s.generation()['hashes']),{p})
        self.s.rollback(route);self.assertEqual(self.s.generation()['hashes'],{})
        self.assertEqual(self.s.rules(),['kurz']);self.assertEqual(self.s.integrity(True),[])
    def test_stale_and_mismatched_dependency_cannot_replace_other_component(self):
        route,p=self.candidate('route');wake,q=self.candidate('wake')
        self.s.switch_generation(route,self.cfg,self.models);before=self.s.generation_id
        with self.assertRaises(ValueError):self.s.switch_generation(wake,self.cfg,self.models)
        halt,_=self.candidate('halt',dependency_revisions={'B1_DETAIL':'different'})
        with self.assertRaises(ValueError):self.s.switch_generation(halt,self.cfg,self.models)
        self.assertEqual(self.s.generation_id,before);self.assertEqual(set(self.s.generation()['hashes']),{p})
    def test_legacy_manifest_view_is_not_mutated(self):
        u,p=self.candidate('route');legacy={'hashes':{p:file_hash(self.home/p)},'models':self.models}
        self.assertEqual(self.s.components(legacy)['route']['update_id'],u)
        self.assertNotIn('components',legacy)
    def test_component_cannot_claim_another_components_path(self):
        u,p=self.candidate('wake');before=self.s.generation_id
        with self.s.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps({'component':'halt','commit_eligible':True}),u))
        with self.assertRaises(ValueError):self.s.switch_generation(u,self.cfg,self.models)
        self.assertEqual(self.s.generation_id,before)
    def test_five_components_survive_restart_predictor_replacement_and_rollback(self):
        artifacts={};updates=[]
        for component in ('route','wake','halt','b1_predictor','b2_predictor'):
            extra={'encoder_revision':'body'} if component.endswith('_predictor') else {}
            u,p=self.candidate(component,**extra);self.s.switch_generation(u,self.cfg,self.models)
            artifacts[component]=p;updates.append(u)
        self.s.close();self.s=Store(self.home)
        self.assertEqual(set(self.s.components()),set(artifacts))
        self.assertEqual(self.s.components()['b1_predictor']['encoder_role'],'B1_DETAIL')
        self.assertEqual(self.s.components()['b2_predictor']['encoder_role'],'B2_GIST')
        u,p=self.candidate('b1_predictor',encoder_revision='body');self.s.switch_generation(u,self.cfg,self.models)
        self.assertEqual(set(self.s.generation()['hashes']),set(artifacts.values())-{artifacts['b1_predictor']}|{p})
        self.s.rollback(u);self.assertEqual(set(self.s.generation()['hashes']),set(artifacts.values()))
        for u in reversed(updates):self.s.rollback(u)
        self.assertEqual(self.s.generation()['hashes'],{});self.assertEqual(self.s.integrity(True),[])
    def test_body_predictor_rejects_control_encoder_revision(self):
        u,p=self.candidate('b1_predictor');before=self.s.generation_id
        with self.assertRaises(ValueError):self.s.switch_generation(u,self.cfg,self.models)
        self.assertEqual(self.s.generation_id,before);self.assertEqual(self.s.generation()['hashes'],{})
    def test_calibration_preserves_all_seven_existing_components_and_ordered_rollback(self):
        updates=[];paths=[]
        for component in ('route','wake','halt','b1_predictor','b2_predictor','a3_student','world_predictor','control_calibration','memory_retrieval'):
            extra={'encoder_revision':'body'} if component in ('b1_predictor','b2_predictor') else {}
            u,path=self.candidate(component,**extra);self.s.switch_generation(u,self.cfg,self.models);updates.append(u);paths.append(path)
        self.assertEqual(len(self.s.components()),9);self.assertEqual(set(self.s.generation()['hashes']),set(paths))
        self.s.close();self.s=Store(self.home);self.assertEqual(self.s.components()['control_calibration']['encoder_role'],'C2_CONTROL')
        self.s.rollback(updates[-1]);self.assertEqual(set(self.s.generation()['hashes']),set(paths[:-1]))
        for u in reversed(updates[:-1]):self.s.rollback(u)
        self.assertEqual(self.s.generation()['hashes'],{});self.assertEqual(self.s.integrity(True),[])

if __name__=='__main__':unittest.main()
