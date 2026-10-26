"""WP-Z2: b1_recent_source_chars (off = live) and the STEP2 timescale-split fixtures/gate (scripts/step2_z2_timescale.py)."""
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import step2_z2_timescale as z
from v13.agi import eligibility as E

SHEET=z.sheet('Kestrel',(40,2,True),(70,7,False))

class Fixtures(unittest.TestCase):
    def test_information_sits_where_preregistered(self):
        self.assertEqual(len(z.FIXTURES),10);self.assertEqual(len({f['id'] for f in z.FIXTURES}),10)
        for f in z.FIXTURES:
            rules_text=' '.join(f['history']+[f['current']])
            for k,v in f['rules'].items():self.assertTrue(E.stated(k,v,rules_text),f['id'])
            for k,v in f['rules'].items():self.assertEqual(E.stated(k,v,f['current']),f['type']=='DETAIL',f['id']+k)
            opts=f['oracle']['options']
            self.assertEqual(all(E.option_stated(o,[f['current']]) for o in opts),f['type']=='RULE',f['id'])
            if f['type']!='RULE':
                recent=f['history'][2];i=recent.index('Option A')
                self.assertGreater(i,z.B2_EXCERPT_CHARS);self.assertLessEqual(len(recent),600)  # outside B2 excerpt, inside B1 window
                self.assertFalse(any(E.option_stated(o,[recent[:z.B2_EXCERPT_CHARS]]) for o in opts))
                self.assertTrue(all(E.option_stated(o,[recent]) for o in opts))
            self.assertIn('Project '+f['id'],f['history'][2])
    def test_oracle_matches_recipe_and_is_never_unknown(self):
        actions=[f['oracle']['action'] for f in z.FIXTURES]
        self.assertNotIn('UNKNOWN',actions);self.assertTrue({'A','B','NONE'}<=set(actions))
        self.assertEqual([f['type'] for f in z.FIXTURES].count('SPLIT'),6)
    def test_arms(self):
        from v13.config import validate,DEFAULTS
        for arm in z.ARMS.values():validate(DEFAULTS|arm)
        self.assertEqual(z.ARMS['C']['b2_control'],'two_body');self.assertEqual(z.ARMS['D']['b2_control'],'shared_body_dual_state')
        self.assertEqual({k:v for k,v in z.ARMS['C'].items() if k!='b2_control'},{k:v for k,v in z.ARMS['D'].items() if k!='b2_control'})
        for bad in (-1,961,True,'600'):
            with self.assertRaises(ValueError):validate(DEFAULTS|{'b1_recent_source_chars':bad})
    def test_harness_copy_leaves_frozen_module_alone(self):
        import integration_step2_utility as frozen
        m=z.harness();self.assertIs(m.FIXTURES,z.FIXTURES);self.assertIsNot(frozen.FIXTURES,z.FIXTURES)
        self.assertNotEqual(m.prepare_base,frozen.prepare_base)
    def test_chain_link_applied_exactly_once(self):
        import integrated_candidates as ic, source_handoff_candidate as sh
        live=(ROOT/'v13/cognition.py').read_text()
        baseline,changed=sh.sources();self.assertIn(live,(baseline['v13/cognition.py'],changed['v13/cognition.py']))
        with self.assertRaises(ValueError):ic.b1_recent(live)
        self.assertIn('b1_recent',ic.INTEGRATED)

def summary(u,ud,b1opt=1.,b2opt=0.,b1rule=0.,b2rule=1.,wins=True):
    return {'C':{'paired_tool':{'mean_utility':u,'b1_b2_each_win_an_episode':wins},'tool_status':'TOOL_UTILITY_FAIL','step2_status':'UTILITY_FAIL',
                 'error_profile_tool':{'b1_only':{'option_fields_correct':b1opt,'rule_fields_correct':b1rule},'b2_only':{'option_fields_correct':b2opt,'rule_fields_correct':b2rule}}},
            'D':{'paired_tool':{'mean_utility':ud},'tool_status':'TOOL_UTILITY_FAIL','step2_status':'UTILITY_FAIL'}}

