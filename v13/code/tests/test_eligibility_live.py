"""Eligibility tool in the live ToolStep path (STEP2 follow-up 2026-10-21): BOOT wording rule, model read only after the
user enabled the tool, offer quotes as evidence, Age-0 shadow + agreement, readable TOOL_RESULT layer. No models."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from v13.agi import eligibility as E, hub
from v13.runtime import Runtime
from v13 import toolstep

CURRENT=('Project Borealis. Decide from the earlier project rules. Option A: cost 55 euros, duration 5 days, local true. '
         'Option B: cost 65 euros, duration 3 days, local true. Compute each remaining budget and eligibility; choose cheapest eligible.')
PRIOR='Project Borealis. Budget 90 euros. Deadline 4 days. Local-only requirement: true.'
EXTRACT={'project':'Borealis','options':[{'entity':'A','cost':55,'days':5,'local':True},{'entity':'B','cost':65,'days':3,'local':True}],
         'budget':90,'deadline':4,'local_only':True}

class Wording(unittest.TestCase):
    def test_boot_rule(self):
        self.assertTrue(E.asks(CURRENT))
        for t in ('Which option is cheaper, A or B?','Option A costs 5. Option B costs 6.','What is 2+2?','x'*5000):self.assertFalse(E.asks(t))
    def test_args_omit_unavailable_rules_and_label_is_readable(self):
        a=E.args_from(dict(EXTRACT,budget=None),CURRENT,[PRIOR]);self.assertNotIn('budget',a);self.assertEqual(a['quotes'],PRIOR)
        r=E.tool(**E.args_from(EXTRACT,CURRENT,[PRIOR]));self.assertEqual(r['action'],'B')
        self.assertEqual(E.label(r),'choose option B; option A: remaining 35, not eligible; option B: remaining 25, eligible')
        self.assertTrue(E.label(E.tool(**a)).startswith('UNKNOWN'))

class LivePath(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.calls=[]
        def generate(messages,*a,**k):
            self.calls.append(messages);return iter([json.dumps(EXTRACT)])
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=generate))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def event_with_offer(self,text):
        e=self.r.store.event(self.r.session,text)
        reply=json.dumps({'summary':'s','quotes':['Budget 90 euros. Deadline 4 days. Local-only requirement: true.'],'uncertainty':'u','needs_reentry':False})
        pool=self.r.pool.get;self.r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=lambda *a,**k:iter([reply])))
        self.r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30);self.r.pool.get=pool
        return e
    def test_not_enabled_means_no_model_call(self):
        e=self.event_with_offer(PRIOR+' '+CURRENT)
        self.assertIsNone(toolstep.ToolStep(self.r).plan(e,CURRENT));self.assertEqual(self.calls,[])
    def test_enabled_proposal_uses_offer_quotes_and_shadows_at_age0(self):
        hub(self.r).tools.enable('eligibility');e=self.event_with_offer(PRIOR+' '+CURRENT);ts=toolstep.ToolStep(self.r)
        p=ts.plan(e,CURRENT)
        self.assertEqual((p['tool'],p['proposer']),('eligibility',E.LIVE_PROPOSER))
        self.assertEqual(p['args']['quotes'],'Budget 90 euros. Deadline 4 days. Local-only requirement: true.')
        user=json.loads(self.calls[0][1]['content']);self.assertEqual(user['verified_quotes'],['Budget 90 euros. Deadline 4 days. Local-only requirement: true.'])
        self.assertEqual(p['status'],'DENIED');self.assertTrue(p['reason'].startswith('AGE_RIGHT'))  # Age 0: own tool choice not yet allowed
        sh=ts.shadow(e,p);self.assertEqual(sh['result']['action'],'B')
        self.assertTrue(ts.compare(e,sh,'Choose option B: it stays within budget and deadline.'))
        self.assertFalse(ts.compare(e,sh,'Option A is the cheapest.'))
        part=dict(p['args'],quotes='Budget 90 euros. Deadline 4 days.')  # local-only rule not in evidence -> refuse
        self.assertEqual(E.tool(**part)['action'],'UNKNOWN')
    def test_earlier_user_turn_is_evidence_but_assistant_text_is_not(self):
        from v13.history import native_history
        hub(self.r).tools.enable('eligibility');ts=toolstep.ToolStep(self.r)
        e0=self.r.store.event(self.r.session,PRIOR)  # store.event writes the user message itself
        a=self.r.store.message(self.r.session,e0['event_id'],'assistant');self.r.store.append_message(a,'Budget 999 euros. Deadline 99 days.');self.r.store.finish_message(a,'FINAL',{'direct_source_copy':True})
        e=self.r.store.event(self.r.session,CURRENT)
        self.assertEqual(len(native_history(self.r.store,self.r.session,e['event_id'],self.r.cfg['history_turns'])[0]),2)
        self.assertEqual(ts.user_turns(e),[PRIOR])  # the assistant's 'Budget 999 euros' never becomes evidence
        self.r.cfg['history_turns']=0;self.assertEqual(ts.user_turns(e),[])
    def test_layer_for_an_executed_call(self):
        ts=toolstep.ToolStep(self.r);res=E.tool(**E.args_from(EXTRACT,CURRENT,[PRIOR]))
        layer=ts.layer({'tool':'eligibility','args':{},'result':res,'action_tx':None,'tx':'tool_x'})
        self.assertEqual(layer['action'],'B');self.assertIn('remaining 25',layer['decision']);self.assertEqual(layer['transaction'],'tool_x')

if __name__=='__main__':unittest.main()
