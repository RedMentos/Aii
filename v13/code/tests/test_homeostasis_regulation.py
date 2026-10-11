"""WP-U2: §16.2 homeostasis regulates N10 path gains slowly (SHADOW unless a human activates it); §68 conflict -> verify first."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13 import homeostasis as H
from v13.neuromod import controller as nm_controller, META

def snap(acts,useful=()):return {'activations':dict(acts),'useful':sorted(useful)}

class Regulate(unittest.TestCase):
    def test_dominant_path_is_damped_and_specialisation_stays_bounded(self):
        prev=snap({'a':0,'b':0,'c':0,'d':0});cur=snap({'a':90,'b':4,'c':3,'d':3})
        reg=H.regulate(prev,cur,{},{},{})
        a=reg['paths']['a'];self.assertIn('DOMINANT',a['reasons']);self.assertLess(a['target'],1.);self.assertLess(a['gain'],1.)
        self.assertEqual(reg['paths']['b']['gain'],1.)
        g={'a':1.}
        for _ in range(50):g={'a':H.regulate(prev,cur,g,{},{})['paths']['a']['gain']}
        self.assertGreaterEqual(g['a'],H.GAIN_MIN);self.assertGreater(g['a'],.5)  # damped, never silenced
    def test_moves_only_part_of_the_way_per_night(self):
        reg=H.regulate(snap({'a':0,'b':0,'c':0}),snap({'a':100,'b':1,'c':1}),{},{},{})
        a=reg['paths']['a'];self.assertAlmostEqual(a['gain'],round(1+H.HOME['activation_balance']*(a['target']-1),6),places=5)
    def test_dead_useful_path_reopens_dead_useless_does_not(self):
        reg=H.regulate(snap({'a':5,'b':7,'c':9}),snap({'a':5,'b':7,'c':20},useful=['a']),{},{},{})
        self.assertIn('DEAD_USEFUL_REOPEN',reg['paths']['a']['reasons']);self.assertGreater(reg['paths']['a']['gain'],1.)
        self.assertEqual(reg['paths']['b']['reasons'],[]);self.assertEqual(reg['paths']['b']['gain'],1.)
    def test_update_budget_normalised_and_first_night_does_not_judge_dominance(self):
        reg=H.regulate(None,snap({'a':10,'b':10,'c':10}),{},{'a':12,'b':0,'c':0},{})
        self.assertEqual(reg['paths']['a']['reasons'],['UPDATE_BUDGET']);self.assertLess(reg['paths']['a']['gain'],1.)
        self.assertNotIn('DOMINANT',H.regulate(None,snap({'a':99,'b':1,'c':1}),{},{},{})['paths']['a']['reasons'])
    def test_route_dominance_is_monitor_only(self):
        r=H.regulate(None,snap({}),{},{},{'simple':9,'detail':1})['routes']
        self.assertEqual((r['dominant'],r['action']),('simple','MONITOR_ONLY'))
        self.assertIsNone(H.regulate(None,snap({}),{},{},{'simple':5})['routes']['dominant'])  # too few samples

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.n=nm_controller(self.r)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_gain_reaches_the_gate_only_when_active(self):
        for i in range(3):
            for p in ('route','memory_retrieval','attention_policy'):self.n.touch(p,'e%d'%i)
        H.run(self.r)
        for i in range(40):self.n.touch('route','f%d'%i)
        for p in ('memory_retrieval','attention_policy'):self.n.touch(p,'g')
        rep=H.run(self.r);self.assertIn('DOMINANT',rep['regulation']['paths']['route']['reasons']);self.assertEqual(rep['regulation']['mode'],'SHADOW')
        g=self.n.gate('route');self.assertLess(g['homeostasis']['gain'],1.);self.assertEqual(g['homeostasis']['mode'],'SHADOW')
        shadow=g['factor']
        with self.assertRaises(PermissionError):H.set_mode(self.r.store,'ACTIVE')
        self.assertIn('ACTIVE',H.operator_command(self.r,['active']))
        self.assertLess(self.n.gate('route')['factor'],shadow)
        self.assertEqual(H.report(self.r.store)['mode'],'ACTIVE')
    def test_conflicting_evidence_blocks_learning_until_verified(self):
        self.n.touch('route','e1')
        self.n.signal('e1','route','verified_teacher',task_success=1.)
        self.assertFalse(self.n.gate('route')['conflict']['verify_first'])
        self.n.signal('e2','route','verified_teacher',task_success=-1.)
        g=self.n.gate('route');self.assertTrue(g['conflict']['verify_first']);self.assertGreaterEqual(g['conflict']['level'],META['conflict_verify_before_learn'])
        self.assertEqual(g['factor'],0.);self.assertEqual(self.n.local_update('route',1.)['scale'],0.)
        self.n.signal('e3','route','human_correction',human_correction=1.)  # a human settles it
        g=self.n.gate('route');self.assertFalse(g['conflict']['verify_first']);self.assertGreater(g['factor'],0.)

if __name__=='__main__':unittest.main()
