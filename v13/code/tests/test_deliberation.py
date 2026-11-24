"""WP-N2 rest: world-error trigger, learned deliberation space (SHADOW/ACTIVE), halt only after stable trajectory."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import deliberation as D
from v13 import neuromod as N

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.d=D.Deliberation(self.r.store,N.Neuromod(self.r.store))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,t='x'):return self.r.store.event(self.r.session,t)['event_id']

class WorldErrorTests(Base):
    def test_modulator_world_error_opens_trigger(self):
        self.assertFalse(self.d.world_error(self.r.session))
        e=self.ev();N.Neuromod(self.r.store).signal(e,path='fast_forward',source_class='real_deterministic_outcome',world_prediction_error=.2)
        self.assertFalse(self.d.world_error(self.r.session))
        N.Neuromod(self.r.store).signal(e,path='fast_forward',source_class='real_deterministic_outcome',world_prediction_error=.9)
        self.assertTrue(self.d.world_error(self.r.session));self.assertFalse(self.d.world_error('other-session'))
        self.assertFalse(self.d.world_error(self.r.session,now=time.time()+D.RECENT_S+5))
    def test_mixed_attribution_opens_trigger(self):
        from v13.contracts import packet
        def add(cls):
            e=self.ev();self.r.store.add_packet('SelfWorldAttribution',packet('SelfWorldAttribution','F3_SELF',e,self.r.store.generation_id,[],
                channel='status',attribution=cls,reason='t',action_ids=['a1'],residual=None,delayed=False))
        add('SELF');self.assertFalse(self.d.world_error(self.r.session))
        add('MIXED');self.assertTrue(self.d.world_error(self.r.session))

class OrderTests(Base):
    MODES=['HYPOTHESIS','COUNTEREXAMPLE','SOURCE_CHECK','ALTERNATIVE']
    def train(self,trig=('NOVELTY',)):
        for i in range(D.MIN_N+2):
            e=self.ev();self.d.record(e,list(trig),'ANSWER',2,[{'mode':'HYPOTHESIS','verdict':'PROPOSED'},{'mode':'COUNTEREXAMPLE','verdict':'NO_TARGET'},
                                                              {'mode':'SOURCE_CHECK','verdict':'CONTESTED'},{'mode':'ALTERNATIVE','verdict':'NO_TARGET'}])
    def test_shadow_proposes_active_applies_hypothesis_first(self):
        m,p,a=self.d.order(self.MODES,['NOVELTY'],True);self.assertEqual(m,self.MODES);self.assertFalse(a)
        self.train();m,p,a=self.d.order(self.MODES,['NOVELTY'],True)
        self.assertEqual(m,self.MODES);self.assertFalse(a);self.assertEqual(p[:2],['HYPOTHESIS','SOURCE_CHECK']);self.assertEqual(sorted(p),sorted(self.MODES))
        with self.assertRaises(PermissionError):self.d.set_mode('ACTIVE')
        self.d.set_mode('ACTIVE','EXPLICIT_HUMAN');m,p,a=self.d.order(self.MODES,['NOVELTY'],True);self.assertTrue(a);self.assertEqual(m,p)
        m,p,a=self.d.order(self.MODES,['NOVELTY'],False);self.assertFalse(a);self.assertEqual(m,self.MODES)  # Age right missing
        self.assertFalse(self.d.order(self.MODES,['CONFLICT'],True)[2])  # other trigger set is unlearned
    def test_rating_outcome_nudges_used_modes(self):
        e=self.ev();self.d.record(e,['CONFLICT'],'ANSWER',1,[{'mode':'HYPOTHESIS','verdict':'PROPOSED'}])
        before=self.d.report()['mode_values']['CONFLICT|HYPOTHESIS']['value']
        self.assertEqual(D.on_rating(self.r.store,e,10)['updated_modes'],1)
        self.assertGreater(self.d.report()['mode_values']['CONFLICT|HYPOTHESIS']['value'],before)
        self.assertEqual(self.d.outcome('unknown',1.)['updated_modes'],0)

class HaltTests(Base):
    def test_halt_only_after_stable_window(self):
        t=['WORLD_PREDICTION_ERROR']
        for i in range(D.WINDOW-1):self.d.record(self.ev(),t,'ANSWER',2,[])
        self.assertFalse(self.d.halt_allowed(t))
        self.d.record(self.ev(),t,'ANSWER',2,[]);self.assertTrue(self.d.halt_allowed(t))
        for i in range(3):self.d.record(self.ev(),t,'ASK' if i%2 else 'IGNORE',2,[])
        self.assertFalse(self.d.halt_allowed(t))
        u=['CONFLICT']
        for i in range(D.WINDOW):self.d.record(self.ev(),u,'ANSWER',1+3*(i%2),[])
        self.assertFalse(self.d.halt_allowed(u))  # cycle counts not narrow
        self.assertIn('WORLD_PREDICTION_ERROR',self.d.report()['trajectory_stability'])

class RuntimeTests(Base):
    def test_turn_stays_final_and_operator(self):
        def gen(messages,*a,**k):yield 'fine'
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit('hello there');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        self.assertEqual(self.r.last_answer()['status'],'FINAL')
        op=Operator(self.r);self.assertIn('SHADOW',op.run(':delib'));self.assertIn('ACTIVE',op.run(':delib active'));self.assertIn('SHADOW',op.run(':delib shadow'))
        self.assertEqual(N.kind_of('inquisition_policy'),'control')

if __name__=='__main__':unittest.main()
