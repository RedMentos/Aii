"""WP-Z2c: does the live switch body_question_b1 / body_question_b2 reproduce the WP-Z2b targeted-question effect?

WP-Z2b (scripts/step2_z2b_seeds.py) put the questions on through a runner patch, only on current-turn offers and on
both bodies. The live switch (v13/cognition.offer, cfg body_question_*) asks on every offer without a re-entry focus,
also on the earlier turns the harness prepares. Arms on the frozen Z2 fixtures, arm C settings, seed 14:
  CL   both switches on (Z2b CQ questions), live path
  CB1  only body_question_b1 (not measured in Z2b; B2 asks nothing)
Compared against the recorded Z2b runs C_s14 and CQ_s14. Same runner, seed patch and tool replay as Z2b (no query
patch). Confirmation only, one seed: no gate, the canonical gate is never promoted, the switch stays off by default.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import step2_z2_timescale as z2
import step2_z2b_seeds as z2b

SEED=14
SWITCH={'CL':{'body_question_b1':z2b.QUESTIONS['B1_DETAIL'],'body_question_b2':z2b.QUESTIONS['B2_GIST']},
        'CB1':{'body_question_b1':z2b.QUESTIONS['B1_DETAIL']}}
Z2B_DIR=ROOT/'bench-results/step2-z2b-seeds-20261021'

def settings(arm,seed):return z2.ARMS['C']|{'seed':seed}|SWITCH[arm] if arm in SWITCH else z2.ARMS[z2b.ARMS[arm]['base']]|{'seed':seed}

def compare(new,ref_dir=Z2B_DIR):
    """Tool-replay utility per variant next to the recorded Z2b runs of the same seed."""
    rows={}
    for rid in ('C_s%d'%SEED,'CQ_s%d'%SEED):
        f=ref_dir/('summary_'+rid+'.json')
        if f.exists():rows[rid+' (Z2b)']=json.loads(f.read_text())
    rows.update({k+' (live switch)':v for k,v in new.items()})
    keep=('paired_tool','joint_access','split_exact_tool','queried_offers')
    return {k:{'tool':v['paired_tool']['mean_utility'],'option_quotes':v['information_access'],'joint_access':v['joint_access'],
               'error_profile_tool':v['error_profile_tool']} for k,v in rows.items() if all(x in v for x in keep[:3])}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    p.add_argument('--runs',nargs='*',default=list(SWITCH))
    a=p.parse_args()
    from v13.common import atomic_write
    z2b.ARMS.update({k:{'base':'C','query':False} for k in SWITCH});z2b.settings=settings  # run_one reads both from module globals
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);new={}
    for arm in a.runs:
        f=work/('summary_'+z2b.run_id(arm,SEED)+'.json')
        new[arm]=json.loads(f.read_text()) if f.exists() else z2b.run_one(a.installed_home,work,arm,SEED)
    result={'kind':'STEP2_Z2C_SWITCH_CONFIRMATION','seed':SEED,'compare':compare(new)}
    atomic_write(work/'z2c_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,indent=1)[:4000])
if __name__=='__main__':main()
