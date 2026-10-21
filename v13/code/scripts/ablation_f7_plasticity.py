"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row F7_MEASURED_PLASTICITY (§16, thread L,
2026-10-12): does the measured shadow-budget gain (retention failures damp, stable fits reopen) beat fixed budgets?

Real `plasticity.Plasticity` on a fresh SQLite store: every shadow trial goes through the real `budget()` (writes the
PlasticityBudget packet and the effective learning rate) and the real `observe()` (manifest/checkpoint/hash checks, gain
update). The learner around it is a harness: an 8-dim linear regressor trained by one pass of normalized SGD over a
20-sample batch of the current task at step = BASE_STEP x (effective_lr / base_lr). Gates as in the learning loop:
  retention_pass   mean held-out MSE of the previous 3 tasks rises by at most .10 (absolute cap, like retention_max_delta)
  commit_eligible  held-out MSE of the current task falls by at least 2 %
A trial is committed only if both hold; otherwise the weights roll back. 240 trials per seed, a new task every 8 trials.
The task targets drift from the previous task by .10 (calm) or .50 (conflict) per coordinate; phases of 40 trials alternate.
BASE_STEP is calibrated without F7: from {.05, .1, .2, .3, .5}, the step where the two fixed arms full and half are
closest (mean primary over calibration seeds 101-105), so neither fixed budget is trivially right; ties -> smaller step.
Arms (same tasks and batches per seed):
  f7         gain from the real Plasticity state (bounded to [.5, 1])
  full       fixed gain 1 (no damping)
  half       fixed gain .5 (always the floor)
  random     gain uniform in [.5, 1] per trial
