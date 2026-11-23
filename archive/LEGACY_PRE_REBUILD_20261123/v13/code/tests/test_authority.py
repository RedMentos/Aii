"""WP-T10: one promotion path SHADOW -> CANDIDATE -> ACTIVE for learned heads, IH-H25 objective adapters, learning-timescale jobs."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from v13.runtime import Runtime
from v13 import authority as AU
from v13 import objectives as OBJ

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def c5_mode(self):
        from v13.actionlearn import controller
        return controller(self.r)._load()[0]['mode']

class Promotion(Base):
    def test_fresh_heads_stay_shadow_with_named_blockers(self):
        out=AU.review(self.r)
        self.assertEqual(out['changes'],[]);self.assertEqual(set(out['heads']),set(AU.HEADS))
        self.assertTrue(all(h['level']==0 and h['mode']=='SHADOW' for h in out['heads'].values()))
        self.assertIn('NO_COMPARISON',out['heads']['attention']['blockers'])
        self.assertIn('OBJECTIVE_UNAVAILABLE',out['heads']['gist']['blockers'])
    def test_candidate_needs_human_then_regression_falls_back_to_scaffold(self):
        for _ in range(AU.MIN_N):AU.observe(self.r.store,'c5_action','DIRECT','DIRECT')
        with self.assertRaises(ValueError):AU.promote(self.r,'c5_action','EXPLICIT_HUMAN')  # not reviewed yet
        out=AU.review(self.r);a=out['heads']['c5_action']
        self.assertEqual(a['level'],1,a['blockers']);self.assertEqual(a['verdict']['reason'],'REPRODUCES_SCAFFOLD')
        self.assertEqual(self.c5_mode(),'SHADOW')  # a candidate does not act
        with self.assertRaises(PermissionError):AU.promote(self.r,'c5_action','SYSTEM')
        AU.promote(self.r,'c5_action','EXPLICIT_HUMAN');self.assertEqual(self.c5_mode(),'ACTIVE')
        for _ in range(AU.MIN_N):AU.observe(self.r.store,'c5_action','DIRECT','C3',scaffold_ok=True,learned_ok=False)
        out=AU.review(self.r)
        self.assertEqual(self.c5_mode(),'SHADOW');self.assertEqual(out['changes'][0]['reason'],'REGRESSION_FALLBACK_TO_SCAFFOLD')
        hist=AU.report(self.r)['heads']['c5_action']['history'];self.assertEqual([h['kind'] for h in hist],['PROMOTE','PROMOTE','DEMOTE'])
    def test_failing_gate_graph_or_objective_blocks_candidate(self):
        for _ in range(AU.MIN_N):AU.observe(self.r.store,'jef_bridge','B1','B1')
        with mock.patch.object(AU,'_gate_status',return_value={'STEP1':'EVIDENCE_NOT_PASSING'}):
            a=AU.review(self.r)['heads']['jef_bridge']
        self.assertEqual(a['level'],0);self.assertIn('GATE_EVIDENCE_NOT_PASSING',a['blockers'])
        a=AU.review(self.r)['heads']['jef_bridge'];self.assertEqual(a['level'],1)
        with mock.patch.object(AU,'_gate_status',return_value={'STEP1':'OPEN'}):
            a=AU.review(self.r)['heads']['jef_bridge']
        self.assertEqual(a['level'],0)  # evidence lapsed -> back to shadow
    def test_better_outcomes_pass_and_operator_demote(self):
        for i in range(AU.MIN_N):AU.observe(self.r.store,'deliberation','D1','D2',scaffold_ok=i%2==0,learned_ok=True)
        a=AU.review(self.r)['heads']['deliberation']
        self.assertEqual(a['verdict']['reason'],'BETTER_OUTCOMES_THAN_SCAFFOLD');self.assertIn('OBJECTIVE_PARTIAL',a['blockers'])  # objective not IMPLEMENTED
        self.assertIn('"blockers"',AU.operator_command(self.r,['c5_action']))
        self.assertIn('"mode":"SHADOW"',AU.operator_command(self.r,['demote','c5_action']))

class Objectives(unittest.TestCase):
    def test_contract_enforced(self):
        reg=OBJ.registry({});self.assertGreaterEqual(len(reg),25)
        self.assertEqual(reg['B_local_JEPA'].learn_gain({'learning_mode':'APPROVED_COMMIT'}),0)
        imp=reg['c5-action-values-v1'];self.assertEqual(imp.learn_gain({'learning_mode':'RECORD_ONLY','learning_rate':.1}),0)
        self.assertEqual(imp.learn_gain({'learning_mode':'SHADOW_UPDATE','learning_rate':.1}),.1)
        row={'objective_id':'x','applicable_components':['C5'],'status':'IMPLEMENTED','loss_terms':['l'],'eval_metrics':['m'],'update_scope':'s','target_builder':'t','credit_mapper':'c','implementation_files':['v13/nope.py']}
        with self.assertRaises(ValueError):OBJ.from_row(row)
        with self.assertRaises(ValueError):OBJ.from_row(dict(row,loss_terms=[]))
        ok=OBJ.from_row(dict(row,objective_id='plug-test',implementation_files=['v13/authority.py']))
        try:
            OBJ.register(ok);self.assertIn('plug-test',OBJ.registry({}))
        finally:OBJ._PLUGINS.pop('plug-test',None)
        self.assertEqual(OBJ.from_row({'objective_id':'u','applicable_components':['A3'],'status':'UNAVAILABLE'}).learn_gain({'learning_mode':'APPROVED_COMMIT'}),0)

class Timescales(Base):
    def test_medium_and_slow_jobs_run_through_scheduler(self):
        self.assertTrue(AU.medium_due(self.r.store,1e12))
        eid=self.r.sleep.scheduler.post('TIMER',origin='USER',action='learn_medium')
        e=next(x for x in self.r.sleep.scheduler._load()[0]['events'] if x['id']==eid)
        out=self.r.sleep.job(e);self.assertEqual(out['status'],'DONE')
        from v13.common import now
        self.assertFalse(AU.medium_due(self.r.store,now()))
        out=AU.job(self.r,'learn_slow');self.assertIn('IMPLEMENTED',out['objectives']);self.assertNotIn('consolidate_event',out)  # RECORD_ONLY
        with self.assertRaises(ValueError):AU.job(self.r,'learn_fast')

if __name__=='__main__':unittest.main()
