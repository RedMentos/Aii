"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_WORLD_MODEL (WP-T8 §7.2.2, thread L,
2026-10-12): does the counterfactual confidence (coverage x OOD x ensemble spread) tell good from bad counterfactuals?

Real `world_model.fit` (bootstrap ridge ensemble, persisted state) and `world_model.counterfactual` on a fresh SQLite
store; only `world_model.transitions` is fed synthetic own transitions instead of reading the actions table.
Hidden world: per action a, y = base_a + w_a . s + q_a x (input length)^2 + noise (.1) for log duration / success /
log chars (the quadratic term makes linear extrapolation wrong far from the data). Collection policy (300 transitions):
simple only for short inputs, detail only for long inputs, gist anywhere, both rarely (5 %); resource state mostly NORMAL.
Queries: 400 random (input length, resource state, hour, action) over the whole space; error = mean absolute difference
between the predicted and the noise-free true outcome over the 3 targets.
Scores (rank quality of a confidence for its own query error), per seed: Spearman correlation between confidence and
-error. Arms:
  confidence     the real counterfactual confidence
  samples_only   1 - exp(-samples/COVER_N) for the queried action (coverage count only)
  spread_only    1 / (1 + spread/SPREAD_REF) (ensemble disagreement only)
  random         uniform random confidence
