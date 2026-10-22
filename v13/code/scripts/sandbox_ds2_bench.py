"""WP-DS2 bench: combined curiosity+goal policy (part A) and generalizing grounding (part B), lab sandbox only.

Preregistered in bench-results/sandbox-ds2-20261022/PREREG.md before this ran. Part A seeds 200..219, part B seeds
300..319 (pilot seeds 1..5 only). Writes report.json there. No models needed.
"""
import json
import statistics as st
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13 import sandbox as S
from v13 import sandbox_ds2 as D

SEEDS_A=range(200,220);SEEDS_B=range(300,320)
OUT=Path(__file__).resolve().parents[2]/'bench-results'/'sandbox-ds2-20261022'
BIG=10**6

def wins(a,b,key):return sum(key(x)<key(y) for x,y in zip(a,b))
def g(v):return BIG if v is None else v
def part_a():
    runs={p:[D.run_a(p,s) for s in SEEDS_A] for p in D.POLICIES_A}
    summ={p:{'kl@1500':round(st.mean(r['final_kl'] for r in rs),4),'mean_hunger':round(st.mean(r['mean_hunger'] for r in rs),4),
             'noise_share':round(st.mean(r['noise_share'] for r in rs),4),'grounding':round(st.mean(r['grounding'] for r in rs),4),
             'pilz_learned':sum(r['new_kind_steps_to_goal'] is not None for r in rs),
             'pilz_median_steps':st.median([g(r['new_kind_steps_to_goal']) for r in rs])} for p,rs in runs.items()}
    L,E,LG,NB=summ['lp'],summ['efe'],summ['lpgoal'],summ['lpgoal_noboost']
    h=wins(runs['lpgoal'],runs['lp'],lambda r:r['mean_hunger'])
    bw=wins(runs['lpgoal'],runs['lpgoal_noboost'],lambda r:g(r['new_kind_steps_to_goal']))
    bl=wins(runs['lpgoal_noboost'],runs['lpgoal'],lambda r:g(r['new_kind_steps_to_goal']))
    verdict={
     'A1_hunger':{'lpgoal_lower_than_lp_of_20':h,'ratio_lpgoal_efe':round(LG['mean_hunger']/E['mean_hunger'],3),
                  'pass':h>=15 and LG['mean_hunger']<=1.25*E['mean_hunger']},
     'A2_new_object':{'lpgoal_pilz_learned_of_20':LG['pilz_learned'],'efe':E['pilz_learned'],'pass':LG['pilz_learned']>=17},
     'A3_world_model':{'ratio_kl1500_lpgoal_lp':round(LG['kl@1500']/L['kl@1500'],3),'pass':LG['kl@1500']<=1.25*L['kl@1500']},
     'A4_noise':{'lpgoal_noise_share':LG['noise_share'],'pass':LG['noise_share']<=.25},
     'A5_novelty_boost':{'boost_faster_of_20':bw,'noboost_faster_of_20':bl,'learned_boost':LG['pilz_learned'],'learned_noboost':NB['pilz_learned'],
                         'result':'BOOST_HELPS' if bw>=14 or LG['pilz_learned']-NB['pilz_learned']>=3 else
                                  'BOOST_HURTS' if bl>=14 or NB['pilz_learned']-LG['pilz_learned']>=3 else 'NO_GAIN','predicted':'NO_GAIN'}}
    return runs,summ,verdict
def part_b():
    runs=[D.run_b(s) for s in SEEDS_B];n=len(runs)
    combos=[D.item_name(i) for i in D.HOLDOUT_COMBOS];look=[D.item_name(i) for i in D.HOLDOUT_LOOKALIKE];wa=D.item_name(D.HOLDOUT_MISLEAD[0])
    def m(r,items,l):return st.mean(r['first_kl'][i][l] for i in items)
    summ={'first_kl':{grp:{l:round(st.mean(m(r,items,l) for r in runs),4) for l in D.LEARNERS}
                      for grp,items in(('combos',combos),('lookalike',look),('wachsapfel',[wa]))},
          'reached_goal':{grp:{l:sum(r['to_goal'][i][l] is not None for r in runs for i in items) for l in D.LEARNERS}
                          for grp,items in(('combos',combos),('lookalike',look),('wachsapfel',[wa]))},
          'median_to_goal':{grp:{l:st.median(g(r['to_goal'][i][l]) for r in runs for i in items) for l in D.LEARNERS}
                            for grp,items in(('combos',combos),('lookalike',look),('wachsapfel',[wa]))},
          'final_mean_item_kl':{l:round(st.mean(r['final_mean_item_kl'][l] for r in runs),4) for l in D.LEARNERS},
          'wachsapfel_feat_p_eaten_first':round(st.mean(r['wachsapfel_feat_p_eaten_first'] for r in runs),4),
          'wachsapfel_p_eaten_final':{l:round(st.mean(r['wachsapfel_p_eaten_final'][l] for r in runs),4) for l in D.LEARNERS}}
    b1=sum(m(r,combos,'feat')<m(r,combos,'backoff') for r in runs)
    b1s=sum(m(r,combos,'backoff')<m(r,combos,'flat') for r in runs)
    b2=sum(m(r,look,'feat')<m(r,look,'flat') for r in runs)
    b2g=summ['reached_goal']['lookalike']['feat']
    b3g=sum(r['to_goal'][wa]['feat'] is not None for r in runs);b3p=sum(r['wachsapfel_p_eaten_final']['feat']<=.1 for r in runs)
    b4=sum(r['final_mean_item_kl']['feat']<r['final_mean_item_kl']['flat'] for r in runs)
    verdict={
     'B1_word_combinations':{'feat_better_than_backoff_of_20':b1,'backoff_better_than_flat_of_20':b1s,'pass':b1>=15},
     'B2_lookalike_nouns':{'feat_better_than_flat_of_20':b2,'feat_reached_goal_of_60':b2g,'pass':b2>=15 and b2g>=54},
     'B3_misleading_look':{'feat_p_eaten_first_mean':summ['wachsapfel_feat_p_eaten_first'],'feat_reached_goal_of_20':b3g,
                           'feat_p_eaten_final_le_0.1_of_20':b3p,'pass':b3g>=18 and b3p>=18},
     'B4_overall_model':{'feat_lower_final_kl_than_flat_of_20':b4,'report_only':True}}
    return runs,summ,verdict
def main():
    ra,sa,va=part_a();rb,sb,vb=part_b()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'report.json').write_text(json.dumps({'revision':D.REVISION,'seeds_a':list(SEEDS_A),'seeds_b':list(SEEDS_B),
        'summary_a':sa,'verdict_a':va,'summary_b':sb,'verdict_b':vb,'runs_a':ra,'runs_b':rb},indent=1))
    print(json.dumps({'summary_a':sa,'verdict_a':va,'summary_b':sb,'verdict_b':vb},indent=1))
if __name__=='__main__':main()
