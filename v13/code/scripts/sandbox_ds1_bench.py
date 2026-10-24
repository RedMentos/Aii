"""WP-DS1 bench: six curiosity policies in the lab sandbox (v13/sandbox.py), preregistered seeds 100..119.

Writes bench-results/sandbox-ds1-20261021/report.json (per run + summary + hypothesis verdicts). No models needed.
"""
import json
import statistics as st
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13 import sandbox as S

SEEDS=range(100,120);OUT=Path(__file__).resolve().parents[2]/'bench-results'/'sandbox-ds1-20261021'

def at(r,t):return [k for s,k in r['curve'] if s<=t][-1]
def wins(a,b,key):return sum(key(x)<key(y) for x,y in zip(a,b))
def main():
    runs={p:[S.run(p,s) for s in SEEDS] for p in S.POLICIES}
    summ={}
    for p,rs in runs.items():
        new=[r['new_kind_steps_to_goal'] for r in rs]
        summ[p]={'kl@300':round(st.mean(at(r,300) for r in rs),4),'kl@600':round(st.mean(at(r,600) for r in rs),4),
                 'kl@1500':round(st.mean(r['final_kl'] for r in rs),4),'kl_learnable@1500':round(st.mean(r['final_kl_learnable'] for r in rs),4),
                 'noise_share':round(st.mean(r['noise_share'] for r in rs),4),'mean_hunger':round(st.mean(r['mean_hunger'] for r in rs),4),
                 'grounding':round(st.mean(r['grounding'] for r in rs),4),'new_kind_learned':sum(n is not None for n in new),
                 'new_kind_median_steps':st.median([n for n in new if n is not None]) if any(n is not None for n in new) else None}
    k600=lambda r:at(r,600);n=len(SEEDS)
    h1={p:wins(runs[p],runs['random'],k600) for p in ('novelty','lp','eig','efe')}
    lp_vs_eig=wins(runs['lp'],runs['eig'],k600)
    h4_h=wins(runs['efe'],runs['eig'],lambda r:r['mean_hunger'])
    verdict={
     'H1_curiosity_beats_random':{'wins_of_20':h1,'pass':all(v>=15 for v in h1.values())},
     'H2_noisy_tv_trap':{'surprise':summ['surprise']['noise_share'],'eig':summ['eig']['noise_share'],'lp':summ['lp']['noise_share'],
                         'pass':summ['surprise']['noise_share']>=.5 and summ['eig']['noise_share']<=.25 and summ['lp']['noise_share']<=.25},
     'H3_lp_vs_eig_kl600':{'lp_wins_of_20':lp_vs_eig,'result':'LP_BETTER' if lp_vs_eig>=14 else 'EIG_BETTER' if n-lp_vs_eig>=14 else 'TIE',
                           'predicted':'LP_BETTER'},
     'H4_efe_hunger':{'efe_lower_hunger_wins_of_20':h4_h,'kl_ratio_efe_eig@1500':round(summ['efe']['kl@1500']/summ['eig']['kl@1500'],3),
                      'pass':h4_h>=15 and summ['efe']['kl@1500']<=1.25*summ['eig']['kl@1500']},
     'H5_new_kind':{p:(summ[p]['new_kind_learned'],summ[p]['new_kind_median_steps']) for p in S.POLICIES},
     'grounding_ge_095':{p:summ[p]['grounding']>=.95 for p in S.POLICIES}}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'report.json').write_text(json.dumps({'revision':S.REVISION,'seeds':list(SEEDS),'summary':summ,'verdict':verdict,'runs':runs},indent=1))
    print(json.dumps({'summary':summ,'verdict':verdict},indent=1))
if __name__=='__main__':main()
