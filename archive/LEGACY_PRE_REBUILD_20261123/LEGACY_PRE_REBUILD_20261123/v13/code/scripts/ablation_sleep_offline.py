"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_SLEEP_OFFLINE (WP-S7 step 2,
thread L, 2026-10-12): does the sleep-time replay of the cerebellar fast-forward predictor lower next-day error?

Real `fastforward.FastForward` (online NLMS `learn`, WP-S7 replay buffer, `consolidate` with its held-out guard) on a
fresh SQLite store. Turns carry the predictor's 14-feature layout (bias, input length, route/wake one-hots, memory,
effort, novelty, conflict) drawn at random; hidden per-seed linear targets give log duration (+ noise .3), success
(Bernoulli of a clipped linear p) and log chars (+ noise .3). 10 days x 60 turns; sleep runs after each day.
Arms (same turns per seed):
  sleep            consolidate() after each day (real, guarded: kept only if held-out error does not rise)
  no_sleep         online learning only
  shuffled_replay  consolidate() after each day on a replay buffer whose outcomes are shuffled across turns (same
                   passes, no real outcome structure); the real buffer is restored afterwards
  unguarded        harness copy of consolidate() that always keeps the result (shows what the guard buys)
Streams: `stationary` (fixed hidden weights) and `drift` (hidden weights redrawn after day 5; reported).
PREREG (fixed before the first run): primary = mean summed absolute prediction error (3 targets, measured before each
online update) over days 2-10 on `stationary`. "helps" only if sleep beats no_sleep and shuffled_replay in >= 4/5 seeds
-> SUPPORTED_SYNTHETIC; one -> PARTIAL; none -> NOT_SUPPORTED. sleep vs unguarded is reported on both streams.
Claim limit: synthetic linear outcome process, BOOT LR / epochs / holdout; digest and TTT staging (steps 1, 3) untested.
"""
import json
import random
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13 import fastforward as FF

PREREG={'schema':'ABLATION_SLEEP_OFFLINE_PREREG_V1','seeds':list(SEEDS),'days':10,'turns_per_day':60,'noise':.3,
        'streams':{'stationary':'fixed hidden weights','drift':'hidden weights redrawn after day 5'},
        'primary':'mean summed abs prediction error (before each online update), days 2-10, stationary',
        'win_rule':'sleep beats no_sleep and shuffled_replay in >=4/5 seeds -> SUPPORTED_SYNTHETIC; one -> PARTIAL; none -> NOT_SUPPORTED'}
DAYS=10;PER_DAY=60;NOISE=.3;ARMS=('sleep','no_sleep','shuffled_replay','unguarded')

def hidden(rng):
    n=len(FF.FEATURES)
    return {'log_duration':[rng.uniform(0,2)]+[rng.uniform(-1,1) for _ in range(n-1)],'success':[.6]+[rng.uniform(-.3,.3) for _ in range(n-1)],
            'log_chars':[rng.uniform(4,6)]+[rng.uniform(-1.5,1.5) for _ in range(n-1)]}

def turns(seed,stream):
    rng=random.Random(seed);w=hidden(rng);out=[]
    for d in range(DAYS):
        if stream=='drift' and d==DAYS//2:w=hidden(rng)
        day=[]
        for _ in range(PER_DAY):
            r=rng.randrange(4);k=rng.randrange(4)
            x=[1.,rng.uniform(.2,.9),*(float(i==r) for i in range(4)),*(float(i==k) for i in range(4)),float(rng.random()<.4),rng.random(),rng.random(),rng.random()]
            dot=lambda t:sum(a*b for a,b in zip(w[t],x))
            p=FF.clip(dot('success'))
            day.append({'x':x,'duration_s':2.718281828**(dot('log_duration')+rng.gauss(0,NOISE)),'status':'FINAL' if rng.random()<p else 'ERROR',
                        'chars':max(1,int(2.718281828**(dot('log_chars')+rng.gauss(0,NOISE))))})
        out.append(day)
    return out

def consolidate_unguarded(ff,epochs=3,lr=FF.LR/3,holdout=.2):
    """Harness copy of FastForward.consolidate without the held-out guard (same split, passes and rate)."""
    st,_=ff._load();buf=st.get('replay',[])
    if len(buf)<10:return
    k=max(2,int(len(buf)*holdout));train=buf[:-k];w={t:list(v) for t,v in st['w'].items()}
    for _ in range(epochs):
        for s in train:
            norm=1e-6+sum(v*v for v in s['x'])
            for t in FF.TARGETS:
                e=s['y'][t]-ff._dot(w[t],s['x']);w[t]=[a+lr*e*xi/norm for a,xi in zip(w[t],s['x'])]
    ff._mutate(lambda st2:st2.__setitem__('w',w))

def shuffled_consolidate(ff,rng):
    st,_=ff._load();real=st.get('replay',[]);ys=[s['y'] for s in real];rng.shuffle(ys)
    ff._mutate(lambda st2:st2.__setitem__('replay',[{'x':s['x'],'y':y} for s,y in zip(real,ys)]))
    rep=ff.consolidate()
    ff._mutate(lambda st2:st2.__setitem__('replay',real))
    return rep

def run_arm(days,arm,seed):
    rng=random.Random(seed*29+7);errs=[];kept=0
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d));ff=FF.FastForward(store)
        for di,day in enumerate(days):
            for i,t in enumerate(day):
                r=ff.learn(f'e{di}_{i}',t['x'],t['duration_s'],t['status'],t['chars'])
                if di>=1:errs.append(sum(abs(v) for v in r['errors'].values()))
            if arm=='sleep':kept+=ff.consolidate().get('status')=='KEPT'
            elif arm=='shuffled_replay':kept+=shuffled_consolidate(ff,rng).get('status')=='KEPT'
            elif arm=='unguarded':consolidate_unguarded(ff);kept+=1
        store.close()
    return {'primary':round(_mean(errs),5),'sleeps_kept':kept}

def run_all(seeds=SEEDS):
    out={}
    for stream in PREREG['streams']:
        per={s:{a:run_arm(turns(s,stream),a,s) for a in ARMS} for s in seeds}
        wins={a:sum(per[s]['sleep']['primary']<per[s][a]['primary'] for s in seeds) for a in ARMS[1:]}
        out[stream]={'per_seed':per,'wins_of_5':wins,
                     'summary':{a:{k:{'mean':round(_mean([per[s][a][k] for s in seeds]),4),'sd':round(_sd([per[s][a][k] for s in seeds]),4)} for k in ('primary','sleeps_kept')} for a in ARMS}}
    w=out['stationary']['wins_of_5'];beat=[a for a in ('no_sleep','shuffled_replay') if w[a]>=4]
    return {'prereg':PREREG,'streams':out,'beats_on_stationary':beat,
            'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==2 else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic linear outcome process, BOOT LR/epochs/holdout; digest and TTT staging untested'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'])
    for k,v in r['streams'].items():print(k,v['wins_of_5'],{a:{m:x['mean'] for m,x in d.items()} for a,d in v['summary'].items()})
