"""WP-F: cerebellar fast-forward predictor, proceduralization lifecycle (G-PROCEDURALIZATION-004), reflex layer."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import fastforward as F
from v13 import reflex as R
from v13 import neuromod as N

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.f=F.FastForward(self.r.store,N.Neuromod(self.r.store))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,t='x'):return self.r.store.event(self.r.session,t)['event_id']

class PredictorTests(Base):
    def test_delta_rule_learns_answer_time_by_wake(self):
        self.assertIsNone(self.f.predict(F.features('q','simple','none'))['duration_s'])
        for i in range(60):
            for wake,dur in (('none',2.),('both',20.)):self.f.learn(self.ev(),F.features('question %d'%i,'simple',wake),dur,'FINAL',120)
        fast=self.f.predict(F.features('question x','simple','none'))['duration_s'];slow=self.f.predict(F.features('question x','simple','both'))['duration_s']
        self.assertLess(abs(fast-2.),1.);self.assertLess(abs(slow-20.),6.);self.assertGreater(self.f.predict(F.features('q','simple','none'))['success_p'],.8)
        out=self.f.learn(self.ev(),F.features('question x','simple','none'),40.,'FINAL',100);self.assertGreater(out['surprise'],.5)
        self.assertEqual(N.kind_of('fast_forward'),'world')
    def test_pattern_is_coarse(self):
        a=F.pattern('what is 2+2','simple',{'novelty':.1});b=F.pattern('what is 3+5','simple',{'novelty':.2})
        self.assertEqual(a,b);self.assertNotEqual(a,F.pattern('what is two','simple',{'novelty':.1}))

class ProceduralTests(Base):
    K='simple|BOOT_SCAFFOLD|short|nonum|nomem|familiar'
    def compile(self):
        for _ in range(F.SKILL['compile_after_successes']):self.f.record_turn(self.K,'none','FINAL',5.)
    def test_lifecycle_observe_compile_shadow_ready(self):
        self.compile();self.assertEqual(self.f.report()['procedures'][self.K]['stage'],'SHADOW')
        for _ in range(F.SKILL['shadow_cycles']):self.f.record_turn(self.K,'none','FINAL',5.,predicted_fast_s=3.)
        p=self.f.report()['procedures'][self.K];self.assertEqual(p['stage'],'READY');self.assertEqual(p['gate']['G'],'G-PROCEDURALIZATION-004')
        self.assertFalse(self.f.procedural(self.K,{})['apply'])  # SHADOW mode never acts
        self.f.set_mode('ACTIVE','EXPLICIT_HUMAN');self.assertEqual(self.f.procedural(self.K,{})['wake'],'none');self.assertTrue(self.f.procedural(self.K,{})['apply'])
        self.assertFalse(self.f.procedural(self.K,{'novelty':.9})['apply'])  # salient/novel turn reopens focal
    def test_inconsistent_or_failing_routes_do_not_compile(self):
        for w in ['none','both']*4:self.f.record_turn(self.K,w,'FINAL',5.)
        self.assertEqual(self.f.report()['procedures'][self.K]['stage'],'OBSERVE')
    def test_gate_fails_on_disagreement_and_failure_reopens(self):
        self.compile()
        for i in range(F.SKILL['shadow_cycles']):self.f.record_turn(self.K,'both' if i%2 else 'none','FINAL',5.)
        self.assertEqual(self.f.report()['procedures'][self.K]['stage'],'SHADOW')
        for _ in range(F.SKILL['shadow_cycles']):self.f.record_turn(self.K,'none','FINAL',5.,predicted_fast_s=3.)
        self.assertEqual(self.f.report()['procedures'][self.K]['stage'],'READY')
        self.f.record_turn(self.K,'none','ERROR',5.,applied=True);self.assertEqual(self.f.report()['procedures'][self.K]['stage'],'OBSERVE')
    def test_latency_must_drop(self):
        self.compile()
        for _ in range(F.SKILL['shadow_cycles']):self.f.record_turn(self.K,'none','FINAL',5.,predicted_fast_s=50.)
        self.assertEqual(self.f.report()['procedures'][self.K]['stage'],'SHADOW')
    def test_active_needs_human(self):
        with self.assertRaises(PermissionError):self.f.set_mode('ACTIVE')

class ReflexTests(Base):
    def setUp(self):
        super().setUp();self.t=[1000.];self.x=R.Reflex(self.r.store,clock=lambda:self.t[0])
    def test_circuit_breaker_opens_and_cools_down_never_for_c3(self):
        for i in range(R.FAILURES-1):self.assertIsNone(self.x.record_failure('B1_DETAIL'))
        self.assertEqual(self.x.record_failure('B1_DETAIL')['action'],'circuit_open');self.assertTrue(self.x.circuit_open('B1_DETAIL'))
        self.t[0]+=R.COOLDOWN_S+1;self.assertFalse(self.x.circuit_open('B1_DETAIL'))
        for i in range(5):self.x.record_failure('C3_LANGUAGE')
        self.assertFalse(self.x.circuit_open('C3_LANGUAGE'))
    def test_old_failures_leave_the_window_and_success_closes(self):
        self.x.record_failure('B2_GIST');self.x.record_failure('B2_GIST');self.t[0]+=R.WINDOW_S+1
        self.assertIsNone(self.x.record_failure('B2_GIST'))
        self.x.record_failure('B2_GIST');self.x.record_failure('B2_GIST');self.assertTrue(self.x.circuit_open('B2_GIST'))
        self.x.record_success('B2_GIST');self.assertFalse(self.x.circuit_open('B2_GIST'))
    def test_timeout_reflex_and_critical_unload(self):
        self.assertIsNone(self.x.timeout_check('e',30.,5.));self.assertIsNone(self.x.timeout_check('e',1.,None))
        self.assertEqual(self.x.timeout_check('e',4.,5.)['action'],'shed_observers')
        pool=Mock();out=self.x.critical('e',pool,{'mem_available_bytes':1});pool.unload.assert_called_once();self.assertTrue(out['detail']['unloaded'])
        self.assertEqual(self.x.report()['counts'],{'imminent_timeout':1,'critical_resource':1})

class RuntimeTests(Base):
    def run_turn(self,role='C3_LANGUAGE',fail=False):
        def gen(messages,*a,**k):
            if fail:raise RuntimeError('boom')
            yield 'fine'
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role=role,last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit('hello there');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        return self.r.last_answer()
    def test_turn_feeds_fast_forward_and_procedures(self):
        for _ in range(4):self.assertEqual(self.run_turn()['status'],'FINAL')
        meta=json.loads(self.r.last_answer()['metadata']);self.assertIn('fast_forward',meta);self.assertIn('procedural',meta)
        rep=F.controller(self.r).report();self.assertGreaterEqual(rep['trained_on'],4);self.assertEqual(len(rep['procedures']),1)
        op=Operator(self.r);self.assertIn('trained_on',op.run(':ff'));self.assertIn('open_circuits',op.run(':reflex'))
    def test_runner_errors_feed_the_circuit_breaker(self):
        for _ in range(3):self.assertEqual(self.run_turn('B1_DETAIL',fail=True)['status'],'ERROR')
        self.assertTrue(R.controller(self.r).circuit_open('B1_DETAIL'))

if __name__=='__main__':unittest.main()
