"""2026-10-21 user decision: rules are read and checked by a fixed, non-generative component (eligibility.fixed_read), never
by a language model; the quote help (pointer + widened quotes) and the rule-scoped body questions are on by default."""
import json,tempfile,unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import toolstep as T
from v13.agi import hub,eligibility as E
from v13.config import DEFAULTS,validate
from v13.cognition import asks_rule_decision

PRIOR='Project Mira. Budget 61 euros. Deadline 8 days. Local-only requirement: false.'
NEWER='Project Mira update. Budget 50 euros.'
CURRENT=('Project Mira. Apply earlier project rules. Option A: cost 45 euros, duration 7 days, local true. Option B: cost 55 euros, '
         'duration 4 days, local false. Compute remaining budget and eligibility; choose cheapest eligible.')

class NoModel:
    def generate(self,*a,**k):raise AssertionError('a language model was asked to read rules')

class Reader(unittest.TestCase):
    def test_reads_canonical_rules_and_options(self):
        v=E.fixed_read(CURRENT,[PRIOR])
        self.assertEqual((v['budget'],v['deadline'],v['local_only']),(61,8,False))
        self.assertEqual(v['options'],[{'entity':'A','cost':45,'days':7,'local':True},{'entity':'B','cost':55,'days':4,'local':False}])
        self.assertEqual(E.tool(**E.args_for(v,CURRENT,[PRIOR]))['action'],'A')
    def test_newest_statement_wins(self):
        v=E.fixed_read(CURRENT,[PRIOR,NEWER]);self.assertEqual(v['budget'],50)
        v=E.fixed_read(CURRENT+' Budget 40 euros.',[PRIOR,NEWER]);self.assertEqual(v['budget'],40)
        self.assertEqual(E.tool(**E.args_for(v,CURRENT+' Budget 40 euros.',[PRIOR,NEWER]))['action'],'NONE')
    def test_two_values_in_one_text_are_not_guessed(self):
        v=E.fixed_read(CURRENT,['Budget 61 euros. Budget 70 euros. Deadline 8 days. Local-only requirement: false.'])
        self.assertIsNone(v['budget']);self.assertEqual(E.tool(**E.args_for(v,CURRENT,[]))['action'],'UNKNOWN')
    def test_disagreeing_quotes_stay_unknown(self):
        v=E.fixed_read(CURRENT,[],['Budget 61 euros.','Budget 80 euros.']);self.assertIsNone(v['budget'])
        v=E.fixed_read(CURRENT,[],['Budget 61 euros.','Budget 61 euros. Deadline 8 days.']);self.assertEqual((v['budget'],v['deadline']),(61,8))
    def test_history_beats_quotes(self):
        v=E.fixed_read(CURRENT,[NEWER],['Budget 61 euros.']);self.assertEqual(v['budget'],50)
    def test_reworded_rule_is_not_invented(self):
        v=E.fixed_read(CURRENT,['We can spend at most 61 euros and need it within 8 days.'])
        self.assertEqual((v['budget'],v['deadline'],v['local_only']),(None,None,None))
    def test_missing_option_value_refuses(self):
        with self.assertRaises(ValueError):E.fixed_read('Option A: cost 45 euros. Option B: cost 55 euros, duration 4 days, local false. Choose.',[PRIOR])

class Defaults(unittest.TestCase):
    def test_quote_help_and_fixed_reader_on(self):
        validate(DEFAULTS)
        self.assertEqual((DEFAULTS['b2_quote_select'],DEFAULTS['offer_quote_context_chars'],DEFAULTS['eligibility_reader'],DEFAULTS['body_question_scope']),('pointer',200,'fixed','rule_decision'))
        self.assertTrue(DEFAULTS['body_question_b1'] and DEFAULTS['body_question_b2'])
        for key,bad in (('body_question_scope','sometimes'),('eligibility_reader','gpt')):
            with self.assertRaises(ValueError):validate(DEFAULTS|{key:bad})
    def test_rule_scope(self):
        self.assertTrue(asks_rule_decision(CURRENT));self.assertFalse(asks_rule_decision('Tell me about the weather in Mira.'))

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.r.pool.get=lambda role:NoModel()
        self.r.cfg['eligibility_reader']='fixed_strict'  # 21.10. reader (no model at all); default 'fixed' = 22.10. reader, tested in test_eligibility_fixed
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def earlier_turn(self,text):
        s=self.r.store;e=s.event(self.r.session,text)
        with s.tx() as c:c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(self.r.session,e['event_id'],'assistant','Noted.','FINAL',json.dumps({'context_source_refs':[e['source_ref']]}),0))
    def test_live_plan_reads_without_any_model(self):
        self.assertEqual(self.r.cfg['eligibility_reader'],'fixed_strict')
        hub(self.r).tools.enable('eligibility');self.earlier_turn(PRIOR);self.earlier_turn(NEWER)
        e=self.r.store.event(self.r.session,CURRENT);ts=T.ToolStep(self.r)
        p=ts.plan(e,CURRENT);self.assertEqual(p['tool'],'eligibility');self.assertEqual(p['args']['budget'],50)
        self.assertEqual(ts.shadow(e,p)['result']['action'],'A')
    def test_unstated_rules_give_unknown_not_a_guess(self):
        hub(self.r).tools.enable('eligibility');e=self.r.store.event(self.r.session,CURRENT);ts=T.ToolStep(self.r)
        p=ts.plan(e,CURRENT);self.assertNotIn('budget',p['args']);self.assertEqual(ts.shadow(e,p)['result']['action'],'UNKNOWN')

if __name__=='__main__':unittest.main()
