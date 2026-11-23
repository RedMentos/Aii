"""WP-Z2b: noise band (several sampling seeds) and targeted executive questions to the bodies on the Z2 STEP2 fixtures.

Follow-up of WP-Z2 (scripts/step2_z2_timescale.py, result Z2_DIVERGENCE_NOT_SUPPORTED with one seed: two bodies .325 vs
b1_only .333, shared body .367). Open: is that difference larger than run-to-run noise, and is the bottleneck the bodies'
selection (B2 quoted the old rule 16/70, never rules and options in the same two-body row)?

Unchanged: the 10 frozen Z2 episodes, the private copy of the frozen STEP2 harness, the eligibility tool replay
(scripts/step2_tool_replay.py, C3 extraction seed 13), Z2 arms C/D settings.
New in this script only (no live code changed):
  seed   cfg['seed'] per run. The body offer path calls LlamaRunner.generate without a seed, so every offer ran with the
         default 13 whatever cfg said; here the runner default follows cfg['seed'] (seed 13 = Z2 bytes). The STEP2 consumer
         already passes cfg['seed']. The tool replay keeps its fixed seed 13, so the band comes from body sampling.
  query  arms CQ/DQ: on the current turn only (never the preparation turns) every body offer gets a fixed executive
         question (jef_query, kind FILL_GAP, the existing QUERY_PACKET path of cognition.offer). Role-specific, the
         same text for every episode, no values: B2 is asked for the earlier rules, B1 for the option figures.
Arms x seeds: C, D, CQ, DQ x 14, 15, 16 (12 runs x 70 rows). Seed 13 (Z2) is reported for reference, not counted.
Preregistration: docs/proofs/continuation-20261021/step2-z2b-seeds/PREREG.md. Diagnosis only (Linux cloud, no Redmi);
the canonical gate is never promoted by this script.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import step2_z2_timescale as z2

SEEDS=(14,15,16)
REFERENCE_SEED=13
QUESTIONS={
 'B2_GIST':'Which earlier project rules apply here: budget, deadline and local-only requirement? '
           'Quote the exact earlier source sentence that states them, or say they are not in the source.',
 'B1_DETAIL':'Which option figures apply here: cost, duration and locality of Option A and Option B? '
             'Quote the exact source sentences that state them, or say they are not in the source.'}
ARMS={'C':{'base':'C','query':False},'D':{'base':'D','query':False},'CQ':{'base':'C','query':True},'DQ':{'base':'D','query':True}}
PRIMARY,CONTROL='CQ','DQ'
SINGLE=('b1_only','b2_only')
BOOT=10000;BOOT_SEED=20261021

def run_id(arm,seed):return f'{arm}_s{seed}'
def settings(arm,seed):return z2.ARMS[ARMS[arm]['base']]|{'seed':seed}

def focus(role):return {'question':QUESTIONS[role],'kind':'FILL_GAP','target_role':role,'reason':'Z2B_PREREGISTERED_QUESTION','authority':'EXECUTIVE_QUESTION_NOT_FACT'}

class Patches:
    """Seed follows cfg for seedless runner calls; optional fixed question on current-turn offers. Undone on exit."""
    def __init__(self,step2,query):self.step2=step2;self.query=query;self.count={'offers':0,'with_question':0}
    def __enter__(self):
        from v13 import runners,cognition
        self.saved=[(runners.LlamaRunner,'generate',runners.LlamaRunner.generate),(cognition.Cognition,'offer',cognition.Cognition.offer),(self.step2,'run_variant',self.step2.run_variant)]
        gen=runners.LlamaRunner.generate;offer=cognition.Cognition.offer;variant=self.step2.run_variant;state={'current':False}
        def generate(runner,messages,cancel,deadline,max_tokens=None,schema=None,*rest,**kw):
            if not rest and 'seed' not in kw:kw['seed']=runner.cfg.get('seed',13)
            return gen(runner,messages,cancel,deadline,max_tokens,schema,*rest,**kw)
        def offer_q(cog,role,e,version,deadline,peer=None,**kw):
            if state['current']:
                self.count['offers']+=1
                if self.query and kw.get('focus') is None:kw['focus']=focus(role);self.count['with_question']+=1
            return offer(cog,role,e,version,deadline,peer,**kw)
        def run_variant(*a,**kw):
            state['current']=True
            try:return variant(*a,**kw)
            finally:state['current']=False
        runners.LlamaRunner.generate=generate;cognition.Cognition.offer=offer_q;self.step2.run_variant=run_variant
        return self
    def __exit__(self,*exc):
        for obj,name,value in self.saved:setattr(obj,name,value)

def joint_access(access):
    """Per variant: rows where verified quotes (any role) carried all rules and all option values together."""
    res={}
    for key,acc in access.items():
        v=key.split(':')[1];both=any(x['rules'] for x in acc.values()) and any(x['options'] for x in acc.values())
        res[v]=res.get(v,0)+both
    return res

def run_one(installed,work,arm,seed):
    import step2_tool_replay as replay
    from v13.common import atomic_write,file_hash
    work=Path(work);rid=run_id(arm,seed);out=work/('step2_'+rid+'.json');home=work/(rid+'-home');step2=z2.harness()
    old=json.loads(out.read_text()) if out.exists() else None
    with Patches(step2,ARMS[arm]['query']) as patch:
        if old and old.get('status') in ('UTILITY_FAIL','UTILITY_PASS_SCOPED') and len(old['rows'])==len(z2.FIXTURES)*7:report=old  # rows recorded, only post-processing failed
        else:report=step2.run_locked(z2.sibling_home(installed,home,settings(arm,seed)),out);report['z2b_queried_offers']=patch.count
    report['proof_kind']='STEP2_Z2B_SEEDS';report['harness_copy_of']='tests/integration_step2_utility.py'
    report['z2b_source_sha256']={str(p.relative_to(ROOT)):file_hash(p) for p in (Path(__file__).resolve(),Path(z2.__file__).resolve(),ROOT/'v13/cognition.py',ROOT/'v13/runners.py',ROOT/'tests/integration_step2_utility.py')}
    report['wire_arm']={'arm':'w1','note':'live wire'};report['z2b_run']={'arm':arm,'seed':seed,'enable':settings(arm,seed),'query':QUESTIONS if ARMS[arm]['query'] else None}
    report['information_access']=z2.information_access(report)
    atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    tool=replay.run(home,out,work/('tool_'+rid+'.json'))
    fixtures={f['id']:f for f in report['fixtures']}
    summary={'run':rid,'arm':arm,'seed':seed,'enable':settings(arm,seed),'query':ARMS[arm]['query'],'step2_status':report['status'],
             'paired_no_tool':report['paired'],'tool_status':tool['status'],'paired_tool':tool['paired_tool'],'tool_summary':tool['summary']['tool'],
             'error_profile_tool':z2.error_profile(tool['rows'],fixtures),'information_access':z2.access_counts(report['information_access'],fixtures),
             'joint_access':joint_access(report['information_access']),'queried_offers':report.get('z2b_queried_offers'),
             'episode_utility_tool':{x['fixture']+':'+x['variant']:x['score']['utility'] for x in tool['rows']},
             'split_exact_tool':{v:sorted(f for f in s['exact_fixtures'] if fixtures[f]['type']=='SPLIT') for v,s in tool['summary']['tool'].items()}}
    atomic_write(work/('summary_'+rid+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def episode_diff(runs,a,b):
    """Per episode (list over episodes) of per-seed differences a-b. a/b are (run_key_arm, variant)."""
    ids=[f['id'] for f in z2.FIXTURES];out=[]
    for fid in ids:
        out.append([runs[(a[0],s)]['episode_utility_tool'][fid+':'+a[1]]-runs[(b[0],s)]['episode_utility_tool'][fid+':'+b[1]] for s in SEEDS])
    return out

def cluster_ci(diffs,n=BOOT,seed=BOOT_SEED):
    """Mean difference and 95% percentile CI, bootstrap over episodes (clusters; all seeds of an episode stay together)."""
    import numpy as np
    per=np.array([sum(d)/len(d) for d in diffs]);rng=np.random.default_rng(seed)
    idx=rng.integers(0,len(per),size=(n,len(per)));boot=per[idx].mean(axis=1)
    return {'mean':float(per.mean()),'ci95':[float(np.percentile(boot,2.5)),float(np.percentile(boot,97.5))],'episodes':len(per),'seeds':len(diffs[0]) if diffs else 0}

def mean_u(runs,arm,v):return sum(runs[(arm,s)]['paired_tool']['mean_utility'].get(v,0.) for s in SEEDS)/len(SEEDS)

def band(runs,arm,v):
    vals=[runs[(arm,s)]['paired_tool']['mean_utility'].get(v,0.) for s in SEEDS]
    return {'per_seed':dict(zip(map(str,SEEDS),vals)),'mean':sum(vals)/len(vals),'min':min(vals),'max':max(vals),'range':max(vals)-min(vals)}

def verdict(ci,pos,neg,none):return pos if ci['ci95'][0]>0 else neg if ci['ci95'][1]<0 else none

def gate(runs,reference=None):
    """Preregistered decision (PREREG.md). Tool-replay utility, seeds 14-16, cluster bootstrap over the 10 episodes."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[run_id(*k) for k in need if k not in runs]}
    P,K=PRIMARY,CONTROL;two=mean_u(runs,P,'both_exact')
    single=max(SINGLE,key=lambda v:mean_u(runs,P,v))
    vs_single=cluster_ci(episode_diff(runs,(P,'both_exact'),(P,single)))
    per_seed_beats=all(runs[(P,s)]['paired_tool']['mean_utility'].get('both_exact',0.)>max(runs[(P,s)]['paired_tool']['mean_utility'].get(v,0.) for v in SINGLE) for s in SEEDS)
    ep={v:{k:sum(runs[(P,s)]['error_profile_tool'][v][k] for s in SEEDS)/len(SEEDS) for k in ('rule_fields_correct','option_fields_correct')} for v in SINGLE}
    complementary=(ep['b1_only']['option_fields_correct']-ep['b2_only']['option_fields_correct']>=.25 and ep['b2_only']['rule_fields_correct']-ep['b1_only']['rule_fields_correct']>=.25)
    vs_same=cluster_ci(episode_diff(runs,(P,'both_exact'),(P,'same_policy_dual')))
    vs_prompt=cluster_ci(episode_diff(runs,(P,'both_exact'),(K,'prompt_only_dual')))
    vs_shared=cluster_ci(episode_diff(runs,(P,'both_exact'),(K,'both_exact')))
    wins=sum(bool(runs[(P,s)]['paired_tool']['b1_b2_each_win_an_episode']) for s in SEEDS)
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    queried=all(runs[(a,s)]['queried_offers']['with_question']==runs[(a,s)]['queried_offers']['offers']>0 for a in ('CQ','DQ') for s in SEEDS) and \
            all(runs[(a,s)]['queried_offers']['with_question']==0 for a in ('C','D') for s in SEEDS)
    checks={'combination_beats_best_single':two>mean_u(runs,P,single) and vs_single['ci95'][0]>0 and per_seed_beats,
            'each_body_wins_an_episode':wins>=2,'complementary_error_profiles':complementary,
            'beats_same_model_same_policy':vs_same['ci95'][0]>0,'beats_same_model_prompt_only':vs_prompt['ci95'][0]>0,
            'structural':structural,'arms_did_what_they_say':queried}
    passed=all(checks.values())
    secondary={'query_effect_two_body':verdict(cluster_ci(episode_diff(runs,('CQ','both_exact'),('C','both_exact'))),'QUERY_HELPS','QUERY_HURTS','QUERY_NO_CLEAR_EFFECT'),
               'query_effect_shared_body':verdict(cluster_ci(episode_diff(runs,('DQ','both_exact'),('D','both_exact'))),'QUERY_HELPS','QUERY_HURTS','QUERY_NO_CLEAR_EFFECT'),
               'b2_model_both_exact':verdict(cluster_ci(episode_diff(runs,('D','both_exact'),('C','both_exact'))),'LFM_B2_BETTER','QWEN_B2_BETTER','NO_CLEAR_DIFFERENCE'),
               'b2_model_b2_only':verdict(cluster_ci(episode_diff(runs,('D','b2_only'),('C','b2_only'))),'LFM_B2_BETTER','QWEN_B2_BETTER','NO_CLEAR_DIFFERENCE')}
    cis={'primary_vs_best_single':vs_single|{'best_single':single},'primary_vs_same_policy_dual':vs_same,'primary_vs_control_prompt_only_dual':vs_prompt,
         'primary_vs_control_shared_body':vs_shared,
         'query_two_body':cluster_ci(episode_diff(runs,('CQ','both_exact'),('C','both_exact'))),'query_shared_body':cluster_ci(episode_diff(runs,('DQ','both_exact'),('D','both_exact'))),
         'lfm_minus_qwen_both_exact':cluster_ci(episode_diff(runs,('D','both_exact'),('C','both_exact'))),'lfm_minus_qwen_b2_only':cluster_ci(episode_diff(runs,('D','b2_only'),('C','b2_only')))}
    bands={a:{v:band(runs,a,v) for v in ('b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual')} for a in ARMS}
    noise={}
    if reference:  # Z2 seed 13: is its difference outside the band of seeds 14-16?
        rc=reference['C']['tool'];rd=reference['D']['tool']
        def diffs(f):return [f(s) for s in SEEDS]
        u=lambda arm,s,v:runs[(arm,s)]['paired_tool']['mean_utility'].get(v,0.)
        d1=diffs(lambda s:u('C',s,'both_exact')-u('C',s,'b1_only'));d2=diffs(lambda s:u('D',s,'both_exact')-u('C',s,'both_exact'))
        noise={'z2_two_body_minus_b1_only':rc['both_exact']-rc['b1_only'],'seeds_two_body_minus_b1_only':[min(d1),max(d1)],
               'z2_shared_minus_two_body':rd['both_exact']-rc['both_exact'],'seeds_shared_minus_two_body':[min(d2),max(d2)],
               'z2_c_both_exact_inside_seed_band':bands['C']['both_exact']['min']<=rc['both_exact']<=bands['C']['both_exact']['max']}
    return {'status':'Z2B_DIVERGENCE_SUPPORTED' if passed else 'Z2B_DIVERGENCE_NOT_SUPPORTED','checks':checks,'primary_arm':P,'control_arm':K,
            'two_body_both_exact_mean':two,'best_single':single,'best_single_mean':mean_u(runs,P,single),'error_profile_mean':ep,'each_body_wins_seeds':wins,
            'two_bodies_worth_cost':passed and vs_shared['ci95'][0]>0,'cheaper_shared_body_enough':vs_shared['ci95'][0]<=0,
            'secondary':secondary,'ci':cis,'bands':bands,'noise_vs_z2':noise,'canonical_gate_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    p.add_argument('--runs',nargs='*',help='e.g. C_s14 DQ_s15; default all in preregistered order');p.add_argument('--reference',help='Z2 z2_result.json (seed 13)')
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    order=[(arm,s) for s in SEEDS for arm in ARMS]
    if a.runs:order=[(r.split('_s')[0],int(r.split('_s')[1])) for r in a.runs]
    for arm,s in order:
        f=work/('summary_'+run_id(arm,s)+'.json')
        if f.exists():runs[(arm,s)]=json.loads(f.read_text());continue
        print(json.dumps({'run_start':run_id(arm,s)}),flush=True);runs[(arm,s)]=run_one(a.installed_home,work,arm,s)
    for f in work.glob('summary_*_s*.json'):
        x=json.loads(f.read_text());runs.setdefault((x['arm'],x['seed']),x)
    ref=json.loads(Path(a.reference).read_text())['arms'] if a.reference else None
    result={'gate':gate(runs,ref),'runs':{run_id(*k):{'tool':v['paired_tool']['mean_utility'],'joint_access':v['joint_access'],'split_exact_tool':v['split_exact_tool']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2b_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
