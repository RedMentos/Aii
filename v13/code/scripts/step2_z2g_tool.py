"""WP-Z2g: the body question comes from the tool whose trigger fires (cfg body_question_mode=tool, bodyq.tool_focus).

Follows WP-Z2f (message-derived question not evaluable, broke body JSON). Same harness as Z2e/Z2f; arm CT. Earlier text:
WP-Z2f: the body question built from the current message by a fixed rule (cfg body_question_mode=derived, v13/bodyq.py). Original Z2e text:
WP-Z2e: a general (task-agnostic) standing body question instead of the STEP2-specific one.

WP-Z2b/Z2c showed a targeted question helps (+.22/+.23 both_exact), but its text names Option A/B, budget, deadline and
locality, so it cannot stay on in normal chat. Here both switches carry general questions that name no task:
  B1_DETAIL  which exact details (numbers, names, values) the current message needs, quoted from the source
  B2_GIST    which earlier statements (rules, constraints, decisions) the current message depends on, quoted
Arms on the frozen Z2 fixtures, arm C settings (two bodies, quote context 200, B1 window 600), fresh seeds 23/24/25:
  C    no question (reference)
  CL   the STEP2-specific Z2b questions via the live switch (as Z2c)
  CG   the general questions via the live switch
The runner uses cfg['seed'] natively since commit 85468a9 (runner_seed); the Z2b script seed patch stays on and is a
no-op for it. Tool replay and scoring unchanged (Z2b run_one). Gate rule fixed in DECISION before any inference.
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import step2_z2_timescale as z2
import step2_z2b_seeds as z2b

SEEDS=(29,30,31)
GENERAL={'B1_DETAIL':'Which exact details (numbers, names, values) does the current message need? '
                     'Quote the exact source sentences that state them, or say they are not in the source.',
         'B2_GIST':'Which earlier statements (rules, constraints, decisions) does the current message depend on? '
                   'Quote the exact earlier source sentences that state them, or say they are not in the source.'}
SWITCH={'C':{},
        'CL':{'body_question_b1':z2b.QUESTIONS['B1_DETAIL'],'body_question_b2':z2b.QUESTIONS['B2_GIST']},
        'CT':{'body_question_mode':'tool'}}
DECISION=('Seeds 29/30/31 x 10 Z2 episodes, tool-replay utility of variant both_exact, cluster bootstrap over episodes '
          '(10000, seed 20261021). TOOL_QUESTION_SUPPORTED iff (1) CT - C mean > 0 with 95% CI lower bound > 0, '
          '(2) CT - CL mean >= -0.05 (tool question keeps the specific gain up to .05), (3) 0 wrong committed '
          'tool rows in CT, (4) all CT runs structurally complete (no invalid body JSON). Reported, not part of the verdict: b1_only/b2_only, option/rule quote counts, CI of CT - CL.')

def settings(arm,seed):return z2.ARMS['C']|{'seed':seed}|SWITCH[arm]

def diffs(runs,a,b,v='both_exact'):
    ids=[f['id'] for f in z2.FIXTURES]
    return [[runs[(a,s)]['episode_utility_tool'][i+':'+v]-runs[(b,s)]['episode_utility_tool'][i+':'+v] for s in SEEDS] for i in ids]

def mean_u(runs,arm,v):return sum(runs[(arm,s)]['paired_tool']['mean_utility'].get(v,0.) for s in SEEDS)/len(SEEDS)

def wrong(runs,arm):return sum(runs[(arm,s)]['tool_summary'][v]['wrong_committed'] for s in SEEDS for v in runs[(arm,s)]['tool_summary'])

def gate(runs):
    vs_c=z2b.cluster_ci(diffs(runs,'CT','C'));vs_l=z2b.cluster_ci(diffs(runs,'CT','CL'))
    crit={'1_tool_beats_none':vs_c['ci95'][0]>0,'2_keeps_specific_gain':vs_l['mean']>=-.05,'3_no_wrong_committed':wrong(runs,'CT')==0,'4_structurally_complete':True}
    return {'verdict':'TOOL_QUESTION_SUPPORTED' if all(crit.values()) else 'NOT_SUPPORTED','criteria':crit,
            'ct_minus_c':vs_c,'ct_minus_cl':vs_l,'cl_minus_c':z2b.cluster_ci(diffs(runs,'CL','C')),
            'mean':{a:{v:round(mean_u(runs,a,v),3) for v in ('b1_only','b2_only','both_exact')} for a in SWITCH},
            'wrong_committed':{a:wrong(runs,a) for a in SWITCH},
            'quotes':{a:[runs[(a,s)]['information_access'] for s in SEEDS] for a in SWITCH},'decision_rule':DECISION}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    p.add_argument('--runs',nargs='*',default=[f'{a}:{s}' for s in SEEDS for a in SWITCH]);p.add_argument('--evaluate',action='store_true')
    a=p.parse_args()
    from v13.common import atomic_write
    z2b.ARMS.update({k:{'base':'C','query':False} for k in SWITCH});z2b.settings=settings  # run_one reads both from module globals
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={};failed=[]
    for item in a.runs:
        arm,seed=item.split(':');seed=int(seed);f=work/('summary_'+z2b.run_id(arm,seed)+'.json')
        try:runs[(arm,seed)]=json.loads(f.read_text()) if f.exists() else z2b.run_one(a.installed_home,work,arm,seed)
        except ValueError as exc:  # the frozen tool replay refuses reports with structural failures (criterion 4)
            failed.append({'run':item,'error':str(exc)[:200]});print(json.dumps(failed[-1]),flush=True);continue
        print(json.dumps({'run':item,'both_exact':runs[(arm,seed)]['paired_tool']['mean_utility'].get('both_exact')}),flush=True)
    if a.evaluate and failed:
        res={'kind':'STEP2_Z2G_TOOL_QUESTION','seeds':SEEDS,'verdict':'NOT_SUPPORTED','criteria':{'4_structurally_complete':False},'failed_runs':failed,'decision_rule':DECISION}
        atomic_write(work/'z2g_result.json',json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,indent=1));return
    if a.evaluate:
        res={'kind':'STEP2_Z2G_TOOL_QUESTION','seeds':SEEDS,**gate(runs)}
        atomic_write(work/'z2g_result.json',json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,indent=1)[:3000])
if __name__=='__main__':main()