PREREG (fixed before the first run): primary = mean held-out MSE of the current and the previous 3 tasks after each trial
(lower is better). "helps" only if f7 beats full, half and random in >= 4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL;
none -> NOT_SUPPORTED.
Claim limit: synthetic linear tasks, harness learner, BOOT gates; no native or shared-layer interference.
"""
import json
import random
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13.common import dumps,file_hash,uid,now
from v13.plasticity import Plasticity

PREREG={'schema':'ABLATION_F7_PLASTICITY_PREREG_V1','seeds':list(SEEDS),'trials':240,'trials_per_task':8,'phase_trials':40,
        'drift':{'calm':.10,'conflict':.50},'retention_tolerance_abs':.10,'base_step_grid':[.05,.1,.2,.3,.5],'calibration_seeds':[101,102,103,104,105],
        'base_step_selection':'min |mean(full)-mean(half)| on calibration seeds, ties -> smaller','eligible_min_drop':.02,'batch':20,'dim':8,
        'primary':'mean held-out MSE of current + previous 3 tasks after each trial (lower is better)',
        'win_rule':'f7 beats full, half and random in >=4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
TRIALS=240;PER_TASK=8;PHASE=40;DIM=8;BATCH=20;HOLD=40;BASE_STEP=.5;NOISE=.1;TOL=.10;MIN_DROP=.02
STEPS=(.05,.1,.2,.3,.5);CAL=(101,102,103,104,105)
ARMS=('f7','full','half','random')

def stream(seed):
    rng=random.Random(seed);tasks=[];w=[rng.gauss(0,1) for _ in range(DIM)]
    def sample(w,n):
        out=[]
        for _ in range(n):
            x=[rng.gauss(0,1) for _ in range(DIM)];out.append((x,sum(a*b for a,b in zip(w,x))+rng.gauss(0,NOISE)))
        return out
    for k in range(TRIALS//PER_TASK):
        if k:
            d=.5 if (k*PER_TASK//PHASE)%2 else .1
            w=[a+rng.gauss(0,d) for a in w]
        tasks.append({'hold':sample(w,HOLD),'batches':[sample(w,BATCH) for _ in range(PER_TASK)]})
    return tasks

def mse(w,data):return _mean([(sum(a*b for a,b in zip(w,x))-y)**2 for x,y in data])

def sgd(w,batch,step):
    w=list(w)
    for x,y in batch:
        e=y-sum(a*b for a,b in zip(w,x));n=1e-6+sum(v*v for v in x);w=[a+step*e*xi/n for a,xi in zip(w,x)]
    return w

def real_gain(pl,store,cfg):
    """One real budget() + updates row + observe() round; returns the effective/base ratio budget() granted."""
    id_=uid('upd');manifest={'component':'route','base_generation':store.generation_id,'metrics':{}}
    eff=pl.budget('route',cfg,id_,manifest);gain=eff['learning_rate']/cfg['learning_rate']
    def finish(retained,eligible):
        p=store.home/'checkpoints'/('head-'+id_+'.fixture');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'ablation fixture, no model')
        manifest['metrics'].update(retention_pass=retained,commit_eligible=eligible,effective_learning_rate=manifest['training_policy']['effective_learning_rate'],
                                   effective_max_update_norm=manifest['training_policy']['effective_max_update_norm'])
        with store.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(id_,store.generation_id,'PENDING_APPROVAL' if eligible else 'EVALUATED_FAIL',str(p.relative_to(store.home)),file_hash(p),dumps(manifest),now()))
        if not pl.observe(id_):raise RuntimeError('Plasticity did not accept the fixture trial')
    return gain,finish

def run_arm(tasks,arm,seed):
    rng=random.Random(seed*31+9);w=[0.]*DIM;scores=[];gains=[];commits=0;ret_fail=0
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d));cfg=dict(cfg,learning_mode='SHADOW_UPDATE');pl=Plasticity(store)
        for k,task in enumerate(tasks):
            old=[t['hold'] for t in tasks[max(0,k-3):k]]
            for b in task['batches']:
                finish=None
                if arm=='f7':g,finish=real_gain(pl,store,cfg)
                elif arm=='full':g=1.
                elif arm=='half':g=.5
                else:g=rng.uniform(.5,1.)
                gains.append(g);nw=sgd(w,b,BASE_STEP*g)
                ob=_mean([mse(w,h) for h in old]) if old else None;oa=_mean([mse(nw,h) for h in old]) if old else None
                retained=ob is None or oa<=ob+TOL;eligible=mse(nw,task['hold'])<=mse(w,task['hold'])*(1-MIN_DROP)
                if finish:finish(retained,eligible)
                ret_fail+=not retained
                if retained and eligible:w=nw;commits+=1
                scores.append(_mean([mse(w,h) for h in old+[task['hold']]]))
        store.close()
    return {'primary':round(_mean(scores),5),'commits':commits,'retention_failures':ret_fail,'mean_gain':round(_mean(gains),4)}

def calibrate():
    global BASE_STEP
    gap={}
    for st in STEPS:
        BASE_STEP=st;m={a:_mean([run_arm(stream(s),a,s)['primary'] for s in CAL]) for a in ('full','half')};gap[st]=abs(m['full']-m['half'])
    BASE_STEP=min(STEPS,key=lambda st:(round(gap[st],6),st));return {str(k):round(v,5) for k,v in gap.items()}

def run_all(seeds=SEEDS):
    cal=calibrate();per={s:{a:run_arm(stream(s),a,s) for a in ARMS} for s in seeds}
    wins={a:sum(per[s]['f7']['primary']<per[s][a]['primary'] for s in seeds) for a in ARMS[1:]}
    beat=[a for a,n in wins.items() if n>=4]
    return {'prereg':PREREG,'calibration_gap':cal,'base_step':BASE_STEP,'per_seed':per,'wins_of_5':wins,
            'summary':{a:{k:{'mean':round(_mean([per[s][a][k] for s in seeds]),4),'sd':round(_sd([per[s][a][k] for s in seeds]),4)} for k in ('primary','commits','retention_failures','mean_gain')} for a in ARMS},
            'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==3 else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic linear tasks, harness learner, BOOT gates; no native or shared-layer interference'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['wins_of_5'])
    for a,v in r['summary'].items():print(' ',a,{k:x['mean'] for k,x in v.items()})