class Gate(unittest.TestCase):
    U={'b1_only':.5,'b2_only':.4,'both_exact':.8,'same_policy_dual':.5}
    def test_pass_needs_every_check(self):
        g=z.gate(summary(self.U,{'prompt_only_dual':.4,'both_exact':.6}))
        self.assertEqual(g['status'],'Z2_DIVERGENCE_SUPPORTED');self.assertTrue(g['two_bodies_worth_cost']);self.assertFalse(g['canonical_gate_pass'])
    def test_shared_body_equal_means_cheaper_form_allowed(self):
        g=z.gate(summary(self.U,{'prompt_only_dual':.4,'both_exact':.8}))
        self.assertEqual(g['status'],'Z2_DIVERGENCE_SUPPORTED');self.assertFalse(g['two_bodies_worth_cost']);self.assertTrue(g['cheaper_shared_body_enough'])
    def test_fails(self):
        D={'prompt_only_dual':.4,'both_exact':.6}
        self.assertFalse(z.gate(summary(self.U|{'both_exact':.5},D))['checks']['combination_beats_best_single'])
        self.assertFalse(z.gate(summary(self.U,D,wins=False))['checks']['each_body_wins_an_episode'])
        self.assertFalse(z.gate(summary(self.U,D,b2opt=.9))['checks']['complementary_error_profiles'])
        self.assertFalse(z.gate(summary(self.U,{'prompt_only_dual':.9,'both_exact':.6}))['checks']['beats_same_model_prompt_only'])
        self.assertEqual(z.gate({'C':summary(self.U,D)['C']})['status'],'INCOMPLETE')

class B1RecentWindow(unittest.TestCase):
    def offer(self,r,text,quotes):
        reply=json.dumps({'summary':'s','quotes':quotes,'uncertainty':'u','needs_reentry':False});seen=[]
        def gen(messages,*a,**k):seen.append(messages);return iter([reply])
        r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=gen))
        e=r.store.event(r.session,text);return r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30),json.loads(seen[0][1]['content']),seen[0][0]['content']
    def test_off_is_live_and_on_gives_exact_recent_source(self):
        from v13.runtime import Runtime
        q='Option A: cost 40 euros, duration 2 days, local true. Option B: cost 70 euros, duration 7 days, local false.'
        cur='Project Kestrel. Decide between Option A and Option B from the latest supplier data sheet.'
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            from v13.config import LEGACY_PRE_20261022;r.cfg.update(LEGACY_PRE_20261022)  # exact-quote path; widened quotes (default since 22.10.) are tested in test_quote_context
            try:
                self.offer(r,SHEET,[])
                p,query,instr=self.offer(r,cur,[q])
                self.assertNotIn('recent_source',query);self.assertEqual(p['evidence_refs'],[]);self.assertEqual(p['context_source_refs'],[])
                self.assertNotIn('recent_source',instr)
                r.cfg['b1_recent_source_chars']=600
                self.offer(r,SHEET,[])
                p,query,instr=self.offer(r,cur,[q])
                self.assertEqual(query['recent_source'],[{'exact_source_excerpt':SHEET,'authority':'RECENT_SOURCE_NOT_FACT'}])
                self.assertEqual([r.store.read_source(x) for x in p['evidence_refs']],[q]);self.assertEqual(len(p['context_source_refs']),1)
                self.assertIn('recent_source',instr)
                r.cfg['b1_recent_source_chars']=100
                self.offer(r,SHEET,[])
                p,query,_=self.offer(r,cur,[q])
                self.assertEqual(query['recent_source'][0]['exact_source_excerpt'],SHEET[:100]);self.assertEqual(p['evidence_refs'],[])  # outside the window: rejected
                r.cfg['b1_recent_source_chars']=600
                self.offer(r,SHEET,[])
                p,query,_=self.offer(r,'Project Zenith. Unrelated meeting tomorrow.',[])
                self.assertNotIn('recent_source',query)  # other topic: no recent source
            finally:r.close()

if __name__=='__main__':unittest.main()
