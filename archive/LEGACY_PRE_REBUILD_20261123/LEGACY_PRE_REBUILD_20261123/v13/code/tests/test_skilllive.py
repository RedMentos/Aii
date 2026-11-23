"""WP-T6 skills live: automatic path without C_fast, fallback, live parity, habits (fixtures, no models)."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from v13 import skilllive
from v13.agi import hub
from v13.operator import Operator
from v13.runtime import Runtime

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.lib=hub(self.r).skills
        Operator(self.r).run(':observers off')
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=lambda *a,**k:iter(['ok'])))
        self.r.learner.output_delta=Mock(return_value=None)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def turn(self,text):
        self.r.submit(text);until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        row=self.r.last_answer();return json.loads(row['metadata']),row
    def trusted(self,name='weekly_plan',trigger='weekly plan',route='gist'):
        self.lib.propose(name,[{'route':route}],trigger=trigger);self.lib.set_stage(name,'TRUSTED');return name

class Automatic(Base):
    def test_trusted_skill_routes_without_c_fast(self):
        self.trusted();self.r._route=Mock(side_effect=AssertionError('C_fast must not run'))
        meta,row=self.turn('Make my weekly plan please')
        self.assertEqual(meta['route']['source'],'TRUSTED_SKILL_AUTOMATIC');self.assertTrue(meta['skill']['automatic'])
        self.assertEqual(self.lib.get('weekly_plan')['uses'],1)
    def test_no_match_or_operator_override_uses_full_path(self):
        self.trusted();self.r._route=Mock(return_value=('simple',{'source':'BOOT_SCAFFOLD'}))
        meta,_=self.turn('What time is it');self.assertEqual(meta['route']['source'],'BOOT_SCAFFOLD');self.r._route.assert_called_once()
        self.r.cfg['route_override']='detail';self.r._route=Mock(return_value=('detail',{'source':'OPERATOR_ROUTE_OVERRIDE'}))
        meta,_=self.turn('Make my weekly plan');self.assertEqual(meta['route']['source'],'OPERATOR_ROUTE_OVERRIDE')
    def test_route_correction_and_failure_reopen_the_skill(self):
        self.trusted();self.r._route=Mock(return_value=('simple',{'source':'BOOT_SCAFFOLD'}))
        meta,row=self.turn('Make my weekly plan')
        self.r.memory.feedback(row['event_id'],'route','gist');self.assertEqual(self.lib.get('weekly_plan')['stage'],'TRUSTED')  # agreeing correction
        self.r.memory.feedback(row['event_id'],'route','detail');self.assertEqual(self.lib.get('weekly_plan')['stage'],'SHADOW')
        self.trusted('daily_plan','daily plan','detail');e=self.r.store.event(self.r.session,'daily plan')
        skilllive.after_turn(self.r,e,{'skill':{'name':'daily_plan','automatic':True}},'ERROR','detail')
        self.assertEqual(self.lib.get('daily_plan')['stage'],'SHADOW')
        meta,_=self.turn('Make my daily plan');self.assertNotEqual(meta['route']['source'],'TRUSTED_SKILL_AUTOMATIC')  # reopened: full path again

class LiveLearning(Base):
    def test_shadow_skill_gets_parity_from_normal_turns(self):
        self.lib.propose('budget_check',[{'route':'detail'}],trigger='budget check')
        self.r._route=Mock(return_value=('detail',{'source':'BOOT_SCAFFOLD'}))
        for _ in range(3):meta,_=self.turn('Run a budget check for me')
        sk=self.lib.get('budget_check');self.assertEqual(sk['stage'],'SHADOW');self.assertEqual(sk['parity'],[1.,1.,1.])
        self.r._route=Mock(return_value=('gist',{'source':'BOOT_SCAFFOLD'}));self.turn('Run a budget check for me')
        self.assertEqual(self.lib.get('budget_check')['parity'][-1],0.)
    def test_repeated_cue_becomes_a_candidate_habit(self):
        self.r._route=Mock(return_value=('gist',{'source':'BOOT_SCAFFOLD'}))
        for i in range(skilllive.HABIT_N):self.turn('Summarize morning emails quickly '+str(i))
        st=skilllive.report(self.r);key=skilllive.cue_key('Summarize morning emails quickly')
        name=st['habits'][key]['proposed'];self.assertTrue(name.startswith('habit_'))
        sk=self.lib.get(name);self.assertEqual((sk['stage'],sk['origin'],sk['steps']),('CANDIDATE','SELF',[{'route':'gist'}]))
        self.assertIn(name,json.loads(Operator(self.r).run(':skilllive'))['learning_skills'])
    def test_mixed_routes_do_not_form_a_habit(self):
        e=self.r.store.event(self.r.session,'Summarize morning emails quickly')
        for i in range(8):skilllive.after_turn(self.r,e,{},'FINAL','gist' if i%2 else 'detail')
        self.assertIsNone(skilllive.report(self.r)['habits'][skilllive.cue_key('Summarize morning emails quickly')]['proposed'])

if __name__=='__main__':unittest.main()