PREREG (fixed before the first run): primary = Spearman(confidence, -error). "helps" only if confidence beats
samples_only, spread_only and random in >= 4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED.
Also reported: mean error of SIMULATION_SUPPORTED vs SIMULATION_UNCERTAIN labels.
Claim limit: synthetic own transitions with a biased collection policy, BOOT coverage knobs; no causal claim.
"""
import json
import math
import random
import sys
import tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13 import world_model as WM

PREREG={'schema':'ABLATION_WORLD_MODEL_CONFIDENCE_PREREG_V1','seeds':list(SEEDS),'transitions':300,'queries':400,'noise':.1,
        'policy':'simple short inputs only, detail long inputs only, gist anywhere, both 5 %','primary':'Spearman(confidence, -error)',
        'win_rule':'confidence beats samples_only, spread_only and random in >=4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
N=300;Q=400;NOISE=.1;ARMS=('confidence','samples_only','spread_only','random')
RES=('NORMAL','PRESSURE','RECOVERY')

def world(seed):
    rng=random.Random(seed)
    W={a:{'b':[rng.uniform(0,2),rng.uniform(.4,.9),rng.uniform(.3,.8)],'w':[[rng.uniform(-1,1) for _ in range(4)] for _ in range(3)],
          'q':[rng.uniform(-3,3),rng.uniform(-.8,.8),rng.uniform(-2,2)]} for a in WM.ACTIONS}
    def truth(s,a):
        p=W[a];return [p['b'][k]+sum(x*y for x,y in zip(p['w'][k],s))+p['q'][k]*s[0]**2 for k in range(3)]
    def state():
        chars=int(math.exp(rng.uniform(math.log(5),math.log(3000))));res=rng.choices(RES,(.85,.1,.05))[0]
        return WM.state_vec(chars,res,rng.uniform(0,24))
    T=[]
    while len(T)<N:
        s=state();u=rng.random()
        a='both' if u<.05 else ('gist' if u<.4 else ('simple' if s[0]<.45 else ('detail' if s[0]>.55 else None)))
        if a is None:continue
        T.append({'action_id':f'a{len(T)}','s':s,'a':a,'y':[v+rng.gauss(0,NOISE) for v in truth(s,a)],'latent':None})
    queries=[]
    for _ in range(Q):
        s=WM.state_vec(int(math.exp(rng.uniform(math.log(5),math.log(3000)))),rng.choice(RES),rng.uniform(0,24));a=rng.choice(WM.ACTIONS)
        queries.append({'s':s,'a':a,'truth':truth(s,a)})
    return T,queries

def spearman(x,y):
    def ranks(v):
        o=sorted(range(len(v)),key=lambda i:v[i]);r=[0.]*len(v);i=0
        while i<len(o):
            j=i
            while j+1<len(o) and v[o[j+1]]==v[o[i]]:j+=1
            for k in range(i,j+1):r[o[k]]=(i+j)/2
            i=j+1
        return r
    rx,ry=ranks(x),ranks(y);mx,my=_mean(rx),_mean(ry)
    num=sum((a-mx)*(b-my) for a,b in zip(rx,ry));den=math.sqrt(sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))
    return num/den if den else 0.

def _scored_counterfactual(cf):
    """Only finite, complete predictions may enter a numerical error ranking.

    An explicit World Model abstention has no error observation. Inventing a
    penalty (or zero error) would change the historical preregistered metric.
    """
    if type(cf) is not dict or type(cf.get('prediction')) is not dict:
        return None
    try:
        pred=[cf['prediction'][t] for t in WM.TARGETS]
        cov=cf['coverage']
        samples=cov['samples']
        spread=cf['model_spread']
        confidence=cf['confidence']
        label=cf['label']
    except (KeyError,TypeError,IndexError):
        return None
    finite=lambda x:type(x) in (int,float) and math.isfinite(x)
    if (type(cov) is not dict or
        not all(finite(x) for x in pred) or
        not finite(samples) or samples<0 or
        not finite(spread) or spread<0 or
        not finite(confidence) or not 0<=confidence<=1 or
        label not in ('SIMULATION_SUPPORTED','SIMULATION_UNCERTAIN')):
        return None
    return pred, samples, spread, confidence, label


def run_seed(seed):
    T,queries=world(seed);rng=random.Random(seed*41+3)
    rows=[];abstentions={}
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d))
        try:
            with mock.patch.object(WM,'transitions',lambda store,limit=WM.MAX_ROWS:T):
                st=WM.fit(store,rng_seed=seed)
            for q in queries:
                cf=WM.counterfactual(store,q['s'],q['a'])
                scored=_scored_counterfactual(cf)
                if scored is None:
                    reason=(cf.get('reason') if type(cf) is dict else None)
                    if type(reason) is not str or not reason or len(reason)>80:
                        reason='INVALID_SCORING_FIELDS'
                    abstentions[reason]=abstentions.get(reason,0)+1
                    continue
                pred,samples,spread,confidence,label=scored
                err=_mean([abs(p-t) for p,t in zip(pred,q['truth'])])
                if not math.isfinite(err):
                    abstentions['NONFINITE_ERROR']=abstentions.get('NONFINITE_ERROR',0)+1
                    continue
                rows.append({'err':err,'confidence':confidence,
                             'samples_only':1-math.exp(-samples/WM.COVER_N),
                             'spread_only':1/(1+spread/WM.SPREAD_REF),
                             'random':rng.random(),'label':label})
        finally:
            store.close()
    neg=[-r['err'] for r in rows]
    sup=[r['err'] for r in rows if r['label']=='SIMULATION_SUPPORTED']
    unc=[r['err'] for r in rows if r['label']=='SIMULATION_UNCERTAIN']
    return {**{a:{'primary':round(spearman([r[a] for r in rows],neg),5) if len(rows)>=2 else None}
               for a in ARMS},
            'queries_n':len(queries),'evaluated_n':len(rows),
            'abstained_n':sum(abstentions.values()),
            'abstention_reasons':dict(sorted(abstentions.items())),
            'labels':{'supported_n':len(sup),'uncertain_n':len(unc),
                      'supported_mean_err':round(_mean(sup),4) if sup else None,
                      'uncertain_mean_err':round(_mean(unc),4) if unc else None},
            'fit_status':st['status'],'counts':st['counts']}


def run_all(seeds=SEEDS):
    per={s:run_seed(s) for s in seeds}
    complete=[s for s in seeds if per[s]['abstained_n']==0 and per[s]['evaluated_n']>=2]
    incomplete=[s for s in seeds if s not in complete]
    wins={a:sum(per[s]['confidence']['primary']>per[s][a]['primary'] for s in complete)
          for a in ARMS[1:]}
    beat=[a for a,n in wins.items() if n>=4]
    lab=sum(per[s]['labels']['supported_mean_err']<per[s]['labels']['uncertain_mean_err']
            for s in seeds if per[s]['labels']['supported_mean_err'] is not None
            and per[s]['labels']['uncertain_mean_err'] is not None)
    summary={}
    for a in ARMS:
        vals=[per[s][a]['primary'] for s in complete]
        summary[a]={'mean':round(_mean(vals),4) if vals else None,
                    'sd':round(_sd(vals),4) if vals else None}
    return {'prereg':PREREG,'per_seed':per,'wins_of_5':wins,
            'complete_seeds':complete,'incomplete_seeds':incomplete,
            'supported_label_lower_error_of_5':lab,'summary':summary,
            'verdict':('INCOMPLETE_ABSTENTION' if incomplete else
                       ('SUPPORTED_SYNTHETIC' if len(beat)==3 else
                        ('PARTIAL' if beat else 'NOT_SUPPORTED'))),
            'claim_limit':('Only fully scored seeds meet original preregistration; '
                           'abstained queries have no observed error and cannot be ranked. '
                           'Synthetic own transitions with biased policy; no causal claim')}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['wins_of_5'],r['summary'],'labels',r['supported_label_lower_error_of_5'])
