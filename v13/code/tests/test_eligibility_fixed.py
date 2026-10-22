"""2026-10-22: fixed (non-generative) rule reader for the eligibility tool and the tool decision as the first answer
sentence (cfg eligibility_reader / tool_answer_first). No models."""
import tempfile,unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import toolstep as T
from v13.config import DEFAULTS,validate
from v13.agi import hub,eligibility as E
from tests.test_eligibility_live import PRIOR,CURRENT,FULL,READ,OPTS,FakeC3

ROOT=Path(__file__).resolve().parents[1]

class Reader(unittest.TestCase):
    def test_reads_rules_and_options_of_the_fixture_wording(self):
        self.assertEqual(E.read_fixed(FULL),dict(READ))
        self.assertEqual(E.read_fixed(CURRENT,[PRIOR]),dict(READ))
        self.assertEqual(E.read_fixed(CURRENT),dict(READ,budget=None,deadline=None,local_only=None))
    def test_current_rule_beats_earlier_and_newest_earlier_wins(self):
        text=CURRENT.replace('Apply earlier project rules.','Apply earlier project rules, but now budget 50 euros.')
        self.assertEqual(E.read_fixed(text,[PRIOR])['budget'],50)
        self.assertEqual(E.read_fixed(CURRENT,[PRIOR,'Project Mira. Budget 70 euros.'])['budget'],70)
        self.assertEqual(E.read_fixed(CURRENT,['Budget 70 euros.',PRIOR])['budget'],61)
    def test_two_values_in_one_text_give_no_value(self):
        self.assertIsNone(E.read_fixed(CURRENT,['Budget 61 euros. Budget 70 euros.'])['budget'])
        self.assertIsNone(E.fixed_option('A','Option A: cost 45 euros, cost 50 euros, duration 7 days, local true.'))
    def test_uncovered_option_wording_leaves_options_to_the_model(self):
        self.assertIsNone(E.read_fixed('Budget 61 euros. Option A is 45 euros. Option B costs 55. Which option?')['options'])
    def test_decision_from_fixed_values(self):
        self.assertEqual(E.tool(**E.args_for(E.read_fixed(CURRENT,[PRIOR]),CURRENT,[PRIOR]))['action'],'A')

class Config(unittest.TestCase):
    def test_defaults_and_validation(self):
        from v13.config import LEGACY_PRE_20261022 as L
        self.assertEqual((DEFAULTS['eligibility_reader'],DEFAULTS['tool_answer_first']),('fixed',True))  # FIRST_SUPPORTED 22.10.
        self.assertEqual((L['eligibility_reader'],L['tool_answer_first']),('model',False))
        for bad in ({'eligibility_reader':'c3'},{'tool_answer_first':1}):
            with self.assertRaises(ValueError):validate(dict(DEFAULTS,**bad))
        validate(dict(DEFAULTS,eligibility_reader='fixed',tool_answer_first=True))
    def test_chain_link_is_live(self):
        from scripts.integrated_candidates import INTEGRATED,integrated_sources
        self.assertIn('tool_answer_first',INTEGRATED)
        live=(ROOT/'v13/runtime.py').read_text();self.assertEqual(integrated_sources()['v13/runtime.py'],live)
        self.assertIn("lead=toolctl.ToolStep(self).lead(tool_result)",live)

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.c3=FakeC3(dict(READ,budget=99,local_only=True));self.r.pool.get=lambda role:self.c3  # a model that misreads rules
        hub(self.r).tools.enable('eligibility')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def plan(self,text):
        e=self.r.store.event(self.r.session,text);ts=T.ToolStep(self.r);return e,ts,ts.plan(e,text)
    def test_fixed_reader_needs_no_model_call_and_ignores_model_rules(self):
        self.r.cfg['eligibility_reader']='fixed'
        e,ts,p=self.plan(FULL);self.assertEqual(self.c3.calls,[]);self.assertEqual(ts.shadow(e,p)['result']['action'],'A')
    def test_model_options_with_fixed_rules_when_wording_is_not_covered(self):
        self.r.cfg['eligibility_reader']='fixed'
        text=FULL.replace('Option B: cost 55 euros','Option B costs 55 euros')
        e,ts,p=self.plan(text);self.assertEqual(len(self.c3.calls),1)
        self.assertEqual((p['args']['budget'],p['args']['local_only']),(61,False))
    def test_model_reader_still_selectable(self):
        self.r.cfg['eligibility_reader']='model';e,ts,p=self.plan(FULL);self.assertEqual(len(self.c3.calls),1);self.assertEqual(p['args']['budget'],99)
    def test_lead_only_when_switched_on_and_executed(self):
        self.r.cfg.update(eligibility_reader='fixed',tool_answer_first=False);e,ts,p=self.plan(FULL)
        res={'tool':'eligibility','args':p['args'],'result':E.tool(**p['args']),'tx':'t1','action_tx':None}
        self.assertIsNone(ts.lead(res));self.assertEqual(ts.layer(res)['note'],E.LIVE_NOTE)
        self.r.cfg['tool_answer_first']=True
        self.assertEqual(ts.lead(res),'Choose Option A. Remaining budget: 16 euros.');self.assertEqual(ts.layer(res)['note'],E.FIRST_NOTE)
        self.assertIsNone(ts.lead(dict(res,tool='list_arith')));self.assertIsNone(ts.lead(dict(res,result=None)))
        self.assertEqual(E.answer_action(ts.lead(res)+' It is cheaper and within the deadline.'),'A')
        self.assertIsNone(ts.lead_final(res))
    def test_unknown_and_none_are_fixed_whole_answers(self):
        self.r.cfg.update(eligibility_reader='fixed',tool_answer_first=True);e,ts,p=self.plan(CURRENT)  # no earlier rules
        res={'tool':'eligibility','args':p['args'],'result':E.tool(**p['args']),'tx':'t1','action_tx':None}
        self.assertEqual(ts.lead_final(res),'I cannot decide yet: the budget, deadline and local-only rules are missing or not stated exactly. '
                         'Please tell me the budget, deadline and local-only rules.')
        self.assertEqual(E.answer_action(ts.lead_final(res)),'UNKNOWN')
        none=FULL.replace('Budget 61 euros','Budget 20 euros');e,ts,p=self.plan(none)
        res=dict(res,args=p['args'],result=E.tool(**p['args']));txt=ts.lead_final(res)
        self.assertTrue(txt.startswith('Neither option is eligible. Option A: 45 euros, 7 days, local, not eligible'));self.assertEqual(E.answer_action(txt),'NONE')

if __name__=='__main__':unittest.main()
