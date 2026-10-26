"""WP-Z2l: the whole chain against the STEP2 criteria, with the shared-body control.

Chain (WP-Z2f..Z2k): b2_context_chars=1536, B2 pointer over whole earlier sources (b2_quote_choices=sources, 4 slots),
eligibility tool with recency guard (history) and rule_reader='newest_quoted'. WP-Z2k confirmed it on changed rules
(S4 exact 8 -> 36/210, 0 wrong). Open: are two bodies worth it? Here
  CS  two bodies (B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B), chain
  DS  one body, two states (B2 = B1 weights), chain
ten fresh episodes (REVISED 4, TWICE 2, LONG 2, CONFIRM 2), new seeds 41-43. Each recorded extraction is re-decided with
guard + reader and rescored with v13.utility.score_decision; the STEP2 comparisons use these chain utilities.
Preregistration: docs/proofs/continuation-20261026/step2-z2l-chain/PREREG.md. Diagnosis only (Linux cloud, no Redmi).
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
from v13.agi import eligibility as E
from v13.common import dumps
from v13.utility import score_decision

def _private(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

i=_private('step2_z2i_for_z2l','scripts/step2_z2i_choices.py')
h,g,z=i.h,i.g,i.z
SEEDS=(41,42,43)
CHOICES={'CS':'sources','DS':'sources'}
ARMS={'CS':('C','pointer'),'DS':('D','pointer')}
PRIMARY,SHARED='CS','DS'
TYPES=('REVISED','TWICE','LONG','CONFIRM')
VARIANTS=('b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual')
SINGLE=('b1_only','b2_only')

EPISODES=[
 ('Ankaa','REVISED',(75,4,True),(70,5,True),(72,3,True),[('deadline',5)]),
 ('Baten','REVISED',(90,5,False),(80,4,False),(60,5,True),[('budget',55)]),
 ('Cursa','REVISED',(100,6,True),(55,5,False),(85,4,True),[('local_only',False)]),
 ('Durre','REVISED',(65,7,False),(70,3,False),(60,8,False),[('budget',75)]),
 ('Enif','TWICE',(95,4,True),(50,6,True),(80,3,True),[('deadline',7),('deadline',2)]),
 ('Giausar','TWICE',(85,5,True),(45,7,True),(70,4,True),[('deadline',8),('deadline',3)]),
 ('Homam','LONG',(90,4,True),(75,5,True),(65,4,True),[]),
 ('Imai','LONG',(70,6,False),(60,6,False),(80,3,True),[]),
 ('Kitalpha','CONFIRM',(80,5,True),(70,3,True),(55,5,True),[('budget',80)]),
 ('Mirach','CONFIRM',(95,4,False),(85,4,False),(90,2,True),[('local_only',False)]),
]

FIXTURES=[h.episode(*x) for x in EPISODES]
FIX={f['id']:f for f in FIXTURES}
for m in (i,h,g):m.FIX=FIX;m.FIXTURES=FIXTURES
z.FIXTURES=FIXTURES;z.z2.FIXTURES=FIXTURES;z.FIX=FIX;z.HARD=[f['id'] for f in FIXTURES];z.HARD_TYPES=TYPES;g.HARD_TYPES=TYPES;i.TYPES=TYPES
z.ARMS.clear();z.ARMS.update(ARMS);z.z2b.ARMS.clear()
for _arm,(_base,_) in ARMS.items():z.z2b.ARMS[_arm]={'base':_base,'query':True}
z.SEEDS=SEEDS;z.z2b.SEEDS=SEEDS;g.SEEDS=SEEDS;h.SEEDS=SEEDS;i.SEEDS=SEEDS
h.ARMS=ARMS;h.SLOTS={a:4 for a in ARMS};i.ARMS=ARMS;i.CHOICES=CHOICES

def chain_rows(report,tool):
    """Every recorded row re-decided with guard + newest_quoted reader and rescored."""
    import step2_tool_replay as replay
    rows={(r['fixture'],r['variant']):r for r in report['rows']};out=[]
    for x in tool['rows']:
        f=FIX[x['fixture']];ex=(x.get('tool') or {}).get('extracted')
        if ex:
            cur,q=replay.evidence(rows[(x['fixture'],x['variant'])]['consumer_messages'])
            d=E.decide({k:ex[k] for k in g.KEYS},ex['options'],cur,q,history=g.history_of(f),rule_reader='newest_quoted')
            answer=dumps({'project':ex['project'],'action':d['action'],'options':d['options']})
        else:answer=x.get('answer') or x.get('raw_answer') or ''
        s=score_decision(answer,f['oracle']);act=replay.action_of({'answer':answer})
        out.append({'fixture':x['fixture'],'variant':x['variant'],'type':f['type'],'oracle':f['oracle']['action'],'action':act,'utility':s['utility'],
                    'recorded_utility':x['score']['utility']})
    return out

def run(installed,work,arm,seed):
    from v13.common import atomic_write,file_hash
    summary=i.run(installed,work,arm,seed);rid=z.z2b.run_id(arm,seed)
    report=json.loads((Path(work)/('step2_'+rid+'.json')).read_text());tool=json.loads((Path(work)/('tool_'+rid+'.json')).read_text())
    rows=chain_rows(report,tool)
    summary['z2l']={'rows':rows,'utility':{f"{r['fixture']}:{r['variant']}":r['utility'] for r in rows},
                    'source_sha256':{str(p.relative_to(ROOT)):file_hash(p) for p in (Path(__file__).resolve(),ROOT/'v13/agi/eligibility.py')}}
    atomic_write(Path(work)/('summary_'+rid+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def ep_diff(runs,a,b):
    return [[runs[(a[0],s)]['z2l']['utility'][f+':'+a[1]]-runs[(b[0],s)]['z2l']['utility'][f+':'+b[1]] for s in SEEDS] for f in FIX]
def mean(runs,arm,v):return sum(runs[(arm,s)]['z2l']['utility'][f+':'+v] for s in SEEDS for f in FIX)/(len(SEEDS)*len(FIX))

def gate(runs):
    """Preregistered decision (PREREG.md)."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z.z2b.run_id(*k) for k in need if k not in runs]}
    rows={a:[r for s in SEEDS for r in runs[(a,s)]['z2l']['rows']] for a in ARMS}
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    consistent=all(runs[k]['z2g']['consistent'] for k in need)
    share={a:sum(runs[(a,s)]['z2g']['validity']['kickoff_in_context'] for s in SEEDS)/max(1,sum(runs[(a,s)]['z2g']['validity']['offers'] for s in SEEDS)) for a in ARMS}
    wrong={a:sum(r['action'] in ('A','B','NONE') and r['action']!=r['oracle'] for r in rows[a]) for a in ARMS}
    single=max(SINGLE,key=lambda v:mean(runs,PRIMARY,v))
    vs_single=z.z2b.cluster_ci(ep_diff(runs,(PRIMARY,'both_exact'),(PRIMARY,single)))
    vs_shared=z.z2b.cluster_ci(ep_diff(runs,(PRIMARY,'both_exact'),(SHARED,'both_exact')))
    vs_same=z.z2b.cluster_ci(ep_diff(runs,(PRIMARY,'both_exact'),(PRIMARY,'same_policy_dual')))
    vs_prompt=z.z2b.cluster_ci(ep_diff(runs,(PRIMARY,'both_exact'),(SHARED,'prompt_only_dual')))
    shared_single=max(SINGLE,key=lambda v:mean(runs,SHARED,v))
    shared_vs_single=z.z2b.cluster_ci(ep_diff(runs,(SHARED,'both_exact'),(SHARED,shared_single)))
    beats_single=vs_single['ci95'][0]>0;beats_shared=vs_shared['ci95'][0]>0
    if not (structural and consistent):status='Z2L_INVALID'
    elif min(share.values())<g.VALID_SHARE:status='Z2L_NOT_TESTABLE'
    elif any(wrong.values()):status='Z2L_UNSAFE'
    elif beats_single and beats_shared:status='Z2L_TWO_BODIES_WORTH'
    elif beats_single:status='Z2L_COMBINATION_ONLY'
    else:status='Z2L_NO_COMBINATION_GAIN'
    exact={a:{v:sum(r['action']==r['oracle'] for r in rows[a] if r['variant']==v) for v in VARIANTS} for a in ARMS}
    return {'status':status,'structural':structural,'consistent':consistent,'validity':{'kickoff_in_context_share':share,'required':g.VALID_SHARE},
            'wrong_chain':wrong,'best_single':single,'ci':{'both_exact_vs_best_single':vs_single,'two_vs_shared_body':vs_shared,'vs_same_policy_dual':vs_same,
            'vs_shared_prompt_only_dual':vs_prompt,'shared_body_vs_its_best_single':shared_vs_single},
            'utility_chain':{a:{v:mean(runs,a,v) for v in VARIANTS} for a in ARMS},'exact_chain':exact,
            'exact_chain_by_type':{a:{t:sum(r['action']==r['oracle'] for r in rows[a] if r['type']==t and r['variant']=='both_exact') for t in TYPES} for a in ARMS},
            'utility_recorded_both_exact':{a:sum(r['recorded_utility'] for r in rows[a] if r['variant']=='both_exact')/max(1,sum(r['variant']=='both_exact' for r in rows[a])) for a in ARMS},
            'b2_rule_rate':{a:sum(h.rule_rate(runs[(a,s)],f) for s in SEEDS for f in FIX)/(len(SEEDS)*len(FIX)) for a in ARMS},'canonical_gate_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    for s in SEEDS:
        for arm in ARMS:
            f=work/('summary_'+z.z2b.run_id(arm,s)+'.json')
            if f.exists() and 'z2l' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
            print(json.dumps({'run_start':z.z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    result={'gate':gate(runs)}
    atomic_write(work/'z2l_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
