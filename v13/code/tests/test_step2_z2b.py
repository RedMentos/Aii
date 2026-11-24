"""WP-Z2b: seed and question patches (scripts/step2_z2b_seeds.py) and the preregistered multi-seed gate."""
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
import step2_z2b_seeds as zb
import step2_z2_timescale as z2

VARIANTS=('b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual')

def run(arm,seed,u,profile=None,wins=True,queried=None):
    ids=[f['id'] for f in z2.FIXTURES]
    profile=profile or {'b1_only':{'option_fields_correct':1.,'rule_fields_correct':0.},'b2_only':{'option_fields_correct':0.,'rule_fields_correct':1.}}
    q=queried if queried is not None else {'offers':120,'with_question':120 if zb.ARMS[arm]['query'] else 0}
    return {'arm':arm,'seed':seed,'paired_tool':{'mean_utility':{v:u.get(v,0.) for v in VARIANTS},'b1_b2_each_win_an_episode':wins},
            'tool_status':'TOOL_UTILITY_FAIL','step2_status':'UTILITY_FAIL','error_profile_tool':profile,'queried_offers':q,
            'episode_utility_tool':{i+':'+v:u.get(v,0.) for i in ids for v in VARIANTS}}

def runs(primary,control=None,**kw):
    control=control or {'prompt_only_dual':.3,'both_exact':.4}
    out={}
    for s in zb.SEEDS:
        out[('CQ',s)]=run('CQ',s,primary,**kw);out[('DQ',s)]=run('DQ',s,control,**kw)
        out[('C',s)]=run('C',s,{'both_exact':.3,'b1_only':.3,'b2_only':.2});out[('D',s)]=run('D',s,{'both_exact':.35,'b2_only':.25})
    return out

class Gate(unittest.TestCase):
    U={'b1_only':.4,'b2_only':.3,'both_exact':.8,'same_policy_dual':.4}
    def test_pass_and_controls(self):
        g=zb.gate(runs(self.U))
        self.assertEqual(g['status'],'Z2B_DIVERGENCE_SUPPORTED',g['checks']);self.assertTrue(g['two_bodies_worth_cost']);self.assertFalse(g['canonical_gate_pass'])
        self.assertEqual(g['secondary']['query_effect_two_body'],'QUERY_HELPS');self.assertEqual(g['secondary']['b2_model_both_exact'],'LFM_B2_BETTER')
        g=zb.gate(runs(self.U,{'prompt_only_dual':.3,'both_exact':.8}))
        self.assertEqual(g['status'],'Z2B_DIVERGENCE_SUPPORTED');self.assertFalse(g['two_bodies_worth_cost']);self.assertTrue(g['cheaper_shared_body_enough'])
    def test_fails(self):
        self.assertFalse(zb.gate(runs(self.U|{'both_exact':.4}))['checks']['combination_beats_best_single'])
        self.assertFalse(zb.gate(runs(self.U,wins=False))['checks']['each_body_wins_an_episode'])
        self.assertFalse(zb.gate(runs(self.U,{'prompt_only_dual':.9,'both_exact':.4}))['checks']['beats_same_model_prompt_only'])
        self.assertFalse(zb.gate(runs(self.U,queried={'offers':120,'with_question':3}))['checks']['arms_did_what_they_say'])
        r=runs(self.U);del r[('DQ',15)];self.assertEqual(zb.gate(r)['status'],'INCOMPLETE')
    def test_one_bad_seed_blocks_pass(self):
        r=runs(self.U);r[('CQ',16)]=run('CQ',16,self.U|{'both_exact':.35})
        self.assertFalse(zb.gate(r)['checks']['combination_beats_best_single'])
    def test_cluster_ci(self):
        ci=zb.cluster_ci([[.1,.1,.1]]*10);self.assertAlmostEqual(ci['mean'],.1);self.assertAlmostEqual(ci['ci95'][0],.1)
        ci=zb.cluster_ci([[1,1,1]]*5+[[-1,-1,-1]]*5);self.assertLess(ci['ci95'][0],0);self.assertGreater(ci['ci95'][1],0)
    def test_reference_band(self):
        ref={'C':{'tool':{'both_exact':.3,'b1_only':.3}},'D':{'tool':{'both_exact':.35}}}
        n=zb.gate(runs(self.U),ref)['noise_vs_z2'];self.assertTrue(n['z2_c_both_exact_inside_seed_band']);self.assertEqual(n['seeds_shared_minus_two_body'],[.04999999999999999,.04999999999999999])

class Arms(unittest.TestCase):
    def test_settings_and_questions(self):
        from v13.config import validate,DEFAULTS
        for a in zb.ARMS:
            for s in zb.SEEDS:validate(DEFAULTS|zb.settings(a,s))
        self.assertEqual(zb.settings('CQ',14),z2.ARMS['C']|{'seed':14});self.assertEqual(zb.settings('DQ',16),z2.ARMS['D']|{'seed':16})
        self.assertNotIn(13,zb.SEEDS)
        text=' '.join(zb.QUESTIONS.values())
        for f in z2.FIXTURES:
            self.assertNotIn(f['id'],text)
            for o in f['oracle']['options']:self.assertNotIn(str(o['cost']),text)

class Patches(unittest.TestCase):
    def test_seed_follows_cfg_only_when_caller_gave_none(self):
        from v13 import runners
        seen=[];orig=runners.LlamaRunner.generate
        runners.LlamaRunner.generate=lambda self,m,c,d,t=None,s=None,seed=13,*a,**k:seen.append(seed) or iter(())
        try:
            fake=SimpleNamespace(run_variant=lambda:None)
            with zb.Patches(fake,False):
                r=SimpleNamespace(cfg={'seed':15})
                list(runners.LlamaRunner.generate(r,[],None,0,64,None));list(runners.LlamaRunner.generate(r,[],None,0,64,None,seed=13))
            list(runners.LlamaRunner.generate(r,[],None,0,64,None))
        finally:runners.LlamaRunner.generate=orig
        self.assertEqual(seen,[15,13,13])
    def test_question_only_on_current_turn(self):
        from v13.runtime import Runtime
        from v13 import cognition
        reply=json.dumps({'summary':'s','quotes':[],'uncertainty':'u','needs_reentry':False})
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                seen=[];r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=lambda m,*a,**k:seen.append(json.loads(m[1]['content'])) or iter([reply])))
                def variant():
                    for role in ('B1_DETAIL','B2_GIST'):r.cognition.offer(role,r.store.event(r.session,'Project Kestrel current.'),0,time.monotonic()+30)
                fake=SimpleNamespace(run_variant=variant)
                with zb.Patches(fake,True) as p:
                    r.cognition.offer('B1_DETAIL',r.store.event(r.session,'Project Kestrel prep.'),0,time.monotonic()+30)
                    fake.run_variant()
                self.assertIs(fake.run_variant,variant);self.assertNotEqual(cognition.Cognition.offer.__name__,'offer_q')
                self.assertNotIn('jef_query',seen[0])
                self.assertEqual(seen[1]['jef_query']['question'],zb.QUESTIONS['B1_DETAIL']);self.assertEqual(seen[2]['jef_query']['question'],zb.QUESTIONS['B2_GIST'])
                self.assertEqual(p.count,{'offers':2,'with_question':2})
                seen.clear()
                with zb.Patches(fake,False) as p:fake.run_variant()
                self.assertTrue(all('jef_query' not in q for q in seen));self.assertEqual(p.count,{'offers':2,'with_question':0})
            finally:r.close()

if __name__=='__main__':unittest.main()
