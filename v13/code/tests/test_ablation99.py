"""WP-AB §99 ablations: harness wiring and mechanism-level properties on short synthetic streams (no model)."""
from pathlib import Path
import tempfile
import unittest
from v13 import ablation99 as A

class Ablation99Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def rows(self,seed=13,T=200):
        store,_=A._store(self.base/'c');r=A.record_gates(A.credit_stream(seed,T),store);store.close();return r
    def test_streams_are_open_loop_and_reproducible(self):
        a,b=A.credit_stream(5,120),A.credit_stream(5,120)
        self.assertEqual([(r['path'],r['y']) for r in a],[(r['path'],r['y']) for r in b])
        self.assertEqual(A.proc_stream(5,50),A.proc_stream(5,50));self.assertEqual(A.age_stream(5)[:20],A.age_stream(5)[:20])
    def test_safety_veto_closes_the_real_gate_and_controls_keep_it(self):
        rows=self.rows();unsafe=[i for i,r in enumerate(rows) if r['signal'].get('safety_veto')]
        self.assertTrue(unsafe)
        for arm in ('v13','v13_datamix','recency_only','scalar_reward','human_only','outcome_only'):
            f=A.factors(rows,arm,__import__('random').Random(1))
            self.assertTrue(all(f[i]==0. for i in unsafe),arm)
        self.assertTrue(all(x==1. for x in A.factors(rows,'gradient_only',None)))
    def test_budget_matched_controls_spend_the_v13_budget(self):
        rows=self.rows();import random
        v=A._mean(A.factors(rows,'v13',None))
        self.assertAlmostEqual(A._mean(A.factors(rows,'gradient_only_matched',None)),v,6)
        self.assertAlmostEqual(A._mean(A.factors(rows,'random_mask',random.Random(3))),v,delta=.1)
    def test_data_mix_keeps_dream_and_self_rows_within_quota(self):
        rows=self.rows(T=400);f=A.factors(rows,'v13_datamix',None)
        kept=[r for r,x in zip(rows,f) if x>0 or r['gate']['veto']];dream=sum(r['signal']['source_class']=='dream' for r in kept)
        own=sum(r['signal']['source_class'] in ('dream','internal_crosscheck') for r in kept)
        self.assertLessEqual(dream/len(kept),.05+1e-9);self.assertLessEqual(own/len(kept),.10+1e-9)
    def test_typed_modulators_scale_dream_rows_below_scalar_reward(self):
        rows=self.rows(T=300);v=A.factors(rows,'v13',None);s=A.factors(rows,'scalar_reward',None)
        human=A.factors(rows,'human_only',None);route=[i for i,r in enumerate(rows) if r['path']=='route']
        self.assertLess(A._mean([human[i] for i in route]),A._mean([v[i] for i in route]))  # human-only starves outcome-driven paths
        self.assertGreaterEqual(A._mean(s),A._mean(v)-1e-9)
    def test_proceduralization_v13_is_cheaper_than_deliberation_and_safer_than_static(self):
        st=A.proc_stream(13,300)
        v=A.run_proc(st,'v13',self.base/'p');full=A.run_proc(st,'full_deliberation');static=A.run_proc(st,'static_shortcut')
        self.assertEqual(full['fast_path_share'],0.);self.assertLess(v['cost_per_turn'],full['cost_per_turn'])
        self.assertLess(v['error_after_drift'],static['error_after_drift']);self.assertLess(v['salient_error'],static['salient_error'])
    def test_age_arms_use_their_plasticity(self):
        st=A.age_stream(13)[:300]
        self.assertEqual(A.run_age(st,'fixed_conservative')['mean_plasticity']['learn'],.45)
        a=A.run_age(st,'age',self.base/'a');self.assertLess(a['mean_plasticity']['learn'],1.);self.assertIsNotNone(a['max_stage'])
    def test_stable_reopen_policy_holds_plasticity_after_demotion_until_errors_persist(self):
        from v13.age import AgeControl,PERSISTENT_ERRORS
        good={'experience':10000,'competence':.95,'stability':.95,'retention':.98,'calibration':.9,'memory_health':.97,'safe_self_control':.999,'regression_pass':True}
        out={}
        for pol in ('boot','stable_reopen'):
            store,cfg=A._store(self.base/pol);cfg['user_stage_cap']=5;cfg['age_plasticity_policy']=pol;a=AgeControl(store,cfg,build_ceiling=5)
            for i in range(3):a.record('language',good,evidence_id=pol+'g'+str(i))
            before=a.plasticity('language')
            for i in range(2):a.record('language',good|{'competence':.3,'regression_pass':False},evidence_id=pol+'b'+str(i))
            out[pol]=(before,a.plasticity('language'),a.plasticity('language',repeated_errors=PERSISTENT_ERRORS),a.plasticity('language',repeated_errors=1),a.state()[0]['capabilities']['language']['stage'])
            store.close()
        self.assertEqual(out['boot'][4],0);self.assertGreater(out['boot'][1],out['boot'][0])  # BOOT: demotion raises plasticity
        self.assertEqual(out['stable_reopen'][4],0);self.assertLessEqual(out['stable_reopen'][1],out['stable_reopen'][0]+1e-9)
        self.assertGreater(out['stable_reopen'][2],out['stable_reopen'][1])  # persistent errors release the hold
        self.assertEqual(out['stable_reopen'][3],out['stable_reopen'][1])   # a single failure does not reopen
    def test_run_all_reports_every_arm(self):
        r=A.run_all(seeds=(13,),T=120,N=120,workdir=self.base/'all')
        self.assertEqual(set(r['eligibility']['summary']),set(A.ELIG_ARMS));self.assertEqual(set(r['modulators']['summary']),set(A.MOD_ARMS))
        self.assertEqual(set(r['age']['summary']),set(A.AGE_ARMS));self.assertIn('claim_limit',r)

