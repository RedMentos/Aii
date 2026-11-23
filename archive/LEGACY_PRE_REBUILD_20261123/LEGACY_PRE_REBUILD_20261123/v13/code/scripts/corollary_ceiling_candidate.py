"""Isolated candidate (thread L, 2026-10-12): corollary attribution with a tolerance ceiling.

Finding of `ablation_corollary.py` (bench-results/corollary-20261012): `selfmodel.attribute` labels 54-66 % of external
events that hit a channel with an open own action as MIXED (own failure). `SelfModel.observe` turns MIXED into a
world-prediction-error modulator of about 1, so a foreign change is learned as an error of the own action.

Candidate: keep `attribute` unchanged; when it returns MIXED with a numeric residual larger than K x the prediction's
tolerance, re-label the observation EXTERNAL (reason `far_outside_own_prediction`). `selfmodel.py` is not changed here.

PREREG (fixed before the first run):
  K grid {4, 6, 8, 12, 20}; K is chosen on calibration seeds 101-105 of the standard stream only (max balanced accuracy,
  ties -> larger K = more conservative). Test on seeds 13-17:
    standard stream  own failures off by 3-6 x tolerance (as in ablation_corollary)
    stress stream    own failures off by 3-40 x tolerance (heavy tail: some own failures look "far off")
  The candidate passes only if, on the test seeds,
    (1) balanced accuracy beats unchanged `attribute` in >= 4/5 seeds on the standard stream,
    (2) false-MIXED rate on external events is lower in >= 4/5 seeds on both streams, and
    (3) on the stress stream the missed-failure rate rises by at most .10 (mean over seeds) and balanced accuracy is not
        lower in more than 1/5 seeds.
  Otherwise FAIL; the trade-off is reported either way.
Claim limit: synthetic digital observations, BOOT tolerances/windows.
"""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.ablation99 import _mean
from v13 import selfmodel as S
import ablation_corollary as AC

KS=(4,6,8,12,20);CAL_SEEDS=(101,102,103,104,105);TEST_SEEDS=(13,14,15,16,17)
PREREG={'schema':'COROLLARY_CEILING_PREREG_V1','k_grid':list(KS),'calibration_seeds':list(CAL_SEEDS),'test_seeds':list(TEST_SEEDS),
        'streams':{'standard':'own failures off by 3-6 x tolerance','stress':'own failures off by 3-40 x tolerance'},
        'k_selection':'max balanced accuracy on calibration seeds, standard stream; ties -> larger K',
        'pass':['balanced accuracy > baseline in >=4/5 test seeds (standard)','false-MIXED rate < baseline in >=4/5 test seeds on both streams',
                'stress: mean missed-failure rise <= .10 and balanced accuracy lower in at most 1/5 seeds']}

def stream(seed,fail_hi=6.):
    """Same generator as ablation_corollary.attr_stream; only the own-failure offset range differs."""
    rng=random.Random(seed);acts=[];obs=[];aid=0
    for t in range(AC.T):
        if rng.random()<.15:
            ch=rng.choice(AC.CHANNELS);v=float(rng.randint(10,100));tol=2.;w=float(rng.randint(3,10))
            aid+=1;c={'action_id':f'a{aid}','issued_at':float(t),'window_s':w,'affected':[ch],'predicted_observations':[{'channel':ch,'value':v,'tolerance':tol,'window_s':w}]}
            acts.append(c);ok=rng.random()<.8;d=rng.uniform(.5,w)
            val=v+rng.uniform(-tol*.9,tol*.9) if ok else v+rng.choice((-1,1))*rng.uniform(3*tol,fail_hi*tol)
            obs.append({'channel':ch,'value':val,'t':t+d,'truth':'SELF' if ok else 'MIXED','action_id':c['action_id']})
        if rng.random()<.25:
            obs.append({'channel':rng.choice(AC.CHANNELS),'value':float(rng.randint(500,900)),'t':t+rng.random(),'truth':'EXTERNAL','action_id':None})
    obs.sort(key=lambda o:o['t']);return acts,obs

