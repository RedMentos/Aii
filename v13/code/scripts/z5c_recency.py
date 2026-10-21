"""WP-Z5c: note recency/supersession term in the focal priority (switch focal_note_recency), real C3/B1/B2, cloud, English.

Preregistered in bench-results/z5c-recency-20261021/PREREGISTRATION.md before any model run.
Z5b found that under real capacity pressure the coalition keeps stale note versions, because the focal priority has no
recency term. Same task templates as Z5b (scripts/z5b_capacity.py: tasks), three task seeds (11 = the Z5b tasks, 12, 13).
Only change to the tasks: notes are stored in their real-world order (dated budget notes oldest first, last year's count
before the correction); the other notes keep their shuffled positions. Storage time is the only recency source.
The live turn runs with focal_note_recency=1. After the focal loop the final admission is replayed on copies of the
same candidates twice: with the terms (must reproduce the live coalition, fidelity) and with the terms zeroed
(the coalition the switch-off runtime would have formed from the same candidates). Arms (answer replayed greedily to the
organ C5 picked live, only the memory and hypotheses layers differ):
  shipped            replay of the live context (fidelity check)
  coalition_recency  memories and body offers of the live coalition (switch on)
  coalition_plain    memories and body offers of the counterfactual coalition (switch off, same candidates)
  full_context       every recalled memory and every offer of the turn
  retrieval_only     the first focal_slots (4) recalled memories, no body offer
  no_context         neither layer
Usage: z5c_recency.py <installed_home> <out.json> [--seeds 11,12,13] [--reps N] [--limit N]"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.common import atomic_write,dumps
import utility_bench as U
import utility_bench2 as U2
import z5_focal_controls as Z
import z5b_capacity as B

ARMS=('shipped_live','shipped','coalition_recency','coalition_plain','full_context','retrieval_only','no_context')
REPLAY=ARMS[1:]
CONTROLS=('coalition_plain','full_context','retrieval_only','no_context','shipped')
CFG=B.CFG|{'focal_note_recency':1}
SEEDS=(11,12,13)

def month(key):
    w=key.split()[-1]
    return B.MONTHS.index(w) if w in B.MONTHS else None

def chrono(fid,notes):
    """Store dated notes oldest first, every kind (and last year's count before the correction) in the slots they already hold."""
    notes=list(notes);kind=fid.rstrip('0123456789')
    at=[i for i,(k,_) in enumerate(notes) if month(k) is not None];vs=sorted((notes[i] for i in at),key=lambda n:month(n[0]))
    for i,n in zip(at,vs):notes[i]=n
    if kind=='correction':
        a=next(i for i,(k,_) in enumerate(notes) if k.endswith('last year'));b=next(i for i,(k,_) in enumerate(notes) if k.endswith('correction'))
        if a>b:notes[a],notes[b]=notes[b],notes[a]
    return notes

def needed(fid,notes):
    """Note keys the answer needs (none for distract: the answer is in the message)."""
    kind=fid.rstrip('0123456789');dated=[k for k,_ in notes if month(k) is not None]
    newest=max(dated,key=month) if dated else None
    if kind=='update':return [newest]
    if kind=='combine':return [newest,next(k for k,_ in notes if k.endswith('budget spending'))]
    if kind=='correction':return [next(k for k,_ in notes if k.endswith('correction'))]
    return []

def stale_keys(fid,notes):
    kind=fid.rstrip('0123456789')
    if kind not in ('update','combine'):return []
    dated=[k for k,_ in notes if month(k) is not None];newest=max(dated,key=month)
    return [k for k in dated if k!=newest]

def tasks(seed):
    return [(fid,text,chrono(fid,notes),nums,checks,stale) for fid,text,notes,nums,checks,stale in B.tasks(seed=seed)]

def seed_notes(r,session,notes):
    """Like Z5b, with a small pause so storage times are strictly increasing in the listed order."""
    ids=[]
    for key,value in notes:
        e=r.store.event(session,key);ids.append(r.memory.feedback(e['event_id'],'fact',value,key=key));time.sleep(.005)
    return ids

def readmit(F,cands,capacity,threshold,recency):
    """Replay of the final admission on copies; recency=False zeroes the WP-Z5c terms first."""
    cc=copy.deepcopy(cands)
    for c in cc:
        if not recency:
            c['priority_terms'].pop('recency',None);c['priority_terms'].pop('superseded',None)
        c['priority']=F.priority(c['priority_terms'])*c['decay']
    a,_=F.admit(cc,capacity,threshold)
    return a

def arm_views(memories,offers,coal_on,coal_off,slots):
    def gate(coal):
        ids={x['item_id'] for x in coal};by={p['packet_id']:p for p in offers}
        return ([m for m in memories if m['id'] in ids],[by[x['item_id']] for x in coal if x['source_kind']!='MEMORY' and x['item_id'] in by])
    return {'coalition_recency':gate(coal_on),'coalition_plain':gate(coal_off),'full_context':(memories,offers),
            'retrieval_only':(memories[:slots],[]),'no_context':([],[])}

def run_rep(installed,seed,rep,fixtures):
    from v13 import effort as EF
    from v13 import focal as F
    from v13 import runtime as RT
    from v13.common import Limits
    from v13.config import initialize,save_config
    from v13.proofs import audit_event
    from v13.prompts import text as prompt
    rows=[];measures=[];sessions=[]
    tmp=tempfile.mkdtemp(prefix='v13-z5c-')
    try:
        home=Path(tmp);cfg=initialize(home)
        for n in ('models','bin'):shutil.rmtree(home/n);(home/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        save_config(home,cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'history_turns':0}|U2.BENCH_CFG|CFG)
        r=RT.Runtime(home);EF.set_mode(r.store,'max')
        cap={}
        orig_loop,orig_save,orig_admit=RT.FocalLoop,RT.save_context,F.admit
        def admit(cands,capacity,threshold,interrupt=F.BOOT['sal_interrupt']):
            snap=copy.deepcopy(cands)
            a,rest=orig_admit(cands,capacity,threshold,interrupt)
            cap['last_admit']=(snap,capacity,threshold);cap['admissions']=[c.get('admission') for c in a+rest];cap['n_candidates']=len(cands)
            cap['max_candidates']=max(cap.get('max_candidates',0),len(cands));cap.setdefault('all_admissions',[]).extend(cap['admissions'])
            return a,rest
        class Loop(orig_loop):
            def run(self,e,version,offers,**kw):
                out=super().run(e,version,offers,**kw);cap['run']=out;cap['e']=e;cap['version']=version;cap['memories']=list(kw.get('memories') or [])
                cap['slots']=max(1,min(int((kw.get('plan') or {}).get('focal_slots') or 1),r.cfg['focal_slots']))
                out['_admissions']=cap.get('admissions',[]);out['_n_candidates']=cap.get('n_candidates',0)
                return out
        def save(store,session,eid,role,messages):
            cap['messages']=json.loads(json.dumps(messages));cap['answer_role']=role
            return orig_save(store,session,eid,role,messages)
        RT.FocalLoop,RT.save_context,F.admit=Loop,save,admit
        try:
            hyp_head='\n'+prompt(r.cfg,'hypotheses');mem_head='\n'+prompt(r.cfg,'memories');anchor='\n'+prompt(r.cfg,'task_context')
            cache={}
            for fid,text,notes,nums,checks,stale in fixtures:
                cap.clear();r.session=r.store.new_session();sessions.append(r.session);seed_notes(r,r.session,notes)
                t0=time.monotonic();eid=r.submit(text);end=t0+900
                while not r.idle():
                    if time.monotonic()>end:r.cancel();break
                    time.sleep(.1)
                a=audit_event(r.store,eid);out=a.get('output') or '';meta=a.get('output_metadata') or {};turn_s=round(time.monotonic()-t0,2)
                ok,num=U.score(out,nums,checks)
                base={'seed':seed,'rep':rep,'fixture':fid,'kind':fid.rstrip('0123456789')}
                run=cap.get('run');msgs=cap.get('messages')
                rows.append(base|{'arm':'shipped_live','pass':all(ok.values()) and all(num.values()),'clean':B.clean(out,stale),'turn_s':turn_s,'status':a.get('status'),
                                  'answer_role':cap.get('answer_role'),'output':out[:400]})
                plan_applied=(meta.get('context_plan') or {}).get('applied')
                if run is None or msgs is None or plan_applied or 'last_admit' not in cap:
                    for arm in REPLAY:rows.append(base|{'arm':arm,'pass':False,'skipped':'NO_FOCAL_RUN' if run is None else 'NO_MESSAGES' if msgs is None else 'CONTEXT_PLAN_APPLIED' if plan_applied else 'NO_ADMIT'})
                    print(json.dumps({'seed':seed,'rep':rep,'fixture':fid,'skipped':True}),flush=True);continue
                snap,capacity,threshold=cap['last_admit']
                on=readmit(F,snap,capacity,threshold,True);off=readmit(F,snap,capacity,threshold,False)
                live_ids=[x['item_id'] for x in run['coalition']]
                coal_on=run['coalition'];coal_off=off
                keys={m['id']:m.get('key_text') for m in cap['memories']}
                need=needed(fid,notes);stl=stale_keys(fid,notes)
                def has(coal,ks):return sum(any(keys.get(x['item_id'])==k for x in coal) for k in ks)
                m=Z.focal_measure(r.store,eid,run,cap['slots'])
                coal_mem=[x for x in coal_on if x['source_kind']=='MEMORY']
                m.update(recalled=len(cap['memories']),max_candidates=cap.get('max_candidates',0),coalition_memories=len(coal_mem),
                         coalition_bodies=len(coal_on)-len(coal_mem),selected_offers=len(run['selected']),
                         capacity_rejections_all_admits=cap.get('all_admissions',[]).count('CAPACITY'),
                         readmit_fidelity=[x['item_id'] for x in on]==live_ids,coalition_differs=sorted(live_ids)!=sorted(x['item_id'] for x in off),
                         needed_notes=len(need),needed_in_recency=has(coal_on,need),needed_in_plain=has(coal_off,need),
                         needed_recalled=sum(k in keys.values() for k in need),stale_notes=len(stl),stale_in_recency=has(coal_on,stl),stale_in_plain=has(coal_off,stl),
                         superseded_flags=sum(1 for x in snap if x['priority_terms'].get('superseded')),recency_flags=sum(1 for x in snap if x['priority_terms'].get('recency')))
                measures.append(base|m)
                e,version=cap['e'],cap['version'];sysmsg=msgs[0]['content']
                live_mem=B.layer(mem_head,r.memory.report_context(text,cap['memories']) if cap['memories'] else None)
                live_hyp=B.layer(hyp_head,r.cognition.analyst_context(run['selected'],e,version) if run['selected'] else None)
                line={'seed':seed,'rep':rep,'fixture':fid,'role':cap['answer_role'],'live':rows[-1]['pass'],'turn_s':turn_s,'cand':m['max_candidates'],
                      'need_on':m['needed_in_recency'],'need_off':m['needed_in_plain'],'differs':m['coalition_differs'],'fid':m['readmit_fidelity']}
                views={'shipped':(cap['memories'],run['selected'])}|arm_views(cap['memories'],run['offers'],coal_on,coal_off,r.cfg['focal_slots'])
                for arm,(mems,subs) in views.items():
                    try:new=B.layer(mem_head,r.memory.report_context(text,mems) if mems else None)+B.layer(hyp_head,r.cognition.analyst_context(subs,e,version) if subs else None)
                    except Exception as exc:rows.append(base|{'arm':arm,'pass':False,'skipped':'CONTEXT_REJECTED','error':type(exc).__name__+': '+str(exc)[:200]});continue
                    try:system=B.swap_layers(sysmsg,(live_mem,live_hyp),new,anchor)
                    except ValueError as exc:rows.append(base|{'arm':arm,'pass':False,'skipped':'LAYER_SWAP_FAILED','error':str(exc)});continue
                    mm=[{'role':'system','content':system}]+msgs[1:];key=hashlib.sha256(dumps(mm).encode()).hexdigest()
                    t1=time.monotonic()
                    if key not in cache:
                        try:cache[key]=''.join(r.pool.get(cap['answer_role']).generate(mm,r.cancel_event,time.monotonic()+300))
                        except Limits as exc:rows.append(base|{'arm':arm,'pass':False,'skipped':'CONTEXT_WINDOW','context_chars':len(new),'error':str(exc)[:200]});continue
                    o=cache[key];ok,num=U.score(o,nums,checks)
                    rows.append(base|{'arm':arm,'pass':all(ok.values()) and all(num.values()),'clean':B.clean(o,stale),'gen_s':round(time.monotonic()-t1,2),'context_hash':key[:16],
                                      'context_chars':len(new),'memories':len(mems),'offers':len(subs),'answer_role':cap['answer_role'],'same_as_live':o.strip()==out.strip(),'output':o[:400]})
                    line[arm]=rows[-1]['pass']
                print(json.dumps(line),flush=True)
        finally:
            RT.FocalLoop,RT.save_context,F.admit=orig_loop,orig_save,orig_admit
            r.close()
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
    return rows,measures

def _sign(a,b):
    from math import comb
    n=a+b;k=min(a,b)
    return 1. if n==0 else min(1.,2*sum(comb(n,i) for i in range(k+1))/2**n)

def paired(rows,x,y):
    by={}
    for r in rows:
        if r.get('skipped'):continue
        by.setdefault((r['seed'],r['rep'],r['fixture']),{})[r['arm']]=r['pass']
    a=b=0;units={}
    for k,v in by.items():
        if x in v and y in v:
            a+=v[x] and not v[y];b+=v[y] and not v[x]
            u=units.setdefault(k[:2],[0,0]);u[0]+=v[x];u[1]+=v[y]
    lead=sum(p-q for p,q in units.values())/max(1,len(units))
    return {'x_only':a,'y_only':b,'sign_test_p':round(_sign(a,b),4),'mean_lead_per_run':round(lead,2),'runs':len(units)}

def noise_band(rows):
    """Largest shipped_live pass-count difference between two runs of the same task seed."""
    per={}
    for r in rows:
        if r['arm']=='shipped_live':per.setdefault(r['seed'],{}).setdefault(r['rep'],0);per[r['seed']][r['rep']]+=r['pass']
    d=[max(v.values())-min(v.values()) for v in per.values() if len(v)>1]
    return max(d) if d else None

def analyse(rows,measures):
    done=[r for r in rows if not r.get('skipped')]
    summ={a:{'pass':sum(r['pass'] for r in done if r['arm']==a),'n':sum(1 for r in done if r['arm']==a),
             'clean':round(sum(r.get('clean',False) for r in done if r['arm']==a)/max(1,sum(1 for r in done if r['arm']==a)),3),
             'mean_context_chars':round(sum(r.get('context_chars',0) for r in done if r['arm']==a)/max(1,sum(1 for r in done if r['arm']==a)))} for a in ARMS}
    kinds=sorted({r['kind'] for r in rows})
    by_kind={a:{k:round(sum(r['pass'] for r in done if r['arm']==a and r['kind']==k)/max(1,sum(1 for r in done if r['arm']==a and r['kind']==k)),3) for k in kinds} for a in ARMS}
    by_seed={a:{str(s):sum(r['pass'] for r in done if r['arm']==a and r['seed']==s) for s in sorted({r['seed'] for r in rows})} for a in ARMS}
    pr={'coalition_recency_vs_'+c:paired(rows,'coalition_recency',c) for c in CONTROLS}
    pr['shipped_live_vs_full_context']=paired(rows,'shipped_live','full_context')
    band=noise_band(rows);n=len(measures)
    def beats(p):return p['sign_test_p']<.05 and p['x_only']>p['y_only'] and band is not None and p['mean_lead_per_run']>band
    pf=pr['coalition_recency_vs_full_context'];pp=pr['coalition_recency_vs_coalition_plain']
    mech={'turns':n,'readmit_fidelity':round(sum(m['readmit_fidelity'] for m in measures)/max(1,n),3),
          'coalition_differs':sum(m['coalition_differs'] for m in measures),
          'capacity_bound_rate':round(sum(m['max_candidates']>m['slots'] for m in measures)/max(1,n),3),
          'mean_superseded_flags':round(sum(m['superseded_flags'] for m in measures)/max(1,n),2)}
    for k in kinds:
        ms=[m for m in measures if m['kind']==k and m['needed_notes']]
        if ms:mech['needed_rate_'+k]={'recency':round(sum(m['needed_in_recency'] for m in ms)/sum(m['needed_notes'] for m in ms),3),
                                       'plain':round(sum(m['needed_in_plain'] for m in ms)/sum(m['needed_notes'] for m in ms),3),
                                       'recalled':round(sum(m['needed_recalled'] for m in ms)/sum(m['needed_notes'] for m in ms),3)}
        ms=[m for m in measures if m['kind']==k and m['stale_notes']]
        if ms:mech['stale_rate_'+k]={'recency':round(sum(m['stale_in_recency'] for m in ms)/sum(m['stale_notes'] for m in ms),3),
                                      'plain':round(sum(m['stale_in_plain'] for m in ms)/sum(m['stale_notes'] for m in ms),3)}
    verdict={'noise_band':band,'capacity_bound_rate':mech['capacity_bound_rate'],'readmit_fidelity':mech['readmit_fidelity'],
             'replay_fidelity':round(sum(r.get('same_as_live',False) for r in done if r['arm']=='shipped')/max(1,sum(1 for r in done if r['arm']=='shipped')),3),
             'beats_full_context':'PASS' if beats(pf) else 'FAIL','term_helps_coalition':'PASS' if beats(pp) else 'FAIL',
             'not_worse_than_retrieval_only':not (pr['coalition_recency_vs_retrieval_only']['sign_test_p']<.05 and pr['coalition_recency_vs_retrieval_only']['y_only']>pr['coalition_recency_vs_retrieval_only']['x_only'])}
    if mech['capacity_bound_rate']<.5:verdict['beats_full_context']='NOT_TESTABLE_CAPACITY_RARELY_BINDS'
    verdict['caveat']=verdict['replay_fidelity']<.95 or verdict['readmit_fidelity']<.95
    return {'summary':summ,'by_kind':by_kind,'by_seed':by_seed,'paired':pr,'mechanism':mech,'verdict':verdict}

def main(installed,out,seeds=SEEDS,reps=2,limit=None):
    installed=Path(installed).resolve();out=Path(out)
    prev=json.loads(out.read_text()) if out.exists() else {}
    rows,measures=prev.get('rows',[]),prev.get('measures',[])
    done={(x['seed'],x['rep']) for x in rows}
    for seed in seeds:
        fx=tasks(seed)
        if limit:fx=[f for i,f in enumerate(fx) if i%(len(fx)//limit)==0][:limit]
        for rep in range(1,reps+1):
            if (seed,rep) in done:continue
            rr,mm=run_rep(installed,seed,rep,fx);rows+=rr;measures+=mm
            atomic_write(out,json.dumps({'kind':'WP_Z5C_RECENCY','preregistration':'bench-results/z5c-recency-20261021/PREREGISTRATION.md',
                'bench_cfg':U2.BENCH_CFG|CFG|{'effort':'max'},'seeds':list(seeds),'runs_done':sorted({(x['seed'],x['rep']) for x in rows}),
                **analyse(rows,measures),'rows':rows,'measures':measures,
                'claim_limit':'generated English tasks (Z5b templates), three task seeds, regex on the final answer, lexical recall, greedy bench decoding, cloud CPU'},indent=1))
    print(json.dumps(analyse(rows,measures)['verdict'],indent=1))

if __name__=='__main__':
    a=sys.argv[1:];reps=2;lim=None;seeds=SEEDS
    if '--reps' in a:i=a.index('--reps');reps=int(a[i+1]);del a[i:i+2]
    if '--limit' in a:i=a.index('--limit');lim=int(a[i+1]);del a[i:i+2]
    if '--seeds' in a:i=a.index('--seeds');seeds=tuple(int(x) for x in a[i+1].split(','));del a[i:i+2]
    main(a[0],a[1],seeds,reps,lim)