if __name__=='__main__':unittest.main()

class AgeNoiseAware(unittest.TestCase):
    """noise_aware: fails inside the measured noise band neither demote nor reopen; a real drop still demotes."""
    def test_noise_band_blocks_demotion_but_not_real_drop(self):
        import tempfile
        from pathlib import Path
        from v13.age import AgeControl
        with tempfile.TemporaryDirectory() as t:
            store,cfg=A._store(Path(t));cfg['user_stage_cap']=5;cfg['age_plasticity_policy']='noise_aware';a=AgeControl(store,cfg,build_ceiling=5)
            good={'experience':10**6,'competence':.9,'stability':.95,'retention':.95,'calibration':.9,'memory_health':.99,'safe_self_control':.999,'regression_pass':True}
            for i in range(12):a.record('language',good|{'competence':.9+(.04 if i%2 else -.04)},evidence_id='g'+str(i))
            st=a.state()[0]['capabilities']['language'];stage=st['stage'];self.assertGreater(stage,0);self.assertGreater(st['noise']['mad'],.01)
            p0=a.plasticity('language');self.assertLess(p0,AgeControl(store,cfg|{'age_plasticity_policy':'boot'},build_ceiling=5).plasticity('language'))
            for i in range(3):self.assertEqual(a.record('language',good|{'competence':.86,'regression_pass':False},evidence_id='n'+str(i)).get('noise'),'FAIL_WITHIN_NOISE_BAND')
            self.assertEqual(a.state()[0]['capabilities']['language']['stage'],stage)
            for i in range(2):a.record('language',good|{'competence':.3,'regression_pass':False},evidence_id='d'+str(i))
            self.assertLess(a.state()[0]['capabilities']['language']['stage'],stage)
            store.close()

class DelayedReward(unittest.TestCase):
    def test_stream_deterministic_and_arms_run(self):
        import tempfile
        self.assertEqual(A.delayed_stream(3,120)['events'][:30],A.delayed_stream(3,120)['events'][:30])
        st=A.delayed_stream(3,400)
        with tempfile.TemporaryDirectory() as t:
            from pathlib import Path
            store,_=A._store(Path(t));rows=A.record_delayed(st,store);store.close()
        self.assertTrue(rows)
        self.assertTrue(all(r['t']==r['due'] for r in rows))
        q=sum(r['factor'] for r in rows)/len(rows)
        o=A.run_delayed(rows,'oracle',st['w'],3,q);v=A.run_delayed(rows,'v13',st['w'],3,q);d=A.run_delayed(rows,'v13_delta',st['w'],3,q)
        self.assertIsNone(o['good_vs_bad_factor']);self.assertGreater(d['good_vs_bad_factor'],2*v['good_vs_bad_factor'])  # WP-T12 per-sample δ separates confirmed samples
