"""WP-AG6 live trainer choice (agi/trainers.py). No torch/model needed: requirements are faked."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from v13.runtime import Runtime
from v13.common import Unavailable
from v13.agi import hub,job,operator_command
from v13.agi import trainers as tr
from v13.agi.weights import NullTrainer

class FakeModels:
    def __init__(self,path):self.p=path
    def path_for(self,role):
        if self.p is None:raise Unavailable('x')
        return self.p
    def revision(self,role):return 'r'

class Trainers(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.g=hub(self.r)
        self.master=self.home/'master';self.master.mkdir();(self.master/'model.safetensors').write_bytes(b'w');(self.master/'config.json').write_text('{}')
        self.gguf=self.home/'c3.gguf';self.gguf.write_bytes(b'GGUF');(self.home/'bin').mkdir(exist_ok=True);(self.home/'bin/llama-server').write_bytes(b'')
        p=mock.patch.object(tr,'arch_match',return_value=True);p.start();self.addCleanup(p.stop)  # fake GGUF bytes
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_probes_spec_is_disjoint_from_ag12_holdout(self):
        anchors,probes=tr.probes();self.assertGreaterEqual(len(anchors),16);self.assertTrue(all(p.get('expect') for p in probes))
        self.assertTrue(self.g.eval.guard_training(anchors+[p['prompt'] for p in probes]))
    def test_auto_without_master_is_null_trainer(self):
        self.r.models=FakeModels(None);t,info=tr.build(self.r)
        self.assertIsInstance(t,NullTrainer);self.assertEqual((info['choice'],info['active']),('auto','none'))
    def test_choice_pins_master_hash_and_builds_lora_with_live_near_miss(self):
        self.r.models=FakeModels(self.gguf)
        with mock.patch.object(tr,'_torch',return_value=True):
            info=tr.choose(self.g,self.r,'auto',str(self.master))
            self.assertEqual(info['active'],'lora');self.assertTrue(info['served_live'])
            t=self.g.weights.trainer;self.assertEqual(t.method,'lora-torch-cpu');self.assertEqual(t.role,'C3_LANGUAGE')
            self.assertEqual(t.master_sha,tr._box(self.r.store).load()[0]['master_sha256'])
            self.assertEqual(t.cfg['base_gguf'],str(self.gguf))
            calls={}
            class Inner:
                def evaluate(s,items,probes,cancel=None,deadline=None,near_miss=None):
                    calls['near']=near_miss
                    return {'base_eval':{'overall':1.},'candidate_eval':{'overall':1.},'near_miss_leak':.5,
                            'rows':{'near_miss':[{'base':0,'candidate':1},{'base':0,'candidate':0}]}}
                def close(s):calls['closed']=True
            ev=tr.LiveNearMissEvaluator(Inner());rep=ev.evaluate([{'prompt':'What is the name of my cat?','target':'Your cat is called Mitzi.'}],[]);ev.close()
            self.assertEqual((rep['base_eval']['near_miss_leak'],rep['candidate_eval']['near_miss_leak']),(0.,.5))  # gate sees specificity
            self.assertTrue(calls['near']);self.assertEqual(calls['near'][0][1],['mitzi']);self.assertTrue(calls['closed'])
            info=tr.choose(self.g,self.r,'sparse');self.assertEqual(info['active'],'sparse');self.assertFalse(info['served_live'])
            info=tr.choose(self.g,self.r,'none');self.assertIsInstance(self.g.weights.trainer,NullTrainer)
        with self.assertRaises(ValueError):tr.choose(self.g,self.r,'magic')
        with self.assertRaises(ValueError):tr.choose(self.g,self.r,'lora',str(self.home/'nope'))
    def test_sparse_served_live_only_with_memory_server(self):
        from v13.memory_server import MANIFEST
        from v13.common import file_hash
        self.r.models=FakeModels(self.gguf);b=Path(self.r.home)/'bin/llama-server-mem';b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(b'srv')
        (Path(self.r.home)/MANIFEST).parent.mkdir(parents=True,exist_ok=True);(Path(self.r.home)/MANIFEST).write_text(json.dumps({'binary_sha256':file_hash(b)}))
        with mock.patch.object(tr,'_torch',return_value=True):
            self.assertEqual(tr.choose(self.g,self.r,'auto',str(self.master))['active'],'lora')  # never auto-sparse (fast-trace bench)
            info=tr.choose(self.g,self.r,'sparse');self.assertTrue(info['served_live'])
            t=self.g.weights.trainer;self.assertEqual(t.role,'C3_LANGUAGE#sparse_memory');self.assertIn('Task context',t.cfg['system']);self.assertEqual(t.cfg['contexts'],[''])
            b.write_bytes(b'changed');self.assertFalse(tr.choose(self.g,self.r,'sparse')['served_live'])
    def test_live_evaluator_measures_frozen_drift_probes(self):
        from v13.drift import Drift
        class Inner:
            def evaluate(s,items,probes,cancel=None,deadline=None,near_miss=None):return {'base_eval':{},'candidate_eval':{}}
            def kl(s,prompts):s.n=len(prompts);return .01
        inner=Inner();rep=tr.LiveNearMissEvaluator(inner,drift=Drift(self.r.store,self.r.cfg)).evaluate([],[])
        d=rep['wp_s5_drift'];self.assertEqual((d['measure'],d['component'],d['n'],d['passed']),('LM_KL','C3_LANGUAGE',inner.n,True))
        self.assertGreaterEqual(inner.n,20)
    def test_master_must_match_deployed_body(self):
        self.r.models=FakeModels(self.gguf)
        with mock.patch.object(tr,'_torch',return_value=True),mock.patch.object(tr,'arch_match',return_value=False):
            info=tr.choose(self.g,self.r,'lora',str(self.master))
        self.assertEqual(info['active'],'none');self.assertIn('master_ok',info['missing']);self.assertFalse(info['requirements']['arch_match'])
    def test_missing_piece_falls_back_honestly(self):
        self.r.models=FakeModels(self.gguf)
        with mock.patch.object(tr,'_torch',return_value=False):
            info=tr.choose(self.g,self.r,'lora',str(self.master))
        self.assertEqual(info['active'],'none');self.assertEqual(info['missing'],['torch'])
    def test_consolidate_job_trains_and_gates_with_installed_trainer(self):
        class FakeTrainer:
            method='fake';role='C3_LANGUAGE'
            def fit(self,items,base_generation,cancel=None,deadline=None):
                return {'artifact':'/x.gguf','hash':'h','method':'fake','metrics':{'kl_to_base':.01},
                        'eval':{'base_eval':{'overall':.8,'unseen':.75},'candidate_eval':{'overall':.8,'unseen':.75,'forgetting':{'rate':0.}},'learned_recall':1.}}
        with mock.patch.object(tr,'build',return_value=(FakeTrainer(),{'choice':'auto','active':'fake'})), \
             mock.patch.object(self.g.weights,'stage',return_value={'batch_id':'b1','status':'STAGED'}), \
             mock.patch.object(self.g.weights,'train_and_gate',return_value={'status':'PENDING_USER'}) as tg:
            e={'action':'growth_consolidate','origin':'USER','payload':{}}
            out=job(self.r.sleep,e)
        self.assertEqual((out['trainer'],out['trained']),('fake','PENDING_USER'));tg.assert_called_once()
        self.assertIsInstance(self.g.weights.trainer,FakeTrainer)
    def test_live_lora_defaults_and_measured_overrides(self):
        self.r.models=FakeModels(self.gguf)
        with mock.patch.object(tr,'_torch',return_value=True):
            tr.choose(self.g,self.r,'lora',str(self.master));t=self.g.weights.trainer
            self.assertEqual((t.cfg['lr'],t.cfg['anchor_weight'],t.cfg['anchors_per_step'],tuple(t.cfg['targets'])),(3e-4,8.,16,('w1','w2','w3')))  # measured live values, not bench lr 1e-3
            out=operator_command(self.r,['trainer','cfg','anchor_weight=6','lr=2e-4','targets=["w1","w3"]'])
            t=self.g.weights.trainer;self.assertEqual((t.cfg['anchor_weight'],t.cfg['lr'],t.cfg['targets']),(6,2e-4,['w1','w3']))
            self.assertIn('"anchor_weight":6,',out.replace(' ',''));self.assertEqual(t.cfg['anchors_per_step'],16)
            with self.assertRaises(ValueError):tr.set_lora_cfg(self.g,self.r,{'threads':99})
            with self.assertRaises(ValueError):tr.set_lora_cfg(self.g,self.r,{'nonsense':1})
            operator_command(self.r,['trainer','cfg','reset']);self.assertEqual(self.g.weights.trainer.cfg['anchor_weight'],8.)
    def test_operator(self):
        self.r.models=FakeModels(None)
        self.assertIn('"active":"none"',operator_command(self.r,['trainer']))

if __name__=='__main__':unittest.main()
