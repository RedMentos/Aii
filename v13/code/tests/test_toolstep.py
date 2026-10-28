"""WP-K rest: TOOL_CALL as live C5 candidate (proposal, IH-H29 policy, shadow agreement, active execution). No models."""
import json,tempfile,unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import toolstep as T
from v13.focal import ActionGate
from v13.agi import hub

class ProposerTests(unittest.TestCase):
    def test_arithmetic_forms_and_non_arithmetic(self):
        self.assertEqual(T.propose('What is 48 times 37?')['args'],{'expression':'48*37'})
        self.assertEqual(T.propose('Calculate 17% of 2,340.')['args'],{'expression':'17/100*2340'})
        self.assertEqual(T.propose('how much is (12+8)*3')['args'],{'expression':'(12+8)*3'})
        self.assertEqual(T.propose('2 to the power of 20')['args'],{'expression':'2**20'})
        for t in ['Hello there','I was born in 1990','Meet on 2026-11-02','My code is 4471','date 12/05/2024']:self.assertIsNone(T.propose(t),t)

    def test_bilingual_half_requires_one_plain_integer_and_explicit_request(self):
        valid={
            'Budget 120 Euro. Berechne die Hälfte.':'120/2',
            'Wie viel ist die Hälfte von 90 Euro?':'90/2',
            'Halbiere 8.':'8/2',
            'What is half of 80?':'80/2',
        }
        for text,expression in valid.items():
            proposal=T.propose(text)
            self.assertIsNotNone(proposal,text)
            self.assertEqual(proposal['tool'],'calc')
            self.assertEqual(proposal['args']['expression'],expression)
            self.assertEqual(text[proposal['span'][0]:proposal['span'][1]],expression.split('/')[0])
        for text in (
            'Berechne nicht die Hälfte von 120',
            'Berechne die Hälfte von 120 und 60',
            '2026-10-28: halbiere 120',
            'Halbiere 1.200',
            'Halbiere -120',
            'Halbiere 120-30',
            'Halbiere 120+30',
            # Excluded second-number spellings must not disappear from the
            # single-operand check and accidentally authorize a proposal.
            'Halbiere 120 und -5.',
            'Halbiere 120 und 1,5.',
            'Halbiere 120 und 1.200.',
            'Halbiere 120 und 2e3.',
            'Halbiere 120 und ١٢.',
            'Calculate half of 120 and -5.',
            'Halbiere ١٢.',
            'Halbiere - 120',
            'Halbiere + 120',
            'Halbiere −120',
            'Halbiere – 120',
            'Halbiere minus 120',
            'Calculate half of negative 80',
            'The budget is 120 Euro.',
        ):
            self.assertIsNone(T.propose(text),text)

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,text):return self.r.store.event(self.r.session,text)

class PolicyTests(Base):
    def test_age0_refuses_system_tool_choice_and_gate_suppresses_with_reason(self):
        e=self.ev('What is 48 times 37?');p=T.ToolStep(self.r).plan(e,'What is 48 times 37?')
        self.assertNotEqual(p['status'],'APPROVED')
        pk=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='ToolProposal' AND event_id=?",(e['event_id'],))['payload'])
        self.assertEqual(pk['truth_authority'],0);self.assertEqual(pk['tool'],'calc')
        c5=ActionGate(self.r.store).select(e,route='detail',direct=False,resource_state='NORMAL',tool=p)
        self.assertNotEqual(c5['role'],'EXTERNAL_TOOL')
        self.assertTrue(any(s['action_id']=='EXTERNAL_TOOL' and s['reason'].startswith('TOOL_POLICY:') for s in c5['suppressed']))
    def test_approved_tool_wins_c5_and_runs_as_transaction(self):
        g=hub(self.r);g.tools.enable('calc')
        e=self.ev('What is 48 times 37?');ts=T.ToolStep(self.r);p=ts.plan(e,'What is 48 times 37?')
        p['status']='APPROVED'  # as if the Age-1 right were granted (age_allows is tested in test_agi)
        c5=ActionGate(self.r.store).select(e,route='detail',direct=False,resource_state='NORMAL',tool=p)
        self.assertEqual(c5['role'],'EXTERNAL_TOOL')
        g.tools._policy=lambda spec,origin,args,confirmed=False:('APPROVED','POLICY',[])
        res=ts.execute(e,p);self.assertEqual(res['result'],1776);self.assertTrue(res['action_tx'])
        self.assertEqual(ts.layer(res)['output'],1776)
        again=ts.execute(e,p);self.assertEqual(again['status'],'DEDUPLICATED')  # idempotent per event
    def test_direct_output_suppresses_tool(self):
        e=self.ev('x');p={'tool':'calc','args':{'expression':'1+1'},'utility':.95,'risk':'READ_LOCAL','status':'APPROVED','reason':'POLICY'}
        c5=ActionGate(self.r.store).select(e,route='simple',direct=True,resource_state='NORMAL',tool=p)
        self.assertEqual(c5['role'],'SOURCE_COPY')

class ShadowTests(Base):
    def test_shadow_computes_pure_tools_only_and_compares(self):
        e=self.ev('What is 48 times 37?');ts=T.ToolStep(self.r);p=ts.plan(e,'What is 48 times 37?')
        sh=ts.shadow(e,p);self.assertEqual(sh['result'],1776)
        self.assertTrue(ts.compare(e,sh,'It is 1,776.'));self.assertFalse(ts.compare(e,sh,'About 1700.'))
        self.assertIsNone(ts.shadow(e,dict(p,risk='WRITE_LOCAL')))
        rep=T.report(self.r.store);self.assertEqual(rep['shadow_compared'],2);self.assertEqual(rep['shadow_agreement'],.5)
    def test_german_half_age0_remains_shadow_and_generic_answer_disagrees(self):
        text='Budget 120 Euro. Berechne die Hälfte.'
        e=self.ev(text);ts=T.ToolStep(self.r);p=ts.plan(e,text)
        self.assertEqual(p['tool'],'calc')
        self.assertEqual(p['args'],{'expression':'120/2'})
        self.assertNotEqual(p['status'],'APPROVED')
        c5=ActionGate(self.r.store).select(e,route='detail',direct=False,resource_state='NORMAL',tool=p)
        self.assertNotEqual(c5['role'],'EXTERNAL_TOOL')
        shadow=ts.shadow(e,p)
        self.assertEqual(shadow['result'],60)
        self.assertFalse(ts.compare(e,shadow,'The calculation yields the requested amount based on the given value.'))
        self.assertTrue(ts.compare(e,shadow,'The half is 60 Euro.'))

    def test_live_turn_plans_tool_without_errors(self):
        e=self.ev('Copy exactly: 2+2');self.r._turn(e)  # direct path: no proposal
        self.assertIsNone(self.r.store.one("SELECT id FROM packets WHERE kind='ToolProposal' AND event_id=?",(e['event_id'],)))
        self.assertIsNone(self.r.store.one("SELECT id FROM telemetry WHERE kind='tool_step_unavailable'"))

if __name__=='__main__':unittest.main()
