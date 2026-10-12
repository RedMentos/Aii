"""Isolated candidate 2 (thread L, 2026-10-12): nearest-prediction residual + tolerance ceiling for corollary attribution.

Candidate 1 (`corollary_ceiling_candidate.py`, FAIL) showed that `selfmodel.attribute` reports the residual of the FIRST
open own action on a channel; with several open actions the residual is large although the matching action only missed
slightly. Candidate 2: when `attribute` returns MIXED, recompute the residual against the NEAREST open numeric prediction
on that channel (same window rules: start <= t <= start + window x DELAY_FACTOR), report that action, and re-label
EXTERNAL only if even the nearest residual exceeds K x its tolerance. `selfmodel.py` unchanged.

PREREG (fixed before the first run): identical streams, K grid, calibration/test seeds and pass criteria as candidate 1
(`corollary_ceiling_candidate.PREREG['pass']`). Also reported without ceiling (K = inf) to separate the two effects.
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

PREREG=dict(C1.PREREG,schema='COROLLARY_NEAREST_PREREG_V1',change='residual against nearest open numeric prediction on the channel, then ceiling K',
            also_reported='K = inf (nearest residual only)')

def attribute_nearest(open_corollaries,obs,k):
    a=S.attribute(open_corollaries,obs)
    if a['class']!='MIXED' or not isinstance(obs.get('value'),(int,float)):return a
    t=obs.get('t');best=None
    for c in open_corollaries:
        start=c['issued_at'];w=c.get('window_s',S.DEFAULT_WINDOW_S)
        if t<start:continue
        for p in c['predicted_observations']:
            pv=p.get('value')
            if p['channel']!=obs['channel'] or not isinstance(pv,(int,float)) or isinstance(pv,bool):continue
            if t>start+p.get('window_s',w)*S.DELAY_FACTOR:continue
            tol=p.get('tolerance');tol=abs(pv)*.5 if tol is None else tol;res=obs['value']-pv
            if best is None or abs(res)<abs(best[1]):best=(c['action_id'],res,tol)
    if best is None:return a
    if abs(best[1])>k*best[2]:
        return {'class':'EXTERNAL','reason':'far_outside_own_prediction','action_ids':[],'residual':None,'ceiling_k':k,'own_residual':best[1]}
    return dict(a,action_ids=[best[0]],residual=best[1],reason='nearest_partial_or_mismatched_outcome')

def score(st,k=None):
    acts,obs=st;by={'SELF':[],'MIXED':[],'EXTERNAL':[]};fm=[];missed=[]
    for o in obs:
        open_=[c for c in acts if c['issued_at']<=o['t']<=c['issued_at']+c['window_s']*S.DELAY_FACTOR]
        q={x:o[x] for x in ('channel','value','t')}
        c=(S.attribute(open_,q) if k is None else attribute_nearest(open_,q,k))['class']
        by[o['truth']].append(c==o['truth'])
        if o['truth']=='EXTERNAL':fm.append(c=='MIXED')
        if o['truth']=='MIXED':missed.append(c!='MIXED')
    return {'balanced_accuracy':round(_mean([_mean(v) for v in by.values()]),5),'false_mixed_rate':round(_mean(fm),5),
            'missed_failure_rate':round(_mean(missed),5),'per_class':{x:round(_mean(v),4) for x,v in by.items()}}

def run():
    cal={k:_mean([score(C1.stream(s),k)['balanced_accuracy'] for s in C1.CAL_SEEDS]) for k in C1.KS}
    best=max(C1.KS,key=lambda k:(round(cal[k],6),k));TS=C1.TEST_SEEDS
    test={n:{s:{'baseline':score(C1.stream(s,hi)),'candidate':score(C1.stream(s,hi),best),'nearest_only':score(C1.stream(s,hi),math.inf)} for s in TS}
          for n,hi in (('standard',6.),('stress',40.))}
    std,stress=test['standard'],test['stress']
    c1=sum(std[s]['candidate']['balanced_accuracy']>std[s]['baseline']['balanced_accuracy'] for s in TS)
    c2={n:sum(test[n][s]['candidate']['false_mixed_rate']<test[n][s]['baseline']['false_mixed_rate'] for s in TS) for n in test}
    rise=_mean([stress[s]['candidate']['missed_failure_rate']-stress[s]['baseline']['missed_failure_rate'] for s in TS])
    worse=sum(stress[s]['candidate']['balanced_accuracy']<stress[s]['baseline']['balanced_accuracy'] for s in TS)
    ok=c1>=4 and all(v>=4 for v in c2.values()) and rise<=.10 and worse<=1
    m=lambda n,arm,key:round(_mean([test[n][s][arm][key] for s in TS]),4)
    return {'prereg':PREREG,'calibration':{str(k):round(v,5) for k,v in cal.items()},'k':best,'test':test,
            'criteria':{'standard_bal_acc_wins_of_5':c1,'false_mixed_wins_of_5':c2,'stress_missed_failure_rise':round(rise,4),'stress_bal_acc_worse_seeds':worse},
            'means':{n:{arm:{key:m(n,arm,key) for key in ('balanced_accuracy','false_mixed_rate','missed_failure_rate')} for arm in ('baseline','candidate','nearest_only')} for n in test},
            'verdict':'PASS' if ok else 'FAIL','claim_limit':'synthetic digital observations, BOOT tolerances/windows; isolated candidate, selfmodel.py unchanged'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1,default=str))
    print(r['verdict'],'K=',r['k'],r['criteria']);print(json.dumps(r['means'],indent=1))
