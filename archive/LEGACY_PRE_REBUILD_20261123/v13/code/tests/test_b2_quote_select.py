"""b2_quote_select (WP-Z2c, 2026-10-21): off = previous B2 quote path, anchor = paraphrase -> exact source sentences, pointer = numbered exact sentences."""
import json
from pathlib import Path
import sys
import time
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
from v13.cognition import anchor_span,quote_choices

RULE='Project Kestrel kickoff notes. Budget 100 euros. Deadline 5 days. Local-only requirement: true.'
TASK='Project Kestrel. Decide between Option A and Option B, using the earlier project rules. Compute each remaining budget.'
SHEET='Project Kestrel supplier data sheet. Option A: cost 40 euros, duration 2 days, local true.'

def text(sources,hit):return sources[hit[0]][hit[1]:hit[2]]

class Anchor(unittest.TestCase):
    S=[TASK,RULE,SHEET]
    def test_paraphrase_points_at_the_rule_sentences(self):
        self.assertEqual(text(self.S,anchor_span('Project Kestrel has a budget of 100 euros',self.S)),'Project Kestrel kickoff notes. Budget 100 euros.')
        self.assertEqual(text(self.S,anchor_span('Project Kestel kickoff notes. Budget 100 euros. Deadline 5 days. Local-only requirement:.',self.S)),
                         'Budget 100 euros. Deadline 5 days. Local-only requirement: true.')
    def test_never_anchors_a_number_the_source_lacks(self):
        for q in ('Project Kestrel has a budget of 90 euros','Project Kestrel has a budget of 100 euros and a deadline of 5,00'):self.assertIsNone(anchor_span(q,self.S))
    def test_short_or_loose_or_tied_quotes_are_dropped(self):
        self.assertIsNone(anchor_span('budget',self.S));self.assertIsNone(anchor_span(None,self.S))
        self.assertIsNone(anchor_span('Kestrel remote vendor weather forecast summary',self.S))
        self.assertIsNone(anchor_span('Budget 100 euros noted',['Budget 100 euros. Other.','Budget 100 euros. Else.']))  # equal cover in two sources
    def test_choices_are_exact_sentences_in_source_order(self):
        c=quote_choices([TASK,RULE]);self.assertEqual([text([TASK,RULE],x) for x in c[:3]],['Project Kestrel.','Decide between Option A and Option B, using the earlier project rules.','Compute each remaining budget.'])
        self.assertEqual(text([TASK,RULE],c[3]),'Project Kestrel kickoff notes.');self.assertEqual(len(quote_choices([RULE]*10)),24)

class OfferPath(unittest.TestCase):
    def offer(self,r,mode,reply):
        r.cfg['b2_quote_select']=mode;r.cfg['offer_quote_context_chars']=200;seen={}
        def generate(messages,cancel,deadline,tokens,schema,*a,**k):
            seen['query']=json.loads(messages[1]['content']);seen['schema']=schema;return iter([json.dumps(reply)])
        r.pool.get=Mock(return_value=SimpleNamespace(role='B2_GIST',last_metrics={},generate=generate))
        e=r.store.event(r.session,TASK+' '+RULE);p=r.cognition.offer('B2_GIST',e,0,time.monotonic()+30)
        return p,[r.store.read_source(x) for x in p['evidence_refs']],seen
    def run_mode(self,mode,reply):
        from v13.runtime import Runtime
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:return self.offer(r,mode,reply)
            finally:r.close()
    def test_off_anchor_pointer(self):
        para={'summary':'s','quotes':['Project Kestrel has a budget of 100 euros'],'uncertainty':'u','needs_reentry':False}
        p,ev,seen=self.run_mode('off',para)
        self.assertEqual((ev,p['rejected_quotes']),([],1));self.assertNotIn('b2_quote_select',p);self.assertNotIn('quote_choices',seen['query'])
        self.assertEqual(seen['schema']['properties']['quotes']['items']['type'],'string')
        p,ev,seen=self.run_mode('anchor',para)
        self.assertEqual(p['rejected_quotes'],0);self.assertEqual(len(ev),1);self.assertIn(RULE,ev[0]);self.assertEqual(p['b2_quote_select']['anchored'],1)
        self.assertEqual(p['b2_quote_select']['raw_quotes'],para['quotes']);self.assertEqual(p['offer']['quotes'],['Project Kestrel kickoff notes. Budget 100 euros.'])
        self.assertNotIn('quote_choices',seen['query'])
        p,ev,seen=self.run_mode('pointer',para|{'quotes':[5,99]})
        ch=seen['query']['quote_choices'];self.assertEqual(ch[4]['text'],'Budget 100 euros.')
        self.assertEqual(seen['schema']['properties']['quotes']['items']['enum'],list(range(1,len(ch)+1)))
        self.assertEqual(p['b2_quote_select']['picked'],[5]);self.assertIn(RULE,ev[0]);self.assertEqual(p['offer']['quotes'],['Budget 100 euros.'])
    def test_b1_is_never_touched(self):
        from v13.runtime import Runtime
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                r.cfg['b2_quote_select']='pointer';seen={}
                def generate(messages,cancel,deadline,tokens,schema,*a,**k):seen['q']=json.loads(messages[1]['content']);return iter([json.dumps({'summary':'s','quotes':['Budget 100 euros.'],'uncertainty':'u','needs_reentry':False})])
                r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=generate))
                e=r.store.event(r.session,RULE);p=r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30)
                self.assertNotIn('quote_choices',seen['q']);self.assertNotIn('b2_quote_select',p)
            finally:r.close()
    def test_config_and_chain_link(self):
        from v13.config import validate,DEFAULTS
        for ok in ('off','anchor','pointer'):validate(DEFAULTS|{'b2_quote_select':ok})
        for bad in ('on',True,1,None):
            with self.assertRaises(ValueError):validate(DEFAULTS|{'b2_quote_select':bad})
        import integrated_candidates as ic, source_handoff_candidate as sh
        live=(ROOT/'v13/cognition.py').read_text()
        baseline,changed=sh.sources();self.assertIn(live,(baseline['v13/cognition.py'],changed['v13/cognition.py']))
        with self.assertRaises(ValueError):ic.b2_quote_select(live)
        self.assertIn('b2_quote_select',ic.INTEGRATED)

