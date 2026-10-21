"""Thread Q: eligibility tool in the live turn (BOOT decision rule, C3 typed read, earlier exact evidence, C5/IH-H29,
SHADOW agreement, TOOL_RESULT layer, broker correction). No models."""
import json,tempfile,unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import toolstep as T
from v13.agi import hub,eligibility as E
from v13.broker import conflicts,correction_text

PRIOR='Project Mira. Budget 61 euros. Deadline 8 days. Local-only requirement: false.'
CURRENT=('Project Mira. Apply earlier project rules. Option A: cost 45 euros, duration 7 days, local true. Option B: cost 55 euros, '
         'duration 4 days, local false. Compute remaining budget and eligibility; choose cheapest eligible.')
FULL='Project Mira. Budget 61 euros. Deadline 8 days. Local-only requirement: false. '+CURRENT.split('. ',2)[2]
OPTS=[{'entity':'A','cost':45,'days':7,'local':True},{'entity':'B','cost':55,'days':4,'local':False}]
READ={'options':OPTS,'budget':61,'deadline':8,'local_only':False}

class FakeC3:
    def __init__(self,values):self.values=values;self.calls=[]
    def generate(self,messages,cancel,deadline,max_tokens=None,schema=None,**kw):
        self.calls.append((messages,schema));yield json.dumps(self.values)

