"""WP-N4 rest: learned C5 promote/suppress pathways (separate modulators), SHADOW/ACTIVE, C6 egress schema check."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import actionlearn as A
from v13.focal import ActionGate
from v13.inputs import record_rating

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.c=A.C5Learning(self.r.store)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def event(self,t='x'):
        eid=self.r.store.event(self.r.session,t)['event_id']
        return {'event_id':eid,'brain_generation_id':self.r.store.generation_id,'source_ref':self.r.store.source(t)}

class LearningTests(Base):
    def test_pathways_stay_separate_and_bounded(self):
        ctx=A.context('detail',.5)
        for _ in range(5):self.c.learn(ctx,'B1_DETAIL',cost_error=1.,rule_violation=1.,task_success=0.)
        for _ in range(5):self.c.learn(ctx,'C3_LANGUAGE',task_success=1.,human_approval=1.)
        rep=self.c.report()['actions']
        self.assertGreater(rep[ctx+'|B1_DETAIL']['suppress'],0);self.assertEqual(rep[ctx+'|B1_DETAIL']['promote'],0.)
        self.assertEqual(set(rep[ctx+'|B1_DETAIL']['modulators']),{'cost_error','rule_violation','task_success'})
        sh,_=self.c.shifts(ctx,['B1_DETAIL','C3_LANGUAGE']);self.assertEqual(sh['B1_DETAIL'],-A.LEARNED_MAX);self.assertGreater(sh['C3_LANGUAGE'],0)
        with self.assertRaises(ValueError):self.c.learn(ctx,'C3_LANGUAGE',reward=1.)
    def test_gate_shadow_logs_active_reorders_but_never_unsuppresses(self):
        ctx=A.context('detail',.5)
        for _ in range(5):self.c.learn(ctx,'B1_DETAIL',cost_error=1.,rule_violation=1.,action_prediction_error=1.);self.c.learn(ctx,'C3_LANGUAGE',task_success=1.,human_approval=1.)
        e=self.event();out=ActionGate(self.r.store).select(e,route='detail',direct=False,resource_state='NORMAL',effort=.5)
        p=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=?",(e['event_id'],))['payload'])
        self.assertEqual(out['role'],'B1_DETAIL');self.assertEqual(p['learning']['learned'],'C3_LANGUAGE');self.assertEqual(p['learning']['boot'],'B1_DETAIL')
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN');e=self.event()
        self.assertEqual(ActionGate(self.r.store).select(e,route='detail',direct=False,resource_state='NORMAL',effort=.5)['role'],'C3_LANGUAGE')
        for _ in range(5):self.c.learn(A.context('simple',.5),'EXTERNAL_TOOL',task_success=1.,human_approval=1.)
        e=self.event();out=ActionGate(self.r.store).select(e,route='simple',direct=False,resource_state='NORMAL',effort=.5)
        self.assertNotEqual(out['role'],'EXTERNAL_TOOL')  # permission suppression wins over learning
        self.assertLess(self.c.report()['agreement_with_boot'],1.)
        with self.assertRaises(PermissionError):self.c.set_mode('ACTIVE')

class EgressTests(unittest.TestCase):
    def test_typed_checks(self):
        self.assertTrue(A.egress('TEXT_REPORT','Hello.')['ok'])
        self.assertIn('empty',A.egress('TEXT_REPORT','  ')['violations']);self.assertIn('control_characters',A.egress('TEXT_REPORT','a\x07b')['violations'])
        self.assertIn('clarify_without_question',A.egress('CLARIFY','Tell me more.')['violations'])
        self.assertIn('exact_render_differs_from_source',A.egress('EXACT_RENDER','abc','abd')['violations'])
        self.assertTrue(A.egress('TOOL_CALL',{'tool':'calc','args':{'expr':'2*3'}},tools={'calc'})['ok'])
        self.assertIn('unknown_tool',A.egress('TOOL_CALL',{'tool':'shell','args':{}},tools={'calc'})['violations'])
        self.assertIn('unsafe_arg:x',A.egress('TOOL_CALL',{'tool':'calc','args':{'x':'1; rm -rf /'}},tools={'calc'})['violations'])
        self.assertIn('tool_schema',A.egress('TOOL_CALL','rm -rf /')['violations'])

class RuntimeTests(Base):
    def test_turn_writes_egress_and_learns_and_rating_feeds_c5(self):
        def gen(messages,*a,**k):yield 'fine answer'
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit('hello there');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        row=self.r.last_answer();self.assertEqual(row['status'],'FINAL');eg=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='EgressCheck' AND event_id=?",(row['event_id'],))['payload']);self.assertTrue(eg['ok']);self.assertEqual(eg['rewrites'],0)
        rep=self.c.report()['actions'];key=[k for k in rep if k.endswith('|C3_LANGUAGE')][0];self.assertEqual(rep[key]['n'],1)
        record_rating(self.r.store,row['event_id'],2,'EXPLICIT_NOTE')
        rep=self.c.report()['actions'];self.assertEqual(rep[key]['n'],2);self.assertGreater(rep[key]['modulators']['human_correction'],0)
        self.assertIn('agreement_with_boot',Operator(self.r).run(':c5'))

if __name__=='__main__':unittest.main()