class Gate(unittest.TestCase):
    def runs(self,rate,wrong=0,picked=5):
        import step2_z2c_b2_rule as z
        out={}
        for arm in z.ARMS:
            for s in z.SEEDS:
                rr={f'{fid}:{v}':{'rules':i<round(rate[arm]*4),'wrong_rule':False} for fid in z.RULE_EPISODES for i,v in enumerate(z.B2_VARIANTS)}
                u={'both_exact':.6,'b1_only':.5,'b2_only':.3}
                out[(arm,s)]={'z2c':{'b2_rule_rows':rr,'b2_rule_rate':rate[arm],'b2_wrong_rule_rows':wrong if arm=='CQA' else 0,'wrong_committed_tool':0,
                                     'b2_offers':{'anchored_quotes':picked,'picked_ids':picked},'b2_prompt_tokens':[500]},
                              'tool_status':'TOOL_UTILITY_FAIL','step2_status':'UTILITY_FAIL','queried_offers':{'offers':60,'with_question':60},
                              'paired_tool':{'mean_utility':u},'episode_utility_tool':{f['id']+':'+v:u[v] for f in z.z2.FIXTURES for v in u},'split_exact_tool':{'both_exact':[]}}
        return out
    def test_fixed_partial_unsafe(self):
        import step2_z2c_b2_rule as z
        g=z.gate(self.runs({'CQ':.25,'CQA':.75,'CQP':.5}))
        self.assertEqual(g['variants']['CQA']['status'],'B2_RULE_QUOTE_FIXED');self.assertEqual(g['variants']['CQP']['status'],'B2_RULE_QUOTE_IMPROVED_PARTIAL')
        self.assertEqual(g['status'],'Z2C_B2_RULE_QUOTE_FIXED');self.assertFalse(g['canonical_gate_pass'])
        self.assertEqual(z.gate(self.runs({'CQ':.25,'CQA':.75,'CQP':.25},wrong=1))['variants']['CQA']['status'],'B2_RULE_QUOTE_UNSAFE_OR_INVALID')
        self.assertEqual(z.gate(self.runs({'CQ':.25,'CQA':.75,'CQP':.25},picked=0))['variants']['CQA']['status'],'B2_RULE_QUOTE_UNSAFE_OR_INVALID')
        self.assertEqual(z.gate(self.runs({'CQ':.25,'CQA':.25,'CQP':.25}))['status'],'Z2C_B2_RULE_QUOTE_NOT_FIXED')
        self.assertEqual(z.gate({})['status'],'INCOMPLETE')
    def test_control_settings_unchanged_from_z2b(self):
        import step2_z2c_b2_rule as z
        self.assertEqual(z.settings('CQ',17),z.z2.ARMS['C']|{'seed':17})
        self.assertEqual(z.settings('CQA',17),z.z2.ARMS['C']|{'seed':17,'b2_quote_select':'anchor'})
        self.assertEqual(z.rule_values('Budget 90 euros. Deadline 4 days. Local-only requirement: false.'),[('budget',90),('deadline',4),('local_only',False)])

if __name__=='__main__':unittest.main()