class Rule(unittest.TestCase):
    def test_question_rule(self):
        self.assertTrue(E.question(CURRENT));self.assertTrue(E.question(FULL))
        self.assertFalse(E.question('Option A or option B, what do you think about the weather?'))
        self.assertFalse(E.question('Budget 61 euros. Which is cheaper?'))
        self.assertFalse(E.question(CURRENT+' '*E.MAX_TEXT))
    def test_args_omit_unavailable_rules_and_join_quotes(self):
        a=E.args_for(dict(READ,budget=None),CURRENT,[PRIOR,'second line\nwrapped'])
        self.assertNotIn('budget',a);self.assertEqual(a['deadline'],8);self.assertEqual(a['quotes'],PRIOR+'\nsecond line wrapped')
        self.assertEqual(E.tool(**a)['action'],'UNKNOWN')
        self.assertEqual(E.tool(**E.args_for(READ,CURRENT,[PRIOR]))['action'],'A')
    def test_answer_parser(self):
        cases={'I recommend Option A.':'A','The cheapest eligible option is B.':'B','Choose option B, it is faster.':'B',
               'Neither option is eligible.':'NONE','The budget is missing, so I cannot decide.':'UNKNOWN',
               'Option A costs 45, option B costs 55.':None,'Option A remains within budget.':'A','':None,
               'Option A is cheaper at 49 euros. Option B exceeds the deadline, so it is not eligible.':'A'}
        for text,want in cases.items():self.assertEqual(E.answer_action(text),want,text)
    def test_decision_line_and_broker(self):
        d=E.tool(**E.args_for(READ,CURRENT,[PRIOR]))
        self.assertEqual(E.decision_line(d),'choose Option A (Option A: remaining budget 16 euros, eligible; Option B: remaining budget 6 euros, eligible)')
        res={'tool':'eligibility','args':{},'result':d,'tx':'t1','action_tx':None}
        self.assertEqual(conflicts('Pick option B.','FINAL',res),['ANSWER_OMITS_TOOL_RESULT'])
        self.assertEqual(conflicts('I recommend Option A (16 euros left).','FINAL',res),[])
        self.assertIn('eligibility: choose Option A',correction_text(res))
        u=E.tool(**E.args_for(dict(READ,budget=None),CURRENT,[]))
        self.assertIn('decision UNKNOWN',E.decision_line(u));self.assertIn('cost 45 euros',E.decision_line(u))
        self.assertEqual(E.answer_sentence(E.args_for(dict(READ,budget=None),CURRENT,[]),u),'I cannot decide yet: the budget, deadline and local-only rules are missing or not stated exactly.')
        a2=E.args_for(dict(READ,budget=None),CURRENT,[PRIOR]);self.assertEqual(E.answer_sentence(a2,E.tool(**a2)),'I cannot decide yet: the budget rule is missing or not stated exactly.')
        self.assertEqual(E.answer_sentence({},{'action':'NONE','options':[]}),'Neither option is eligible.')

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.c3=FakeC3(READ);self.r.pool.get=lambda role:self.c3
        self.r.cfg['eligibility_reader']='c3'  # these tests cover the measured C3 read path; the default fixed reader is tested in test_rule_reader_fixed
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def earlier_turn(self,text):
        s=self.r.store;e=s.event(self.r.session,text)
        with s.tx() as c:c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(self.r.session,e['event_id'],'assistant','Noted.','FINAL',json.dumps({'context_source_refs':[e['source_ref']]}),0))
    def test_disabled_tool_costs_no_model_call(self):
        e=self.r.store.event(self.r.session,FULL);self.assertIsNone(T.ToolStep(self.r).plan(e,FULL));self.assertEqual(self.c3.calls,[])
    def test_enabled_tool_uses_earlier_user_message_as_evidence(self):
        g=hub(self.r);g.tools.enable('eligibility');self.earlier_turn(PRIOR)
        e=self.r.store.event(self.r.session,CURRENT);ts=T.ToolStep(self.r)
        p=ts.plan(e,CURRENT);self.assertEqual((p['tool'],p['proposer']),('eligibility',T.ELIG_PROPOSER));self.assertNotEqual(p['status'],'APPROVED')  # Age 0
        msgs,schema=self.c3.calls[0];self.assertEqual(schema,E.READ_SCHEMA);self.assertIn(PRIOR,msgs[1]['content'])
        self.assertEqual(p['args']['quotes'],PRIOR)
        sh=ts.shadow(e,p);self.assertEqual(sh['result']['action'],'A');self.assertEqual(sh['result']['rejected'],[])
        self.assertTrue(ts.compare(e,sh,'I recommend Option A, 16 euros remain.'));self.assertFalse(ts.compare(e,sh,'Choose option B.'))
        self.assertEqual(self.r.store.state(T.KEY)[0]['tools']['eligibility'],[2,1])
        g.tools._policy=lambda spec,origin,args,confirmed=False:('APPROVED','POLICY',[])
        res=ts.execute(e,p);self.assertEqual(res['result']['action'],'A')
        lay=ts.layer(res);self.assertEqual(lay['answer'],'Choose Option A. Remaining budget: 16 euros.')
        self.assertTrue(lay['details'].startswith('choose Option A'));self.assertNotIn('input',lay)
    def test_without_earlier_rules_the_invented_budget_is_refused(self):
        hub(self.r).tools.enable('eligibility');e=self.r.store.event(self.r.session,CURRENT);ts=T.ToolStep(self.r)
        p=ts.plan(e,CURRENT);self.assertNotIn('quotes',p['args'])
        d=ts.shadow(e,p)['result'];self.assertEqual(d['action'],'UNKNOWN');self.assertIn('budget:not_stated',d['rejected'])
    def test_current_override_beats_earlier_turn(self):
        hub(self.r).tools.enable('eligibility');self.earlier_turn(PRIOR)
        text=CURRENT.replace('Apply earlier project rules.','Apply earlier project rules, but now local-only requirement: true.')
        self.c3.values=dict(READ,local_only=True);e=self.r.store.event(self.r.session,text)
        d=T.ToolStep(self.r).shadow(e,T.ToolStep(self.r).plan(e,text))['result'];self.assertEqual(d['action'],'A')
        self.assertEqual([o['eligible'] for o in d['options']],[True,False])
        self.c3.values=READ;e=self.r.store.event(self.r.session,text)  # reader copies the stale earlier value
        d=T.ToolStep(self.r).shadow(e,T.ToolStep(self.r).plan(e,text))['result'];self.assertEqual(d['action'],'UNKNOWN')
        self.assertIn('local_only:conflicts_current',d['rejected'])
    def test_bad_read_logs_and_proposes_nothing(self):
        hub(self.r).tools.enable('eligibility');self.c3.values=dict(READ,options=OPTS[::-1])
        e=self.r.store.event(self.r.session,FULL);self.assertIsNone(T.ToolStep(self.r).plan(e,FULL))
        self.assertIsNotNone(self.r.store.one("SELECT id FROM telemetry WHERE kind='tool_step_unavailable'"))
    def test_non_decision_text_keeps_old_proposers(self):
        hub(self.r).tools.enable('eligibility');e=self.r.store.event(self.r.session,'What is 12 * 7?')
        p=T.ToolStep(self.r).plan(e,'What is 12 * 7?');self.assertEqual(p['tool'],'calc');self.assertEqual(self.c3.calls,[])

if __name__=='__main__':unittest.main()
