"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_REFLEX (WP-F §5.3 runner-failure
reflex, thread L, 2026-10-12): does the circuit breaker save failed body calls without skipping healthy ones?

Real `reflex.Reflex` (circuit_open / record_failure / record_success, BOOT FAILURES 3, WINDOW_S 600, COOLDOWN_S 120) on a
fresh SQLite store with a simulated clock; the runtime around it mirrors runtime.py (a turn asks circuit_open before the
body call; FINAL -> record_success, ERROR -> record_failure). Only the circuit-breaker reflex is tested here.

One body runner, one call every exp(mean 30 s) for 24 simulated hours. The hidden runner state alternates:
  outage stream   healthy periods exp(mean 2 h, failure p .02) and outages exp(mean 10 min, failure p .95)
  flaky stream    no outages, independent failure p .25 (reported: the breaker should not cost much here)
Cost per turn: a failed body call 1.0 (wasted wait, then the C3 fallback anyway), a skipped call .3 (the turn runs on C3
without the body contribution), a successful call 0.
Arms (same call times and hidden states per seed):
  breaker      the real reflex
  never        no breaker: always call
  skip_all     never call the body (C3 only)
  random       skip the same number of calls as `breaker`, at random turns
PREREG (fixed before the first run): primary = mean cost per turn on the outage stream (lower is better). "helps" only if
breaker beats never, skip_all and random in >= 4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED.
Claim limit: synthetic failure process, one runner, assumed costs, BOOT thresholds; imminent_timeout/critical_resource untested.
"""
import json
import random
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13 import reflex as RX

PREREG={'schema':'ABLATION_REFLEX_BREAKER_PREREG_V1','seeds':list(SEEDS),'hours':24,'mean_gap_s':30,
        'streams':{'outage':'healthy exp(2h, p_fail .02) / outage exp(10min, p_fail .95)','flaky':'iid p_fail .25'},
        'cost':{'failed_call':1.,'skipped_call':.3,'ok_call':0.},'primary':'mean cost per turn on the outage stream (lower is better)',
        'win_rule':'breaker beats never, skip_all and random in >=4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
HOURS=24;GAP=30.;FAIL_COST=1.;SKIP_COST=.3;ROLE='B1_DETAIL';ARMS=('breaker','never','skip_all','random')

def calls(seed,stream):
    """[(t, fails_if_called)] for one simulated day; the failure draw is fixed per call so all arms see the same world."""
    rng=random.Random(seed);t=0.;out=[];end=HOURS*3600.
    state='healthy';switch=rng.expovariate(1/7200.)
    while True:
        t+=rng.expovariate(1/GAP)
        if t>=end:return out
        if stream=='outage':
            while t>=switch:
                state='outage' if state=='healthy' else 'healthy';switch+=rng.expovariate(1/(600. if state=='outage' else 7200.))
            p=.95 if state=='outage' else .02
        else:p=.25
        out.append((t,rng.random()<p))

def run_arm(cs,arm,seed,n_skip=0):
    costs=[];skipped=0
    if arm=='random':skip=set(random.Random(seed*17+1).sample(range(len(cs)),n_skip))
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d));now=[0.];rx=RX.Reflex(store,clock=lambda:now[0])
        for i,(t,fails) in enumerate(cs):
            now[0]=t
            if arm=='breaker':off=rx.circuit_open(ROLE)
            elif arm=='never':off=False
            elif arm=='skip_all':off=True
            else:off=i in skip
            if off:costs.append(SKIP_COST);skipped+=1;continue
            if fails:
                costs.append(FAIL_COST)
                if arm=='breaker':rx.record_failure(ROLE,None,'ERROR')
            else:
                costs.append(0.)
                if arm=='breaker':rx.record_success(ROLE)
        store.close()
    return {'primary':round(_mean(costs),5),'skipped':skipped,'failed_calls':sum(c==FAIL_COST for c in costs),'turns':len(cs)}

def run_all(seeds=SEEDS):
    out={}
    for stream in PREREG['streams']:
        per={}
        for s in seeds:
            cs=calls(s,stream);b=run_arm(cs,'breaker',s)
            per[s]={'breaker':b,**{a:run_arm(cs,a,s,b['skipped']) for a in ARMS[1:]}}
        wins={a:sum(per[s]['breaker']['primary']<per[s][a]['primary'] for s in seeds) for a in ARMS[1:]}
        out[stream]={'per_seed':per,'wins_of_5':wins,
                     'summary':{a:{k:{'mean':round(_mean([per[s][a][k] for s in seeds]),4),'sd':round(_sd([per[s][a][k] for s in seeds]),4)} for k in ('primary','skipped','failed_calls')} for a in ARMS}}
    beat=[a for a,n in out['outage']['wins_of_5'].items() if n>=4]
    return {'prereg':PREREG,'streams':out,'beats_on_outage':beat,
            'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==3 else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic failure process, one runner, assumed costs, BOOT thresholds; imminent_timeout/critical_resource untested'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'])
    for k,v in r['streams'].items():print(k,v['wins_of_5'],{a:{m:x['mean'] for m,x in d.items()} for a,d in v['summary'].items()})
