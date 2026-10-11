"""WP-T2: Age rights per capability reach ExecState, effort/focal, gist, attention, cognition; maturity evidence is fed live."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from v13.config import initialize
from v13.store import Store
from v13 import age, effort
from v13.executive import permission_flags
from v13.agi.base import age_allows

GOOD={'experience':10000,'competence':.95,'stability':.95,'retention':.98,'calibration':.9,'memory_health':.97,'safe_self_control':.999,'regression_pass':True}

class AgeStageChangesAllowedPaths(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory();self.home=Path(self.td.name);self.cfg=initialize(self.home);self.store=Store(self.home)
        self.cfg['user_stage_cap']=5;self.a=age.AgeControl(self.store,self.cfg,build_ceiling=5)
    def tearDown(self):self.store.close();self.td.cleanup()
    def plan(self):return {'wake':'both','max_reentry':1,'focal_slots':4,'focal_cycles':6,'tool_steps':2,'verify':True,'effort':.8,'band':'HIGH'}
    def test_age_stage_changes_allowed_paths(self):
        a=self.a;lim=effort.age_limits(a,'NORMAL');pf=permission_flags(a,self.cfg,'NORMAL')
        self.assertFalse(lim['tools']);self.assertFalse(lim['deliberation']);self.assertFalse(pf['external_tool_execution'])
        p=effort.constrain(self.plan(),age=lim);self.assertEqual(p['tool_steps'],0);self.assertFalse(p['verify'])
        self.assertFalse(a.gist_resolution()['adaptive_grouping']);self.assertFalse(age_allows(a,'simple_tool_choice','SELF'))
        for _ in range(9):a.record('system',GOOD)
        self.assertEqual(a.system_stage(),3)
        # A mature system stage alone does not open capability rights: tool and language are still Age 0.
        lim=effort.age_limits(a,'NORMAL');pf=permission_flags(a,self.cfg,'NORMAL')
        self.assertFalse(lim['tools']);self.assertFalse(lim['deliberation']);self.assertFalse(pf['external_tool_execution'])
        self.assertIn('own_sleep_planning',pf['rights']);self.assertNotIn('simple_tool_choice',pf['rights'])
        self.assertFalse(age_allows(a,'simple_tool_choice','SELF'));self.assertTrue(age_allows(a,'simple_tool_choice','USER'))
        for _ in range(3):a.record('tool',GOOD)
        for _ in range(6):a.record('language',GOOD)
        lim=effort.age_limits(a,'NORMAL');pf=permission_flags(a,self.cfg,'NORMAL')
        self.assertEqual(pf['age_by_capability']['tool'],1);self.assertEqual(pf['age_by_capability']['language'],2)
        self.assertTrue(lim['tools']);self.assertTrue(lim['deliberation']);self.assertTrue(pf['external_tool_execution'])
        p=effort.constrain(self.plan(),age=lim);self.assertEqual(p['tool_steps'],2);self.assertTrue(p['verify'])
        self.assertTrue(a.gist_resolution()['adaptive_grouping']);self.assertTrue(age_allows(a,'simple_tool_choice','SELF'))
        self.assertFalse(lim['long_loops'])  # long_loops needs language Age 3
        self.assertFalse(pf['native_body_training'])  # body_port never measured -> stays closed
        # Resources still mask rights; a demotion closes the path again.
        self.assertNotIn('own_sleep_planning',permission_flags(a,self.cfg,'CRITICAL')['rights'])
        a.lower('tool',0);self.assertFalse(effort.age_limits(a,'NORMAL')['tools'])
    def test_gist_without_adaptive_right_keeps_base_grouping(self):
        a=self.a
        for _ in range(3):a.record('system',GOOD)
        for _ in range(3):a.record('language',GOOD)
        self.assertEqual(a.ceiling('language'),1);g=a.gist_resolution()
        self.assertFalse(g['adaptive_grouping']);self.assertEqual(g['tokens_per_group'],age.GIST_BASE[1])

class Clock:
    def __init__(self,t=1_700_000_000.):self.t=t
    def __call__(self):return self.t

class LiveFeed(unittest.TestCase):
    def setUp(self):
        from v13.runtime import Runtime
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_turn_feed_records_system_and_capabilities_rate_limited(self):
        from v13.agi import hub
        from v13.agi import maturity
        g=hub(self.r);c=Clock();out=maturity.turn_feed(g,c)
        self.assertIn('system',out['recorded']);self.assertIn('language',out['recorded']);self.assertNotIn('vision',out['recorded'])
        self.assertEqual(g.age.view()['capabilities']['language']['evidence'],1)
        c.t+=10;self.assertIsNone(maturity.turn_feed(g,c))  # rate limit
        c.t+=maturity.TURN_FEED_MIN_S;self.assertIsNone(maturity.turn_feed(g,c))  # no new experience
        real=maturity.collect
        with mock.patch.object(maturity,'collect',lambda *x:dict(real(*x),experience=7)):
            self.assertIsNotNone(maturity.turn_feed(g,c))
        self.assertEqual(g.age.view()['capabilities']['routing_skill']['evidence'],2)
    def test_exec_state_flags_come_from_age(self):
        pf=permission_flags(age.controller(self.r),self.r.cfg,'NORMAL')
        self.assertEqual(pf['age'],0);self.assertIn('direct_route',pf['rights']);self.assertNotIn('short_dream',pf['rights'])
        self.assertEqual(set(pf['age_by_capability']),set(age.CAPABILITIES))

if __name__=='__main__':unittest.main()
