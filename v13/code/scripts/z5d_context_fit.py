"""WP-Z5d: live context fit before/after on the Z5c long-session tasks (60 WP-T3b tasks x N reps, one session per rep).

Same setup as z5_focal_controls.py --session (fresh home per rep, effort max, bench mode, kinds shuffled with seed 7,
history_turns 0) but only the shipped live turn is measured, once with cfg context_fit=<arm>. Overflow = the answer is
a SOURCE_SYSTEM_REPORT (window exceeded); it counts as failed. Per turn the context_fit report (steps, tokens) is kept.
Usage: z5d_context_fit.py <installed_home> <out.json> --arm off|shadow|active [--reps N] [--limit N]"""
import json
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.common import atomic_write
import utility_bench as U
import utility_bench2 as U2
from z5_focal_controls import SESSION_SEED,intrusion,is_system_report

def fixtures(limit=None):
    fx=U2.tasks()
    if limit:fx=[f for i,f in enumerate(fx) if i%(len(fx)//limit)==0][:limit]
    random.Random(SESSION_SEED).shuffle(fx)
    return fx

def run_rep(installed,rep,fx,arm):
    from v13 import effort as EF
    from v13 import runtime as RT
    from v13.config import initialize,save_config
    from v13.proofs import audit_event
    rows=[];tmp=tempfile.mkdtemp(prefix='v13-z5d-')
    try:
        home=Path(tmp);cfg=initialize(home)
        for n in ('models','bin'):shutil.rmtree(home/n);(home/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        save_config(home,cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'history_turns':0,'context_fit':arm}|U2.BENCH_CFG)
        r=RT.Runtime(home);EF.set_mode(r.store,'max');r.session=r.store.new_session();previous=[]
        try:
            for fid,text,nums,checks in fx:
                t0=time.monotonic();eid=r.submit(text);end=t0+900
                while not r.idle():
                    if time.monotonic()>end:r.cancel();break
                    time.sleep(.1)
                a=audit_event(r.store,eid);out=a.get('output') or '';meta=a.get('output_metadata') or {}
                ok,num=U.score(out,nums,checks);overflow=is_system_report(out)
                if overflow:ok,num={'answer':False},{}
                prev=previous[-3:];previous.append(nums)
                row={'rep':rep,'fixture':fid,'kind':fid.rstrip('0123456789'),'arm':arm,'pass':all(ok.values()) and all(num.values()),
                     'overflow':overflow,'intrusion':intrusion(out,nums,prev) and not overflow,'turn_s':round(time.monotonic()-t0,2),
                     'role':(meta.get('runner') or {}).get('role'),'context_fit':meta.get('context_fit'),'output':out[:400]}
                rows.append(row)
                print(json.dumps({k:row[k] for k in ('rep','fixture','arm','pass','overflow','turn_s')}|{'fit':(row['context_fit'] or {}).get('steps')}),flush=True)
        finally:r.close()
    finally:shutil.rmtree(tmp,ignore_errors=True)
    return rows

def summary(rows):
    reps=sorted({x['rep'] for x in rows})
    fits=[x['context_fit'] for x in rows if x.get('context_fit')]
    steps={}
    for f in fits:
        for k,v in f.get('steps',{}).items():steps[k]=steps.get(k,0)+v
    return {'turns':len(rows),'pass':sum(x['pass'] for x in rows),'overflow':sum(x['overflow'] for x in rows),
            'intrusion':sum(x['intrusion'] for x in rows),'per_rep':[sum(x['pass'] for x in rows if x['rep']==r) for r in reps],
            'overflow_per_rep':[sum(x['overflow'] for x in rows if x['rep']==r) for r in reps],
            'fit_checked':len(fits),'fit_applied':sum(bool(f.get('applied')) for f in fits),
            'fit_still_too_long':sum(f.get('fits') is False for f in fits),'fit_steps':steps,
            'median_turn_s':sorted(x['turn_s'] for x in rows)[len(rows)//2] if rows else None}

def main(installed,out,arm,reps=5,limit=None):
    installed=Path(installed).resolve();out=Path(out);fx=fixtures(limit)
    prev=json.loads(out.read_text()) if out.exists() else {}
    rows=prev.get('rows',[]);done={x['rep'] for x in rows}
    for rep in range(1,reps+1):
        if rep in done:continue
        rows+=run_rep(installed,rep,fx,arm)
        atomic_write(out,json.dumps({'kind':'WP_Z5D_CONTEXT_FIT','arm':arm,'bench_cfg':U2.BENCH_CFG|{'effort':'max','history_turns':0},
            'fixtures':[f[0] for f in fx],'summary':summary(rows),'rows':rows,
            'claim_limit':'generated English tasks, one seed, regex on the final answer, greedy bench decoding, cloud CPU'},indent=1))
    print(json.dumps(summary(rows),indent=1))

if __name__=='__main__':
    a=sys.argv[1:];reps=5;lim=None
    i=a.index('--arm');arm=a[i+1];del a[i:i+2]
    if '--reps' in a:i=a.index('--reps');reps=int(a[i+1]);del a[i:i+2]
    if '--limit' in a:i=a.index('--limit');lim=int(a[i+1]);del a[i:i+2]
    main(a[0],a[1],arm,reps,lim)
