"""WP-U5: representation anchor strength from domain novelty and old-skill stability (SHADOW by default, ACTIVE by a human)."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13 import anchor as AN
from v13.agi.weights import WeightConsolidation

class Policy(unittest.TestCase):
    def test_new_domain_relaxes_old_skill_protects_floors_hold(self):
        new=AN.policy(1.,0.,shared=False);old=AN.policy(0.,1.,shared=False)
        self.assertEqual(new['reason'],'NEW_DOMAIN_RELAXED');self.assertLess(new['multiplier'],1.)
        self.assertEqual(old['reason'],'OLD_SKILL_PROTECTED');self.assertGreater(old['multiplier'],1.)
        self.assertGreaterEqual(new['multiplier'],AN.ANCHOR['pretrained_geometry_weight'])
        self.assertEqual(AN.policy(1.,0.,shared=True)['multiplier'],AN.ANCHOR['shared_layer_priority'])  # shared layers keep more anchor
        self.assertLessEqual(AN.policy(0.,1.)['multiplier'],AN.MAX_MULT)

class Fake:
    method='fake'
    def __init__(self):self.cfg={'anchor_weight':8.,'targets':('w1','w2','w3')};self.seen=[]
    def fit(self,items,base,cancel=None,deadline=None):
        self.seen.append(self.cfg['anchor_weight']);return {'artifact':'x.gguf','hash':'h','method':'fake','metrics':{}}

class Batch(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def fact(self,q,v):
        e=self.s.event(self.r.session,q);self.r.memory.feedback(e['event_id'],'fact',v)
    def test_novelty_measures_overlap_with_existing_memories(self):
        self.assertEqual(AN.novelty(self.s,[{'memory_id':'x','prompt':'Projekt Aurora Budget?'}]),1.)
        self.fact('Projekt Aurora Budget im Mai?','120 Euro')
        same=AN.novelty(self.s,[{'memory_id':'x','prompt':'Projekt Aurora Budget im Mai?'}])
        other=AN.novelty(self.s,[{'memory_id':'x','prompt':'Wie heißt der Hund von Kunde Berta?'}])
        self.assertLess(same,other);self.assertEqual(other,1.)
    def test_shadow_records_active_applies_and_restores(self):
        self.fact('Projekt Aurora Budget?','120 Euro');t=Fake()
        w=WeightConsolidation(self.s,self.r.cfg|{'learning_mode':'SHADOW_UPDATE'},trainer=t)
        b=w.train(w.stage(require_replay_pass=False)['batch_id'])
        a=b['anchor'];self.assertEqual((a['mode'],a['applied']),('SHADOW',False));self.assertEqual(t.seen,[8.])
        self.assertIn('proposed_anchor_weight',a)
        with self.assertRaises(PermissionError):AN.set_mode(self.s,'ACTIVE')
        AN.operator_command(self.r,['active'])
        w.box.mutate(lambda st:st['batches'].clear());b=w.train(w.stage(require_replay_pass=False)['batch_id'])
        self.assertTrue(b['anchor']['applied']);self.assertEqual(t.seen[-1],b['anchor']['proposed_anchor_weight'])
        self.assertEqual(t.cfg['anchor_weight'],8.)  # restored after the batch

if __name__=='__main__':unittest.main()