def attribute_ceiling(open_corollaries,obs,k):
    a=S.attribute(open_corollaries,obs)
    if a['class']!='MIXED' or not isinstance(a.get('residual'),(int,float)):return a
    tol=None
    for c in open_corollaries:
        if c['action_id'] in a['action_ids']:
            for p in c['predicted_observations']:
                if p['channel']==obs['channel'] and isinstance(p.get('value'),(int,float)):
                    tol=p.get('tolerance');tol=abs(p['value'])*.5 if tol is None else tol
    if tol is not None and abs(a['residual'])>k*tol:
        return {'class':'EXTERNAL','reason':'far_outside_own_prediction','action_ids':[],'residual':None,'ceiling_k':k,'own_residual':a['residual']}
    return a

def score(st,k=None):
    acts,obs=st;by={'SELF':[],'MIXED':[],'EXTERNAL':[]};false_mixed=[];missed=[]
    for o in obs:
        open_=[c for c in acts if c['issued_at']<=o['t']<=c['issued_at']+c['window_s']*S.DELAY_FACTOR]
        q={x:o[x] for x in ('channel','value','t')}
        c=(S.attribute(open_,q) if k is None else attribute_ceiling(open_,q,k))['class']
        by[o['truth']].append(c==o['truth'])
        if o['truth']=='EXTERNAL':false_mixed.append(c=='MIXED')
        if o['truth']=='MIXED':missed.append(c!='MIXED')
    return {'balanced_accuracy':round(_mean([_mean(v) for v in by.values()]),5),'false_mixed_rate':round(_mean(false_mixed),5),
            'missed_failure_rate':round(_mean(missed),5),'per_class':{x:round(_mean(v),4) for x,v in by.items()}}

def run():
    cal={k:_mean([score(stream(s),k)['balanced_accuracy'] for s in CAL_SEEDS]) for k in KS}
    best=max(KS,key=lambda k:(round(cal[k],6),k))
    test={}
    for name,hi in (('standard',6.),('stress',40.)):
        test[name]={s:{'baseline':score(stream(s,hi)),'candidate':score(stream(s,hi),best)} for s in TEST_SEEDS}
    std,stress=test['standard'],test['stress']
    c1=sum(std[s]['candidate']['balanced_accuracy']>std[s]['baseline']['balanced_accuracy'] for s in TEST_SEEDS)
    c2={n:sum(test[n][s]['candidate']['false_mixed_rate']<test[n][s]['baseline']['false_mixed_rate'] for s in TEST_SEEDS) for n in test}
    rise=_mean([stress[s]['candidate']['missed_failure_rate']-stress[s]['baseline']['missed_failure_rate'] for s in TEST_SEEDS])
    worse=sum(stress[s]['candidate']['balanced_accuracy']<stress[s]['baseline']['balanced_accuracy'] for s in TEST_SEEDS)
    ok=c1>=4 and all(v>=4 for v in c2.values()) and rise<=.10 and worse<=1
    mean=lambda n,arm,key:round(_mean([test[n][s][arm][key] for s in TEST_SEEDS]),4)
    return {'prereg':PREREG,'calibration':{str(k):round(v,5) for k,v in cal.items()},'k':best,'test':test,
            'criteria':{'standard_bal_acc_wins_of_5':c1,'false_mixed_wins_of_5':c2,'stress_missed_failure_rise':round(rise,4),'stress_bal_acc_worse_seeds':worse},
            'means':{n:{arm:{key:mean(n,arm,key) for key in ('balanced_accuracy','false_mixed_rate','missed_failure_rate')} for arm in ('baseline','candidate')} for n in test},
            'verdict':'PASS' if ok else 'FAIL','claim_limit':'synthetic digital observations, BOOT tolerances/windows; isolated candidate, selfmodel.py unchanged'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],'K=',r['k'],r['criteria']);print(json.dumps(r['means'],indent=1))
