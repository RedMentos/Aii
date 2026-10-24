"""WP-T14 Thin-Control-Fabric budget (§22.2.3, §24.14): many small heads must not quietly grow into a big model.

One shared, measured budget over the whole control fabric (everything that is not a body forward pass):
  parameters / resident bytes  approved learned checkpoints (heads, projectors, adapters) of the active generation
  state bytes                  persistent control state (states table) incl. the largest keys
  event latency                mean and P95 of the control stages of a turn, from the per-turn stage marks
                               (ingress, policy, perception, memory, routing incl. C2, focal loop, output prepare);
                               body stages (B observers, C3/native answer) are reported beside it, not counted
  wake / forward frequency     share of turns with an inline B-observer stage, turns per hour
The blueprint fixes no limits before target-hardware measurement, so every limit knob defaults to 0 = unset and the
verdict is NO_LIMITS (report only). With limits set, each one is PASS/FAIL and the whole budget is PASS only if all
set limits pass. Energy/thermal overhead needs the phone (WP-R) and is reported as UNMEASURED.
"""
import json
import math
from pathlib import Path

KEY='WP_T14_CONTROL_BUDGET';REVISION='wp-t14-control-budget-v1'
STAGES=('ingress','policy_check','perception_and_state','memory_recall','routing','preanswer_observers','focal_loop','output_prepare','native_answer','finished')
BODY=('preanswer_observers','native_answer')
CONTROL=tuple(s for s in STAGES[:-1] if s not in BODY)
LIMITS=(('control_budget_p95_ms','control_p95_ms'),('control_budget_state_mb','state_mb'),('control_budget_params_mb','params_mb'))

def durations(marks):
    """Finite monotonic cumulative marks; invalid traces are not measurements."""
    if type(marks) is not dict:return {}
    seen=[]
    for stage in STAGES:
        value=marks.get(stage)
        if type(value) in (int,float) and math.isfinite(value) and value>=0:
            seen.append((stage,float(value)))
    if len(seen)<2 or any(seen[i+1][1]<seen[i][1] for i in range(len(seen)-1)):
        return {}
    return {stage:seen[i+1][1]-t for i,(stage,t) in enumerate(seen[:-1])}

def pct(xs,q):
    if not xs:return None
    xs=sorted(xs);i=min(len(xs)-1,max(0,int(round(q*(len(xs)-1)))));return xs[i]

def latency(store,n=200):
    rows=store.rows("SELECT metadata,created FROM messages WHERE role='assistant' AND status='FINAL' ORDER BY id DESC LIMIT ?",(n,))
    ctrl=[];body=[];per={s:[] for s in STAGES[:-1]};inline=0;times=[]
    for r in rows:
        try:meta=json.loads(r['metadata'] or '{}')
        except (ValueError,TypeError):continue
        if type(meta) is not dict:continue
        d=durations(meta.get('stage_marks_s'))
        created=r.get('created')
        if not d or type(created) not in (int,float) or not math.isfinite(created):continue
        times.append(created)
        for s,v in d.items():per[s].append(v)
        ctrl.append(sum(v for s,v in d.items() if s in CONTROL));body.append(sum(v for s,v in d.items() if s in BODY))
        inline+=d.get('preanswer_observers',0.)>.001
    n=len(ctrl);span=(max(times)-min(times))/3600 if n>1 else 0.
    ms=lambda x:None if x is None else round(1000*x,2)
    return {'turns':n,'control_mean_ms':ms(sum(ctrl)/n) if n else None,'control_p95_ms':ms(pct(ctrl,.95)),'body_mean_ms':ms(sum(body)/n) if n else None,
            'control_share':round(sum(ctrl)/max(1e-9,sum(ctrl)+sum(body)),4) if n else None,
            'stages_p95_ms':{s:ms(pct(v,.95)) for s,v in per.items() if v},'inline_observer_rate':round(inline/n,4) if n else None,
            'turns_per_hour':round(n/span,2) if span>0 else None}

def checkpoints(store,home):
    """Count only regular, non-symlink files inside the owned checkpoints tree.

    This is a *size inventory*, not cryptographic checkpoint verification.
    Hash/authenticity checks belong to the existing model registry/gates.
    """
    root=Path(home).resolve();allowed=root/'checkpoints'
    gen=store.generation();out=[];seen=set()
    def walk(x,where):
        if isinstance(x,dict):
            for k,v in x.items():walk(v,where+'.'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,where)
        elif isinstance(x,str) and ('checkpoints/' in x or x.endswith(('.npz','.gguf','.safetensors'))):
            p=Path(x);p=p if p.is_absolute() else root/p
            try:
                resolved=p.resolve(strict=True)
                if (not resolved.is_relative_to(allowed) or resolved!=p.absolute() or
                    not p.is_file() or resolved in seen):return
                seen.add(resolved)
                out.append({'path':str(resolved.relative_to(root)),
                            'bytes':resolved.stat().st_size,'from':where[1:]})
            except (OSError,ValueError,RuntimeError):return
    walk(gen,'');return out

def state_bytes(store,top=5):
    rows=store.rows('SELECT key,length(payload) AS n FROM states ORDER BY n DESC');total=sum(r['n'] or 0 for r in rows)
    return {'bytes':total,'keys':len(rows),'largest':[{'key':r['key'],'bytes':r['n']} for r in rows[:top]]}

def report(store,home,cfg,n=200):
    lat=latency(store,n);ck=checkpoints(store,home);st=state_bytes(store)
    measured={'control_p95_ms':lat['control_p95_ms'],'state_mb':round(st['bytes']/2**20,4),'params_mb':round(sum(c['bytes'] for c in ck)/2**20,4)}
    limits={};verdict='NO_LIMITS'
    for knob,key in LIMITS:
        cap=float(cfg.get(knob,0) or 0)
        if not math.isfinite(cap) or cap<0:raise ValueError('invalid control fabric limit: '+knob)
        if cap==0:continue
        val=measured[key];limits[key]={'cap':cap,'value':val,'pass':val is not None and val<=cap}
    if limits:verdict='PASS' if all(l['pass'] for l in limits.values()) else 'FAIL'
    if limits and lat['turns']==0 and 'control_p95_ms' in limits:verdict='NO_DATA'
    return {'revision':REVISION,'verdict':verdict,'limits':limits,'measured':measured,'latency':lat,'checkpoints':ck,'state':st,
            'energy_thermal':'UNMEASURED (Redmi, WP-R)','note':'Blueprint §22.2.3: concrete limits only after target-hardware measurement; 0 = unset'}

def record(store,rep):
    store.set_state(KEY,{'revision':REVISION,'verdict':rep['verdict'],'measured':rep['measured'],'limits':rep['limits']})
    store.log('control_budget',None,{'status':rep['verdict'],'value':rep['measured']['control_p95_ms'],'n':rep['latency']['turns']})

def operator_command(runtime,args):
    """:fabric [report|record]"""
    a=args[0] if args else 'report'
    if a not in ('report','record'):raise ValueError(':fabric [report|record]')
    rep=report(runtime.store,runtime.home,runtime.cfg)
    if a=='record':record(runtime.store,rep)
    return rep
