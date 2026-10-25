"""Thread L §99-style ablations for metaplasticity and homeostasis: drive the real pure functions, verdict rule."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ablation_homeo_meta as A
from v13 import homeostasis as H

class HomeoMeta(unittest.TestCase):
    def test_streams_are_identical_per_seed_and_arms_differ(self):
        self.assertEqual(A.meta_stream(13)[5]['y'],A.meta_stream(13)[5]['y'])
        s=A.homeo_stream(13);self.assertEqual({e['path'] for e in s if e['phase']=='skewed'}-set(A.PATHS),set())
        self.assertNotIn(A.REVIVED,{e['path'] for e in s if e['phase']=='skewed'})
        v=A.run_meta(A.meta_stream(13),'v13');p=A.run_meta(A.meta_stream(13),'fixed_permissive')
        self.assertEqual(p['mean_p'],1.);self.assertLess(v['mean_p'],1.)
    def test_home_knobs_restored_after_ablation(self):
        old=dict(H.HOME)
        with A._home(dominant_path_inhibition=0.):self.assertEqual(H.HOME['dominant_path_inhibition'],0.)
        self.assertEqual(H.HOME,old)
    def test_verdict_rule(self):
        per={s:{'v13':{'primary':1.},'a':{'primary':2.},'b':{'primary':.5}} for s in range(5)}
        self.assertEqual(A._verdict(per,('v13','a','b'))['verdict'],'PARTIAL')
        per={s:{'v13':{'primary':1.},'a':{'primary':2.}} for s in range(5)};self.assertEqual(A._verdict(per,('v13','a'))['verdict'],'SUPPORTED_SYNTHETIC')

if __name__=='__main__':unittest.main()

import ablation_corollary as C
class Corollary(unittest.TestCase):
    def test_attribution_uses_real_function_and_safety_stays_raw(self):
        st=C.attr_stream(13);acts,obs=st
        self.assertEqual({o['truth'] for o in obs},{'SELF','MIXED','EXTERNAL'})
        self.assertEqual(C.run_attr(st,'no_corollary')['primary'],round(1/3,5))
        a=C.att_stream(13,40);rows={x:C.run_att(a,x,seed=1) for x in C.ATT_ARMS}
        self.assertTrue(all(rows[x]['raw_signals']==rows['v13']['raw_signals'] for x in rows))
        old=C.S.ATTENUATION
        with C._att(1.):pass
        self.assertEqual(C.S.ATTENUATION,old)

import ablation_attention_prior as AP
class AttentionPrior(unittest.TestCase):
    def test_short_run_uses_real_admission_budget(self):
        old=AP.EVENTS;AP.EVENTS=4
        try:
            st=AP.stream(13,'blind');r={a:AP.run_arm(st,a,13) for a in ('scaffold','learned_active')}
            self.assertEqual(r['scaffold']['granted'],2*3);self.assertEqual(r['learned_active']['granted'],2*3)
        finally:AP.EVENTS=old

import ablation_latewatch as LW
class LateWatch(unittest.TestCase):
    def test_real_watcher_cuts_conflict_not_agreement(self):
        t={'src':'What is 46 plus 62?','answer':'The result is 100, because I applied plus to the two numbers.','wrong':True,'body':'right',
           'offer':{'role':'B1_DETAIL','packet_id':'p','offer':{'summary':'46 + 62 = 108','needs_reentry':False,'quotes':[]}},'arrive':0}
        self.assertTrue(LW.rule_cut(t));self.assertEqual(LW.score(t,True),1)
        ok=dict(t,answer=t['answer'].replace('100','108'),wrong=False);self.assertFalse(LW.rule_cut(ok));self.assertEqual(LW.score(ok,True),-1)

import ablation_reflex_breaker as RB
class ReflexBreaker(unittest.TestCase):
    def test_real_breaker_opens_after_three_failures_and_skips(self):
        cs=[(float(i),True) for i in range(5)]+[(500.,False)]
        r=RB.run_arm(cs,'breaker',13)
        self.assertEqual(r['failed_calls'],3);self.assertEqual(r['skipped'],2)  # open for COOLDOWN_S after the third failure
        self.assertEqual(RB.run_arm(cs,'never',13)['failed_calls'],5)

import ablation_episodic_route as EPR
class EpisodicRouteAblation(unittest.TestCase):
    def test_one_correction_fixes_the_paraphrase_not_the_other_entity(self):
        q=lambda text,task,truth,u=0.:{'text':text,'task':task,'truth':truth,'u':u}
        reqs=[q('Erkläre Projekt Aurora genau.','detail','gist'),q('Erkläre Projekt Borealis genau.','detail','detail',1.),q('Erkläre mir Projekt Aurora ganz genau.','detail','gist',1.)]
        old=EPR.N;EPR.N=2
        try:
            self.assertEqual(EPR.run_arm(reqs,'episodic')['primary'],1.)  # Borealis untouched, Aurora paraphrase corrected
            self.assertEqual(EPR.run_arm(reqs,'no_entity_guard')['primary'],.5)  # the correction leaks to Borealis
        finally:EPR.N=old

import ablation_sleep_offline as SO
class SleepOfflineAblation(unittest.TestCase):
    def test_short_run_uses_real_consolidate_and_restores_buffer(self):
        days=SO.turns(13,'stationary')[:2]
        self.assertEqual(SO.run_arm(days,'no_sleep',13)['sleeps_kept'],0)
        import tempfile;from pathlib import Path;from v13.ablation99 import _store
        with tempfile.TemporaryDirectory() as d:
            store,_=_store(Path(d));ff=SO.FF.FastForward(store)
            for i,t in enumerate(days[0]):ff.learn(f'e{i}',t['x'],t['duration_s'],t['status'],t['chars'])
            before=ff._load()[0]['replay'];SO.shuffled_consolidate(ff,__import__('random').Random(1))
            self.assertEqual(ff._load()[0]['replay'],before);store.close()

import ablation_f7_plasticity as F7A
class F7PlasticityAblation(unittest.TestCase):
    def test_real_observe_accepts_every_fixture_trial(self):
        old=F7A.TRIALS;F7A.TRIALS=16
        try:
            r=F7A.run_arm(F7A.stream(13),'f7',13)  # raises if observe() rejects a trial
            self.assertTrue(.5<=r['mean_gain']<=1.);self.assertEqual(F7A.run_arm(F7A.stream(13),'half',13)['mean_gain'],.5)
        finally:F7A.TRIALS=old

import ablation_aplane_gate as APG
class APlaneGateAblation(unittest.TestCase):
    def test_real_gate_promotes_good_and_refuses_bad_student(self):
        turns=[{'teacher':i%2==0,'student_right':True,'scaffold_right':False} for i in range(240)]
        old=APG.T;APG.T=240
        try:
            self.assertEqual(APG.run_arm((turns,[]),'never',)['primary'],0.)
            self.assertEqual(APG.run_arm((turns,[]),'always')['primary'],1.)
            self.assertEqual(APG.run_arm((turns,[]),'gated')['primary'],1.)  # promoted once GATE_N agreeing comparisons exist
            bad=[dict(q,student_right=False,scaffold_right=True) for q in turns]
            self.assertEqual(APG.run_arm((bad,[]),'gated')['primary'],1.)  # the real gate refuses the failing student: scaffold routes
        finally:APG.T=old

import ablation_world_model_confidence as WMC
class WorldModelConfidenceAblation(unittest.TestCase):
    def test_spearman_and_real_fit(self):
        self.assertAlmostEqual(WMC.spearman([1,2,3],[3,2,1]),-1.);self.assertAlmostEqual(WMC.spearman([1,1,2],[1,1,2]),1.)
        old=WMC.Q;WMC.Q=20
        try:
            r=WMC.run_seed(13)
            self.assertEqual(r['fit_status'],'FITTED')
            self.assertEqual(r['queries_n'],20)
            self.assertEqual(r['evaluated_n']+r['abstained_n'],20)
            self.assertEqual(r['labels']['supported_n']+r['labels']['uncertain_n'],r['evaluated_n'])
        finally:WMC.Q=old
