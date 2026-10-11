"""WP-D adaptive reasoning effort / body-wake (G5B, §10.2). No model needed.

Policy tests are pure. Runtime tests use the real coordinator + SQLite with
native seams replaced by spies; they prove which compute is requested, not
model quality.
"""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from v13 import effort
from v13.contracts import validate
from v13.operator import Operator
from v13.runtime import Runtime

CFG={'max_reentry':1,'focal_slots':4}


def sig(text,route='simple',**kw):return effort.signals(text,route,{'source':'BOOT_SCAFFOLD','scaffold':route},**kw)


class EffortPolicy(unittest.TestCase):
    def test_bands_follow_blueprint_boot_ranges(self):
        self.assertEqual([effort.band(x) for x in (0.,.19,.2,.49,.5,.79,.8,1.)],
                         ['DIRECT_C_NATIVE']*2+['C_NATIVE_ONE_BODY']*2+['FOCAL_TARGETED']*2+['DEEP_FOCAL']*2)

    def test_adaptive_keeps_easy_cheap_and_recruits_matching_bodies(self):
        easy=effort.decide('adaptive',sig('Hallo, wie geht es dir?'),cfg=CFG)
        self.assertEqual(easy['wake'],'none');self.assertLess(easy['effort'],.5);self.assertEqual(easy['max_reentry'],0)
        self.assertEqual(effort.decide('adaptive',sig('Hallo'),cfg=CFG)['band'],'DIRECT_C_NATIVE')
        calc=effort.decide('adaptive',sig('Berechne 17 * 23 für mein Budget','detail'),cfg=CFG)
        self.assertEqual(calc['wake'],'detail');self.assertEqual(calc['max_reentry'],0)
        gist=effort.decide('adaptive',sig('Fasse den Plan zusammen und gib einen Überblick','gist'),cfg=CFG)
        self.assertEqual(gist['wake'],'gist')
        mixed=effort.decide('adaptive',sig('Vergleiche Option A und B: Kosten 120 + 80 oder Strategie?','both'),cfg=CFG)
        self.assertGreaterEqual(mixed['effort'],.5);self.assertEqual(mixed['wake'],'both');self.assertEqual(mixed['max_reentry'],1)

    def test_escalation_rule_lifts_effort_to_at_least_half(self):
        s=sig('Hallo')|{'uncertainty':.5}
        self.assertGreaterEqual(effort.adaptive_effort(s),.5)
        s=sig('Hallo')|{'conflict':.41}
        self.assertGreaterEqual(effort.adaptive_effort(s),.5)

    def test_open_questions_and_salience_raise_effort(self):
        base=effort.adaptive_effort(sig('Kannst du das nochmal prüfen'))
        self.assertGreater(effort.adaptive_effort(sig('Kannst du das nochmal prüfen',open_questions=3)),base)
        self.assertGreater(effort.adaptive_effort(sig('Kannst du das nochmal gründlich prüfen? Wichtig!')),base)

    def test_familiar_topic_is_less_novel_than_new_topic(self):
        text='Projekt Aurora Budget Planung Lieferanten Termine Risiken'
        new=sig(text);old=sig(text,prior_goals=[text])
        self.assertGreater(new['novelty'],old['novelty']);self.assertEqual(old['novelty'],0.)

    def test_user_modes_are_fixed_and_ordered_in_cost(self):
        s=sig('Vergleiche A und B','both');plans={m:effort.decide(m,s,cfg=CFG) for m in effort.MODES}
        self.assertEqual(plans['disabled']['wake'],'none');self.assertEqual(plans['low']['wake'],'none')
        self.assertEqual(plans['max']['wake'],'both');self.assertEqual(plans['max']['max_reentry'],1)
        self.assertEqual(plans['high']['effort'],.7);self.assertFalse(plans['high']['learned_wake_allowed'])
        with self.assertRaises(ValueError):effort.decide('turbo',s)

    def test_hard_limits_bind_user_override(self):
        s=sig('Vergleiche A und B','both')
        for limits,reason in (({'direct':True},'EXACT_OR_FIXED_OUTPUT'),({'observers':False},'OBSERVERS_OFF'),
                              ({'resource_state':'PRESSURE'},'RESOURCE_PRESSURE'),({'observer_window_s':.5},'DEADLINE_NO_BODY')):
            p=effort.decide('max',s,cfg=CFG,**limits)
            self.assertEqual(p['wake'],'none',reason);self.assertIn(reason,p['constraints']);self.assertEqual(p['max_reentry'],0);self.assertFalse(p['verify'])
        p=effort.decide('max',s,cfg=CFG,observer_window_s=3.)
        self.assertEqual(p['wake'],'detail');self.assertIn('DEADLINE_ONE_BODY',p['constraints'])
        p=effort.decide('max',s,cfg={'max_reentry':0,'focal_slots':2})
        self.assertEqual((p['max_reentry'],p['focal_slots']),(0,2))
        p=effort.decide('max',s,cfg=CFG)
        self.assertEqual((p['tool_steps'],p['verify'],p['focal_cycles']),(0,False,1))
        for reason in ('AGE_NO_TOOLS','AGE_NO_DELIBERATION_MODES','AGE_FOCAL_DEPTH'):self.assertIn(reason,p['constraints'])

    def test_age_bounds_autonomous_escalation_but_older_stage_opens_it(self):
        hot=sig('Vergleiche A und B','both')|{'uncertainty':1.,'conflict':1.,'novelty':1.,'salience':1.}
        young=effort.decide('adaptive',hot,cfg=CFG)
        self.assertEqual(young['requested_effort'],1.);self.assertLessEqual(young['effort'],.79)
        self.assertEqual(young['band'],'FOCAL_TARGETED');self.assertEqual(young['wake'],'both')
        self.assertIn('AGE_AUTONOMOUS_EFFORT_MAX_LOW',young['constraints'])
        old={'stage':5,'autonomous_effort_max':'max','focal_depth':5,'deliberation':True,'tools':True,'long_loops':True,'resource_mode':'GREEN'}
        mature=effort.decide('adaptive',hot,cfg=CFG,age=old)
        self.assertEqual((mature['band'],mature['verify'],mature['tool_steps'],mature['focal_cycles']),('DEEP_FOCAL',True,1,3))

    def test_age_limits_are_read_from_age_module(self):
        from v13.age import AgeControl
        from v13.config import initialize
        from v13.store import Store
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);cfg=initialize(home);store=Store(home)
            try:
                limits=effort.age_limits(AgeControl(store,cfg),'NORMAL')
                self.assertEqual((limits['stage'],limits['autonomous_effort_max'],limits['deliberation'],limits['tools']),(0,'low',False,False))
                self.assertEqual(effort.age_limits(AgeControl(store,cfg),'PRESSURE')['resource_mode'],'RED')
            finally:store.close()

    def test_learned_wake_only_inside_ceiling_and_never_over_user_mode(self):
        s=sig('Vergleiche A und B','both')
        adaptive=effort.decide('adaptive',s,cfg=CFG,observer_window_s=3.)
        self.assertEqual(effort.resolve_wake(adaptive,'both'),('detail','LEARNED_WAKE_CAPPED'))
        self.assertEqual(effort.resolve_wake(adaptive,'none'),('none','LEARNED_WAKE'))
        forced=effort.decide('max',s,cfg=CFG)
        self.assertEqual(effort.resolve_wake(forced,'none'),('both','EFFORT_POLICY'))
        with self.assertRaises(ValueError):effort.resolve_wake(effort.decide('adaptive',s,cfg=CFG),'everything')

    def test_offline_comparison_reports_underthinking_and_overthinking(self):
        cases=[{'signals':sig('Hallo'),'need':'none'},{'signals':sig('Danke dir'),'need':'none'},
               {'signals':sig('Berechne 17 * 23','detail'),'need':'detail'},
               {'signals':sig('Fasse den Plan zusammen','gist'),'need':'gist'},
               {'signals':sig('Vergleiche Kosten 120 + 80 und Strategie','both'),'need':'both'}]
        r=effort.compare(cases)
        self.assertEqual(r['low']['hard_task_underthinking'],1.);self.assertEqual(r['max']['easy_task_overthinking'],1.)
        self.assertEqual(r['adaptive']['hard_task_underthinking'],0.);self.assertEqual(r['adaptive']['easy_task_overthinking'],0.)
        self.assertLess(r['adaptive']['mean_cost'],r['max']['mean_cost'])


class EffortRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)

    def tearDown(self):
        self.r.close();self.tmp.cleanup()

    def wait(self):
        until=time.monotonic()+5
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        self.assertTrue(self.r.idle());return self.r.last_answer()

    def turn(self,text,route):
        self.r._route=Mock(return_value=(route,{'source':'BOOT_SCAFFOLD','scaffold':route}))
        self.r.learner.decide=Mock(side_effect=lambda component,e,baseline,*a,**k:{'learned':False,'action':baseline})
        self.r.learner.output_delta=Mock(return_value=None)
        foreground=[]
        def offer(role,e,version,deadline,peer=None,*,valid_until=None):
            if valid_until is not None:foreground.append(role)
            raise RuntimeError('test seam: no body model')
        self.r.cognition.offer=offer
        runner=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=lambda *a,**k:iter(['ok']))
        self.r.pool.get=Mock(return_value=runner)
        self.r.submit(text);row=self.wait()
        p=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='EffortDecision' ORDER BY rowid DESC LIMIT 1")['payload'])
        validate('EffortDecision',p);return foreground,p,json.loads(row['metadata'])

    def test_mode_controls_real_body_wake_requests(self):
        op=Operator(self.r)
        op.run(':effort disabled');woken,p,meta=self.turn('Vergleiche A und B','both')
        self.assertEqual(woken,[]);self.assertEqual((p['mode'],p['wake'],p['effort']),('disabled','none',0.))
        self.assertEqual(meta['reasoning_effort'],p['packet_id'])
        op.run(':effort max');woken,p,_=self.turn('Hallo','simple')
        self.assertEqual(woken,['B1_DETAIL','B2_GIST']);self.assertEqual(p['plan']['band'],'DEEP_FOCAL')
        op.run(':effort adaptive');woken,p,_=self.turn('Hallo','simple')
        self.assertEqual(woken,[]);self.assertEqual(p['wake_source'],'EFFORT_POLICY')
        woken,p,_=self.turn('Berechne 17 * 23 für mein Budget','detail')
        self.assertEqual(woken,['B1_DETAIL'])
        status=json.loads(op.run(':effort'))
        self.assertEqual(status['mode'],'adaptive');self.assertEqual(status['turns'],4);self.assertEqual(status['status'],'BOOT_HEURISTIC_NOT_LEARNED')

    def test_mode_survives_restart_and_rejects_unknown(self):
        op=Operator(self.r);op.run(':effort high')
        with self.assertRaises(ValueError):op.run(':effort turbo')
        self.r.close();self.r=Runtime(self.home)
        self.assertEqual(effort.get_mode(self.r.store),'high')


if __name__=='__main__':unittest.main()
