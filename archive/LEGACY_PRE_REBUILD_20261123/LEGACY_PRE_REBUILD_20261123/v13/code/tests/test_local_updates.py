"""WP-U6 §12.7: each learned head scales its own step by the N10 gate of its path (SHADOW default = unchanged)."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13.neuromod import Neuromod,step
from v13.actionlearn import C5Learning

PATH='c5_action_selection'

class LocalUpdates(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.n=Neuromod(self.r.store);self.c=C5Learning(self.r.store,self.n)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def mod(self,ctx):return self.c._load()[0]['q'][ctx+'|simple']['mods']['task_success']
    def test_shadow_keeps_the_head_step_active_scales_it(self):
        self.assertEqual(step(None,PATH),1.);self.assertEqual(self.n.step_scale(PATH),1.)
        for ctx in ('a','b'):self.c.learn(ctx,'simple','e0',task_success=0.)
        self.c.learn('a','simple','e1',task_success=1.);shadow=self.mod('a')
        self.assertAlmostEqual(shadow,.2)  # RATE .2, unchanged in SHADOW
        with self.assertRaises(PermissionError):self.n.set_local_mode('ACTIVE')
        self.n.set_local_mode('ACTIVE','EXPLICIT_HUMAN');f=self.n.gate(PATH)['factor']
        self.assertEqual(self.n.step_scale(PATH),f);self.assertLess(f,1.)
        self.c.learn('b','simple','e2',task_success=1.);self.assertAlmostEqual(self.mod('b'),round(.2*f,4),places=4)
    def test_veto_stops_the_head_from_learning(self):
        self.n.set_local_mode('ACTIVE','EXPLICIT_HUMAN')
        self.c.learn('a','simple','e0',task_success=0.)
        self.n.signal('e0',PATH,safety_veto=True)
        self.assertEqual(self.n.step_scale(PATH),0.)
        self.c.learn('a','simple','e1',task_success=1.);self.assertEqual(self.mod('a'),0.)
    def test_operator_switch(self):
        from v13.neuromod import operator_command
        self.assertIn('ACTIVE',operator_command(self.r,['local','active']));self.assertIn('SHADOW',operator_command(self.r,['local','shadow']))

if __name__=='__main__':unittest.main()
