"""G13 long-run lifecycle soak (Canon G13; §22.2.1 scheduler, §94 sleep, §102 redmi_longrun_proof).

Runs simulated days through the real Runtime: each day is a fresh process-level restart of the Runtime,
user turns go through the durable turn queue and worker, wake events through the live G13 scheduler and
sleep through the real SleepRuntime job path. Only the sleep/scheduler clock is advanced (days pass in
seconds); turn deadlines stay real.

Per day it checks the G13 list: restarts, wake order/priority (USER/TOOL/TIMER/GOAL/REPLAY/IDLE),
replay scheduling, memory health (every recorded fact still recallable, store integrity), Age stability,
job errors and growth of DB / queues, so a slow collapse cannot stay silent.

  python scripts/longrun_soak.py --home /tmp/soak --days 3            # fixture C3 (cloud, Linux software test)
  python scripts/longrun_soak.py --home ~/v13soak --days 7 --native --models-from ~/v13   # Redmi (WP-R)

Evidence level: without --native this is a software test with a fixture speaker; RSS/thermal/latency
need the native run on the phone. The report is written to <home>/exports/longrun-soak.json.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write,dumps  # noqa: E402

REVISION='g13-longrun-soak-v1'
DAY=86400.
# Wake batch per day: (kind, origin, action, due offset s). USER origin: not V13's own initiative (no Age right needed).
WAKES=(('IDLE','USER','notice',0),('REPLAY_DUE','USER','notice',0),('GOAL_WAKE','USER','notice',0),
       ('TIMER','USER','notice',0),('TOOL_EVENT','USER','notice',0),('TIMER','USER','notice',3600))
FACTS=('Project {d}{i} budget is {v} euro','The {d}{i} meeting room is number {v}','Server {d}{i} runs on port {v}')
MAX_DB_GROWTH_MB_PER_DAY=8.   # BOOT bound for "no silent collapse" in fixture mode (no model output stored at scale)

class Clock:
    def __init__(self,t):self.t=float(t)
    def __call__(self):return self.t

class SimulatedWall:
    """One simulated wall clock for store timestamps (accepted turns, telemetry, replay rows) and the
    scheduler/sleep clock, so idle time, burn-out budget and replay spacing all see the same days.
    Monotonic deadlines of turns stay real."""
    def __init__(self,clock):self.clock=clock;self.saved=[]
    def __enter__(self):
        import importlib,pkgutil
        import v13,v13.common as common
        for m in pkgutil.walk_packages(v13.__path__,'v13.'):  # modules imported lazily later would keep the real clock
            if m.name not in sys.modules:
                try:importlib.import_module(m.name)
                except Exception:pass  # optional heavy deps (torch etc.) are not part of the soak path
        real=common.now
        for name,mod in list(sys.modules.items()):
            if (name=='v13' or name.startswith('v13.')) and getattr(mod,'now',None) is real:
                self.saved.append((mod,real));mod.now=self.clock
        return self
    def __exit__(self,*exc):
        for mod,real in self.saved:mod.now=real
        self.saved.clear()

def fixture_speaker(r):
    """Deterministic C3 stand-in: answers from the recalled context so memory health shows in the text."""
    def generate(messages,cancel,deadline,*a,**k):
        yield 'Noted. '+messages[-1]['content'][-80:]
    r.pool.get=lambda role:SimpleNamespace(role=role,last_metrics={'fixture':True},generate=generate,pids=lambda:[])

def wait_idle(r,timeout=60.):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if r.idle() and r.jobs.empty():return True
        time.sleep(.02)
    return False

def open_runtime(home,clock,native):
    from v13.runtime import Runtime
    from v13.sleep import SleepRuntime
    r=Runtime(home)
    r.sleep=SleepRuntime(r,clock=clock)  # same job path, simulated wall clock for idle/sleep/scheduler
    r.sleep.cycle.set_policy('enabled','on');r.sleep.cycle.set_policy('tick_seconds','300')
    if not native:
        fixture_speaker(r);r.cfg['observer_mode']='off'
        r.learner.output_delta=lambda *a,**k:None
    return r

def recall_ok(r,facts):
    hit=0
    for f in facts:
        found=r.memory.recall(f['question'],f['session'])
        hit+=any(m.get('value')==f['value'] for m in found)
    return hit

def soak(home,days=3,turns=4,native=False,models_from=None,start=None,log=print):
    home=Path(home);home.mkdir(parents=True,exist_ok=True)
    if models_from:
        src=Path(models_from).expanduser()
        (home/'config').mkdir(parents=True,exist_ok=True)
        if not (home/'models').exists():os.symlink(src/'models',home/'models')
        shutil.copy2(src/'config/models.json',home/'config/models.json')
    clock=Clock(start or time.time())
    report={'kind':'V13_G13_LONGRUN_SOAK','revision':REVISION,'native':native,'days':[],'facts':0,
            'evidence_level':'NATIVE_DEVICE_RUN' if native else 'LINUX_SOFTWARE_FIXTURE_SPEAKER',
            'claim_limit':'fixture speaker: no model quality, RSS, thermal or latency claim' if not native else 'single device run'}
    facts=[];first_stage=None;carry=None
    import v13.runtime  # noqa: F401  (every module importing common.now is loaded before patching)
    with SimulatedWall(clock):
        for d in range(days):
            t0=time.monotonic();day_start=clock();r=open_runtime(home,clock,native);day={'day':d,'checks':{}}
            try:
                from v13 import age as agectl
                from v13.resources import process_memory
                sched=r.sleep.scheduler
                day['restart_recovered']=sched.recover()
                # 1) events posted before the restart must survive it and wake now.
                carried=[e for e in sched.pending() if e['id'] in (carry or ())]
                # 2) user turns through the durable queue + worker.
                statuses=[]
                for i in range(turns):
                    v=str(100+17*d+i);text=FACTS[i%len(FACTS)].format(d=chr(65+d%26),i=i,v=v)
                    r.submit(text)
                    if not wait_idle(r):raise TimeoutError('turn did not finish')
                    row=r.last_answer();statuses.append(row['status'] if row else None)
                    e=r.store.one('SELECT * FROM events WHERE id=?',(row['event_id'],))
                    mid=r.memory.feedback(row['event_id'],'fact',v)  # explicit user fact -> memory + replay item
                    facts.append({'question':text.rsplit(' is ',1)[0].replace(' runs on port','')+'?','value':v,'session':e['session_id'],'memory_id':mid})
                day['turn_status']=statuses
                # 3) wake batch: dispatch order must follow priority; a future TIMER waits for its due time.
                ids=[]
                for kind,origin,action,due in WAKES:
                    ids.append(sched.post(kind,origin=origin,action=action,due=clock()+due,payload={'text':''}))
                order=[];clock.t+=60
                pol=r.sleep.cycle.policy();qst=r.sleep.cycle.queue.load()[0];r.sleep.cycle.queue.sync(qst,pol)
                due0=len(r.sleep.cycle.queue.due(qst,clock(),min_priority=pol['wake_min_priority']))
                for _ in range(64):  # system wake replays (higher priority than IDLE) drain first
                    e=r.sleep.tick(force=True)
                    if e is None:break
                    order.append((e['kind'],e['id']))
                    wait_idle(r)
                day['wake_order']=[k for k,_ in order]
                replays=sum(1 for k,i in order if k=='REPLAY_DUE' and i not in ids)
                day['wake_replays']={'due_at_start':due0,'dispatched':replays}
                day['checks']['replay_wakes_drain']=replays<=due0+1 and e is None
                expected=sorted([w for w in WAKES if w[3]==0],key=lambda w:-{'TOOL_EVENT':80,'TIMER':50,'GOAL_WAKE':40,'REPLAY_DUE':20,'IDLE':10}[w[0]])
                got=[k for k,i in order if i in ids]
                day['checks']['wake_priority']=got==[w[0] for w in expected]
                day['checks']['future_timer_waits']=ids[-1] not in [i for _,i in order]
                day['checks']['carried_wakes_survive_restart']=all(c['id'] in [i for _,i in order] for c in carried)
                carry=[ids[-1]]  # the future TIMER is due tomorrow, after the restart
                # 4) idle night: the scheduler posts and runs a full sleep through the job queue.
                clock.t+=r.sleep.cycle.policy()['sleep_idle_s']+r.sleep.cycle.policy()['sleep_interval_s']+1
                for _ in range(6):
                    e=r.sleep.tick(force=True);wait_idle(r,120)
                    last=r.sleep.cycle.status()['last']
                    if last and last.get('mode')=='full' and last.get('started',0)>=clock.t-1:break
                last=r.sleep.cycle.status()['last'] or {}
                day['sleep']={k:last.get(k) for k in ('mode','status','origin','resource_state')}
                a=next((p for p in last.get('phases',[]) if p.get('phase')=='SLEEP_A'),{})
                day['sleep']['replay']={k:a.get(k) for k in ('selected','passed','failed','retired','retention_old')}
                day['checks']['sleep_full_done']=last.get('mode')=='full' and last.get('status')=='DONE'
                # 5) health.
                hit=recall_ok(r,facts);day['recall']={'facts':len(facts),'recalled':hit}
                day['checks']['memory_health']=hit==len(facts)
                integrity=r.store.integrity(False);day['integrity_errors']=integrity;day['checks']['store_integrity']=not integrity
                ac=agectl.controller(r);stage=ac.system_stage();first_stage=stage if first_stage is None else first_stage
                day['age']={'stage':stage,'maturity':ac.maturity()};day['checks']['age_stable']=stage==first_stage
                errs=r.store.rows("SELECT kind,metrics FROM telemetry WHERE kind IN ('job_error','turn_error','sleep_error') AND created>=?",(day_start,))
                day['job_errors']=[x['kind'] for x in errs];day['checks']['no_job_errors']=not errs
                day['checks']['turns_final']=all(s=='FINAL' for s in statuses)
                st=sched.report();day['scheduler']={'pending':len(st['pending']),'counters':st['counters']}
                day['checks']['scheduler_bounded']=len(st['pending'])<=len(WAKES)+2
                db=sum(p.stat().st_size for p in (home/'data/db').glob('*') if p.is_file())/1048576
                day['db_mb']=round(db,3);day['rss_mb']=round((process_memory().get('rss_bytes') or 0)/1048576,1)
                if report['days']:
                    day['db_growth_mb']=round(db-report['days'][-1]['db_mb'],3)
                    day['checks']['db_growth_bounded']=day['db_growth_mb']<=MAX_DB_GROWTH_MB_PER_DAY
                day['replay_live']=r.sleep.cycle.status()['live']
            except Exception as exc:
                day['error']=type(exc).__name__+': '+str(exc)[:300];day['checks']['no_exception']=False
            finally:
                r.close()
            day['ok']=all(day['checks'].values()) and 'error' not in day
            day['seconds']=round(time.monotonic()-t0,2);report['days'].append(day)
            log('day %d %s %s'%(d,'OK' if day['ok'] else 'FAIL',{k:v for k,v in day['checks'].items() if not v}))
            clock.t=(clock.t//DAY+1)*DAY+8*3600  # next morning
    report['facts']=len(facts)
    report['verdict']='PASS' if report['days'] and all(x['ok'] for x in report['days']) else 'FAIL'
    due=[x.get('wake_replays',{}).get('due_at_start') for x in report['days']]
    report['findings']=[]
    if len(due)>=3 and None not in due and all(b>=a for a,b in zip(due,due[1:])) and due[-1]>=2*max(1,due[0]):
        report['findings'].append({'id':'REPLAY_BACKLOG_GROWS','detail':'due replay items rise every day ('+','.join(map(str,due))+'); autonomous replay is capped by the Age replay_items budget','severity':'WARN'})
    out=home/'exports/longrun-soak.json';out.parent.mkdir(parents=True,exist_ok=True);atomic_write(out,dumps(report));report['artifact']=str(out)
    return report

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--home',required=True);ap.add_argument('--days',type=int,default=3);ap.add_argument('--turns',type=int,default=4)
    ap.add_argument('--native',action='store_true');ap.add_argument('--models-from')
    a=ap.parse_args(argv)
    if a.native and not a.models_from:ap.error('--native braucht --models-from <installiertes V13-Home> (nie im Nutzer-Home selbst laufen lassen)')
    if a.models_from and Path(a.home).expanduser().resolve()==Path(a.models_from).expanduser().resolve():ap.error('--home darf nicht das Nutzer-Home sein')
    rep=soak(a.home,a.days,a.turns,a.native,a.models_from)
    print(json.dumps({'verdict':rep['verdict'],'artifact':rep['artifact'],'days':[{k:d.get(k) for k in ('day','ok','seconds')} for d in rep['days']]}))
    return 0 if rep['verdict']=='PASS' else 1

if __name__=='__main__':sys.exit(main())
