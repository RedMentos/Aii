"""Isolated candidate 3 (thread L, 2026-10-12) after corollary candidates 1+2 (FAIL): nearest open prediction, and a
value far outside it becomes UNCLEAR (abstain) instead of EXTERNAL. `selfmodel.py` is not changed here.

Rationale (candidate 2 README): an own failure 20-40x off looks like a foreign event by value alone. Labelling it
EXTERNAL teaches "foreign" for an own failure; MIXED (today) teaches an own error for a foreign event. UNCLEAR learns
neither (selfmodel.observe only learns from MIXED/SELF evidence).

Fixed before the first run: K = 20 (the calibration result of candidate 2; no new calibration), same streams and seeds.
Score per observation: harmful = foreign event labelled SELF/MIXED, own failure labelled SELF/EXTERNAL, own success
labelled MIXED/EXTERNAL; UNCLEAR = abstention (not harmful, not learned).
PREREG, test seeds 13-17, PASS only if
  (1) harmful rate lower than unchanged `attribute` in >= 4/5 seeds on both streams,
  (2) harmful rate higher than candidate 2 (EXTERNAL variant) in at most 1/5 seeds on both streams,
  (3) standard stream: mean abstention on own failures <= .05 (ordinary own failures are still learned).
  Otherwise FAIL. Abstention rates per class are reported on both streams.
Claim limit: synthetic digital observations, BOOT tolerances/windows.
"""
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.ablation99 import _mean
from v13 import selfmodel as S
import corollary_ceiling_candidate as C1
import corollary_nearest_candidate as C2

K=20
PREREG={'schema':'COROLLARY_UNCLEAR_PREREG_V1','k':K,'test_seeds':list(C1.TEST_SEEDS),'streams':C1.PREREG['streams'],
        'harmful':'foreign->SELF/MIXED, own failure->SELF/EXTERNAL, own success->MIXED/EXTERNAL; UNCLEAR = abstention',
        'pass':['harmful < unchanged in >=4/5 on both streams','harmful > candidate 2 in <=1/5 on both streams','standard: own-failure abstention mean <= .05']}

def attribute_unclear(open_corollaries,obs,k=K):
    a=C2.attribute_nearest(open_corollaries,obs,k)
    if a.get('reason')=='far_outside_own_prediction':
        return {'class':'UNCLEAR','reason':'far_outside_own_prediction','action_ids':[],'residual':None,'ceiling_k':k,'own_residual':a['own_residual']}
    return a

HARM={'EXTERNAL':{'SELF','MIXED'},'MIXED':{'SELF','EXTERNAL'},'SELF':{'MIXED','EXTERNAL'}}
def score(st,fn):
    acts,obs=st;harm=[];abst={'SELF':[],'MIXED':[],'EXTERNAL':[]}
    for o in obs:
        open_=[c for c in acts if c['issued_at']<=o['t']<=c['issued_at']+c['window_s']*S.DELAY_FACTOR]
        c=fn(open_,{x:o[x] for x in ('channel','value','t')})['class']
        harm.append(c in HARM[o['truth']]);abst[o['truth']].append(c=='UNCLEAR')
    return {'harmful_rate':round(_mean(harm),5),'abstention':{x:round(_mean(v),4) for x,v in abst.items()}}

ARMS={'unchanged':lambda o,q:S.attribute(o,q),'candidate2':lambda o,q:C2.attribute_nearest(o,q,K),'candidate3':attribute_unclear}

def run():
    TS=C1.TEST_SEEDS
    test={n:{s:{a:score(C1.stream(s,hi),fn) for a,fn in ARMS.items()} for s in TS} for n,hi in (('standard',6.),('stress',40.))}
    H=lambda n,s,a:test[n][s][a]['harmful_rate']
    c1={n:sum(H(n,s,'candidate3')<H(n,s,'unchanged') for s in TS) for n in test}
    c2={n:sum(H(n,s,'candidate3')>H(n,s,'candidate2') for s in TS) for n in test}
    c3=_mean([test['standard'][s]['candidate3']['abstention']['MIXED'] for s in TS])
    ok=all(v>=4 for v in c1.values()) and all(v<=1 for v in c2.values()) and c3<=.05
    means={n:{a:{'harmful_rate':round(_mean([H(n,s,a) for s in TS]),4),'abstention':{x:round(_mean([test[n][s][a]['abstention'][x] for s in TS]),4) for x in ('SELF','MIXED','EXTERNAL')}} for a in ARMS} for n in test}
    return {'prereg':PREREG,'test':test,'means':means,'criteria':{'harm_below_unchanged':c1,'harm_above_candidate2':c2,'standard_own_failure_abstention':round(c3,4)},
            'verdict':'PASS' if ok else 'FAIL','claim_limit':'synthetic digital observations, BOOT tolerances/windows; isolated candidate, selfmodel.py unchanged'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['criteria']);print(json.dumps(r['means'],indent=1))
