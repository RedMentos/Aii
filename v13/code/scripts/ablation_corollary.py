"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_SELFMODEL /
F4_SELF_WORLD_OBSERVATIONS (WP-N9 corollary copy, §7.5, §85.7; thread L, 2026-10-12).

  A) Self/world attribution helps   selfmodel.attribute (corollary: channel + predicted value + window)
       vs  no_corollary  (every observation EXTERNAL),
           temporal_only (anything while an own action is open is SELF),
           channel_only  (an open own action on the same channel makes it SELF; value ignored).
     Primary: balanced accuracy over the true classes SELF / MIXED / EXTERNAL (UNCLEAR counts as a miss and is
     reported as abstention). Secondary: false-SELF rate on external events (hides real world change) and
     missed-failure rate (own action failed but not MIXED).
  B) Corollary sensory attenuation helps   selfmodel.interoception with own_active=True (self-caused RAM load attenuated
       in the salience channel by ATTENUATION)
       vs  none (own_active=False), full subtraction (attenuation 1.0), random attenuation share.
     Primary: AUROC of the RAM-salience value for "external pressure rose" against "own load rose" events.
     Hard check: the raw safety signal is identical in every arm.

The real, unchanged pure functions are driven; stream generation and scoring are harness code. Streams are open-loop
and identical for all arms of a seed. PREREG (fixed before the first run): "helps" only if V13 beats every control on
the primary metric in >= 4 of 5 seeds; PARTIAL if it beats some; NOT_SUPPORTED if none.
Claim limit: synthetic digital observations and RAM snapshots, BOOT tolerances/windows; no claim of self-awareness.
"""
import contextlib
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd
from v13 import selfmodel as S

PREREG={'schema':'ABLATION_COROLLARY_PREREG_V1','seeds':list(SEEDS),'win_rule':'v13 better than control on the primary metric in >=4/5 seeds, for every control',
        'verdicts':{'SUPPORTED_SYNTHETIC':'beats every control','PARTIAL':'beats at least one control','NOT_SUPPORTED':'beats none'},
        'attribution':{'primary':'balanced accuracy over true SELF/MIXED/EXTERNAL (higher is better)','secondary':['false_self_rate','missed_failure_rate','abstention']},
        'attenuation':{'primary':'AUROC external-vs-own RAM salience (higher is better)','hard_check':'raw safety signals identical across arms'}}

CHANNELS=('file_count','counter','net_bytes');T=600
ATTR_ARMS=('v13','no_corollary','temporal_only','channel_only')
ATT_ARMS=('v13','none','full','random')

def attr_stream(seed):
    """Own actions (p=.15 per step) open a corollary predicting one channel value; 80 % succeed (observation equals the
    prediction within tolerance, after a delay up to the window), 20 % fail (value off by 3-6x the tolerance).
    External events (p=.25 per step) hit a random channel with a value drawn far from any prediction, also while own
    actions are open. Ground truth comes from the generator."""
    rng=random.Random(seed);acts=[];obs=[];aid=0
    for t in range(T):
        if rng.random()<.15:
            ch=rng.choice(CHANNELS);v=float(rng.randint(10,100));tol=2.;w=float(rng.randint(3,10))
            aid+=1;c={'action_id':f'a{aid}','issued_at':float(t),'window_s':w,'affected':[ch],'predicted_observations':[{'channel':ch,'value':v,'tolerance':tol,'window_s':w}]}
            acts.append(c);ok=rng.random()<.8;d=rng.uniform(.5,w)
            val=v+rng.uniform(-tol*.9,tol*.9) if ok else v+rng.choice((-1,1))*rng.uniform(3*tol,6*tol)
            obs.append({'channel':ch,'value':val,'t':t+d,'truth':'SELF' if ok else 'MIXED','action_id':c['action_id']})
        if rng.random()<.25:
            obs.append({'channel':rng.choice(CHANNELS),'value':float(rng.randint(500,900)),'t':t+rng.random(),'truth':'EXTERNAL','action_id':None})
    obs.sort(key=lambda o:o['t']);return acts,obs

def classify(arm,acts,o):
    open_=[c for c in acts if c['issued_at']<=o['t']<=c['issued_at']+c['window_s']*S.DELAY_FACTOR]
    if arm=='v13':return S.attribute(open_,{k:o[k] for k in ('channel','value','t')})['class']
    if arm=='no_corollary':return 'EXTERNAL'
    if arm=='temporal_only':return 'SELF' if any(c['issued_at']<=o['t']<=c['issued_at']+c['window_s'] for c in open_) else 'EXTERNAL'
    if arm=='channel_only':return 'SELF' if any(o['channel'] in c['affected'] and o['t']<=c['issued_at']+c['window_s'] for c in open_) else 'EXTERNAL'
    raise ValueError(arm)

def run_attr(stream,arm):
    acts,obs=stream;by={'SELF':[],'MIXED':[],'EXTERNAL':[]};abst=0
    for o in obs:
        c=classify(arm,acts,o);by[o['truth']].append(c==o['truth']);abst+=c=='UNCLEAR'
    ext=[o for o in obs if o['truth']=='EXTERNAL'];fails=[o for o in obs if o['truth']=='MIXED']
    return {'primary':round(_mean([_mean(v) for v in by.values()]),5),'per_class_accuracy':{k:round(_mean(v),4) for k,v in by.items()},
            'false_self_rate':round(_mean([classify(arm,acts,o)=='SELF' for o in ext]),5),
            'missed_failure_rate':round(_mean([classify(arm,acts,o)!='MIXED' for o in fails]),5),'abstention':round(abst/len(obs),5),'n':len(obs)}

CFG={'minimum_free_mb':300,'thermal_limit_c':45,'deadline_seconds':30}
GB=1024**3

def att_stream(seed,n=400):
    """RAM snapshots of a 6 GB phone. Each step raises used memory either by our own bodies (label OWN, own process RSS
    grows by the same amount) or by another app (label EXTERNAL, own RSS unchanged), from a random baseline."""
    rng=random.Random(seed);out=[]
    for _ in range(n):
        total=6*GB;base_used=rng.uniform(3.5,4.3)*GB;own0=rng.uniform(.3,1.)*GB;inc=rng.uniform(.8,1.4)*GB;ext=rng.random()<.5
        own=own0 if ext else own0+inc;used=base_used+inc
        out.append({'label':'EXTERNAL' if ext else 'OWN','snap':{'mem_total_bytes':int(total),'mem_available_bytes':int(total-used),'processes':[{'rss_bytes':int(own)}]}})
    return out

@contextlib.contextmanager
def _att(v):
    old=S.ATTENUATION;S.ATTENUATION=v
    try:yield
    finally:S.ATTENUATION=old

def _auroc(pos,neg):
    pairs=[(1. if p>q else .5 if p==q else 0.) for p in pos for q in neg];return _mean(pairs)

def run_att(stream,arm,seed=0):
    rng=random.Random(seed);sal={'EXTERNAL':[],'OWN':[]};raw=[]
    for ev in stream:
        if arm=='random':
            with _att(rng.random()):x=S.interoception(ev['snap'],CFG,own_active=True)
        elif arm=='full':
            with _att(1.):x=S.interoception(ev['snap'],CFG,own_active=True)
        else:x=S.interoception(ev['snap'],CFG,own_active=arm=='v13')
        sal[ev['label']].append(x['salience']['ram_pressure']);raw.append(x['signals']['ram_pressure'])
    return {'primary':round(_auroc(sal['EXTERNAL'],sal['OWN']),5),'mean_salience':{k:round(_mean(v),4) for k,v in sal.items()},'raw_signals':raw}

def _verdict(per_seed,arms,v='v13'):
    wins={a:sum(1 for s in per_seed if per_seed[s][v]['primary']>per_seed[s][a]['primary']) for a in arms if a!=v}
    beat=[a for a,n in wins.items() if n>=4]
    return {'wins_of_5':wins,'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==len(wins) else ('PARTIAL' if beat else 'NOT_SUPPORTED'),'beats':beat}

def _summary(per_seed,arms):
    keys=[k for k,v in next(iter(per_seed.values()))['v13'].items() if isinstance(v,(int,float)) and k!='n']
    return {a:{k:{'mean':round(_mean([per_seed[s][a][k] for s in per_seed]),5),'sd':round(_sd([per_seed[s][a][k] for s in per_seed]),5)} for k in keys} for a in arms}

def run_all(seeds=SEEDS):
    attr={};att={};safety_identical=True
    for s in seeds:
        st=attr_stream(s);attr[s]={a:run_attr(st,a) for a in ATTR_ARMS}
        st=att_stream(s);row={a:run_att(st,a,seed=s) for a in ATT_ARMS}
        safety_identical&=all(row[a]['raw_signals']==row['v13']['raw_signals'] for a in ATT_ARMS)
        for a in row:row[a].pop('raw_signals')
        att[s]=row
    return {'prereg':PREREG,'seeds':list(seeds),
            'attribution':{'arms':ATTR_ARMS,'per_seed':attr,'summary':_summary(attr,ATTR_ARMS),**_verdict(attr,ATTR_ARMS)},
            'attenuation':{'arms':ATT_ARMS,'per_seed':att,'summary':_summary(att,ATT_ARMS),'safety_raw_identical':safety_identical,**_verdict(att,ATT_ARMS)},
            'claim_limit':'synthetic digital observations and RAM snapshots, BOOT tolerances/windows/attenuation; no claim of self-awareness'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    out=Path(sys.argv[1]);r=run_all();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    for part in ('attribution','attenuation'):
        print(part,r[part]['verdict'],r[part]['wins_of_5'])
        for a,v in r[part]['summary'].items():print(' ',a,{k:x['mean'] for k,x in v.items()})
