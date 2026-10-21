"""WP-Z5b: focal coalition under real capacity pressure (more candidates than slots), real C3/B1/B2, cloud, English.

Preregistered in bench-results/z5b-capacity-20261021/PREREGISTRATION.md before any model run.
Z5 found that capacity never binds on the WP-T3b tasks (max. 3 candidates, 4 slots). Here every task seeds six stored
user notes (memory facts, one session per task) that all pass lexical recall (memory_top_k 6), so the focal loop sees
about 3 body offers + 6 memories = 9 candidates for 4 slots. Only some notes are needed; the rest are stale versions
or same-topic distractors. Four kinds x 15 (seed 11):
  update      the newest of three dated budget notes is the answer, three other budgets are distractors
  combine     newest budget minus the spending note (two notes needed, four distractors)
  correction  the message carries a count, a stored correction replaces it, five survey distractors
  distract    the answer is in the message (expense total), all six notes are distractors
Shipped runtime: recalled memories always reach the answer (ACTIVE_VIEW layer); the coalition only filters body offers.
Per turn the live answer is the arm `shipped_live`; after the focal loop the other arms are rebuilt from the same
recalled memories and offers and sent greedily to the organ C5 picked live; only the memory and hypotheses layers differ:
  shipped          replay of the live context (fidelity check)
  coalition_gated  memories and body offers of the live coalition only (the B4 bottleneck as the answer's view)
  full_context     every recalled memory and every offer of the turn
  fixed_slots      the first 2 recalled memories + the newest offer per body (4 fixed slots, no competition)
  retrieval_only   the first focal_slots (4) recalled memories, no body offer
  no_context       neither layer
Usage: z5b_capacity.py <installed_home> <out.json> [--reps N] [--limit N]"""
import hashlib
import json
import random
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

ARMS=('shipped_live','shipped','coalition_gated','full_context','fixed_slots','retrieval_only','no_context')
REPLAY=ARMS[1:]
CONTROLS=('full_context','fixed_slots','retrieval_only','no_context','shipped')
PROJECTS=('Kestrel','Alder','Birch','Heron','Lynx','Otter','Quartz','Raven','Sable','Tamarack','Umber','Vireo','Willow','Yarrow','Zephyr',
          'Cedar','Falcon','Juniper','Maple','Nimbus')
MONTHS=('January','February','March','April','May','June','July','August','September','October')
CFG={'memory_top_k':6,'focal_slots':4}

def word(n):return U2.word(n)

def tasks(seed=11,per_kind=15):
    """(fixture, message, notes [(key, value)], answer numbers, regex checks, stale numbers). Notes are stored in the listed order."""
    rng=random.Random(seed);out=[]
    def shuffled(xs):xs=list(xs);rng.shuffle(xs);return xs
    for i in range(per_kind):
        p=rng.choice(PROJECTS);ms=sorted(rng.sample(range(len(MONTHS)),3));vs=rng.sample(range(30,95),3);ds=[rng.randint(1,28) for _ in ms]
        tr,hw,tn=rng.sample(range(5,29),3)
        notes=[('Project %s budget %s'%(p,MONTHS[m]),'Budget note of %d %s: the Project %s main budget is %d units.'%(d,MONTHS[m],p,v)) for m,v,d in zip(ms,vs,ds)]
        notes+=[('Project %s travel budget'%p,'The Project %s travel budget is %d units, separate from the main budget.'%(p,tr)),
                ('Project %s hardware budget'%p,'The Project %s hardware budget is %d units, separate from the main budget.'%(p,hw)),
                ('Project %s training budget'%p,'The Project %s training budget is %d units, separate from the main budget.'%(p,tn))]
        out.append(('update%02d'%i,'Project %s: what is the current main budget according to the most recent budget note? Answer with the number.'%p,
                    shuffled(notes),[vs[-1]],{'budget':word(vs[-1])},vs[:-1]))
    for i in range(per_kind):
        p=rng.choice(PROJECTS);m1,m2=sorted(rng.sample(range(len(MONTHS)),2));old,new=rng.sample(range(50,99),2);spend=rng.randint(8,40);ts,tsp,hw=rng.randint(10,30),rng.randint(2,9),rng.randint(5,30)
        notes=[('Project %s budget %s'%(p,MONTHS[m1]),'Budget note of %s: the Project %s main budget is %d units.'%(MONTHS[m1],p,old)),
               ('Project %s budget %s'%(p,MONTHS[m2]),'Budget note of %s: the Project %s main budget is %d units.'%(MONTHS[m2],p,new)),
               ('Project %s budget spending'%p,'Spending report: %d units of the Project %s main budget have been spent.'%(spend,p)),
               ('Project %s travel budget'%p,'The Project %s travel budget is %d units, separate from the main budget.'%(p,ts)),
               ('Project %s travel budget spending'%p,'Spending report: %d units of the Project %s travel budget have been spent.'%(tsp,p)),
               ('Project %s hardware budget'%p,'The Project %s hardware budget is %d units, separate from the main budget.'%(p,hw))]
        out.append(('combine%02d'%i,'Project %s: how many units of the main budget are left, using the most recent budget note and the spending report? Answer with the number.'%p,
                    shuffled(notes),[new-spend],{'left':word(new-spend)},[old-spend,new]))
    for i in range(per_kind):
        p=rng.choice(PROJECTS);city=rng.choice(U2.CITIES);n=rng.randint(150,900);fix=n+rng.choice([-1,1])*rng.randint(12,60);fill=rng.sample(U2.FILLER,4);pos=rng.randint(1,3)
        sc,cars,last,team=rng.randint(20,90),rng.randint(40,300),rng.randint(150,900),rng.randint(3,9)
        sents=fill[:pos]+['In %s the Project %s survey counted %d bicycles parked at the station.'%(city,p,n)]+fill[pos:]
        notes=[('Project %s survey bicycles correction'%p,'Correction after the recount: the Project %s survey counted %d bicycles at the station, not %d.'%(p,fix,n)),
               ('Project %s survey scooters'%p,'The Project %s survey counted %d scooters at the station.'%(p,sc)),
               ('Project %s survey cars'%p,'The Project %s survey counted %d cars in the station car park.'%(p,cars)),
               ('Project %s survey bicycles last year'%p,'Last year the Project %s survey counted %d bicycles.'%(p,last)),
               ('Project %s survey team'%p,'The Project %s survey team had %d members.'%(p,team)),
               ('Project %s survey weather'%p,'During the Project %s survey the weather was dry and mild.'%p)]
        out.append(('correction%02d'%i,'Field notes: '+' '.join(sents)+' Question: Project %s survey: how many bicycles were counted at the station this year, taking stored corrections into account?'%p,
                    shuffled(notes),[fix],{'count':word(fix)},[n,last]))
    for i in range(per_kind):
        p=rng.choice(PROJECTS);its=rng.sample(U2.ITEMS,3);vals=[rng.randint(12,95) for _ in its];true=sum(vals);wrong=true+rng.choice([-20,-10,10,20])
        a,b,fc=rng.sample(range(120,300),3);lim,trav=rng.randint(250,400),rng.randint(30,90)
        notes=[('Project %s expenses April'%p,'The Project %s expenses in April totalled %d euros.'%(p,a)),
               ('Project %s expenses March'%p,'The Project %s expenses in March totalled %d euros.'%(p,b)),
               ('Project %s expenses May forecast'%p,'Forecast made in April: Project %s expenses in May were expected to be %d euros.'%(p,fc)),
               ('Project %s expenses limit'%p,'The monthly Project %s expenses limit is %d euros.'%(p,lim)),
               ('Project %s expenses travel'%p,'Project %s travel expenses are booked separately; last trip %d euros.'%(p,trav)),
               ('Project %s expenses approval'%p,'Project %s expenses are approved by the finance office.'%p)]
        out.append(('distract%02d'%i,'Project %s expenses report for May. Items: '%p+', '.join('%s %d euros'%(x,v) for x,v in zip(its,vals))+
                    '. Summary line at the bottom: "Total: %d euros." Is the summary line of this Project %s May expenses report correct? Give the correct total.'%(wrong,p),
                    shuffled(notes),[true],{'total':word(true)},[wrong,a,b,fc]))
    return out

def seed_notes(r,session,notes):
    """Store each note as an operator fact correction in this session (own key, so no note supersedes another)."""
    ids=[]
    for key,value in notes:
        e=r.store.event(session,key);ids.append(r.memory.feedback(e['event_id'],'fact',value,key=key))
    return ids

def layer(head,body):return '' if not body else head+dumps(body)

def swap_layers(system,old_blocks,new_text,anchor):
    """Remove the live memory/hypotheses layers (contiguous, in order) and insert the arm's layers at the same place."""
    present=[b for b in old_blocks if b]
    for b in present:
        if system.count(b)!=1:raise ValueError('layer not unique')
    if present:
        at=system.index(present[0]);span=''.join(present)
        if system[at:at+len(span)]!=span:raise ValueError('layers not contiguous')
        return system[:at]+new_text+system[at+len(span):]
    if system.count(anchor)!=1:raise ValueError('task-context anchor not unique')
    return system.replace(anchor,new_text+anchor)

def arm_views(memories,offers,selected,coalition,slots):
    """Arm -> (memories, body offers) built from the same recalled memories and offers of one turn."""
    coal_mem={x['item_id'] for x in coalition if x['source_kind']=='MEMORY'}
    return {'shipped':(memories,selected),'coalition_gated':([m for m in memories if m['id'] in coal_mem],selected),
            'full_context':(memories,offers),'fixed_slots':(memories[:2],Z.latest_per_role(offers)),
            'retrieval_only':(memories[:slots],[]),'no_context':([],[])}

def clean(text,stale):
    import re
    return not any(re.search(r'(?<![\d.,])'+str(x)+r'(?![\d])',text or '') for x in stale)

def run_rep(installed,rep,fixtures):
    from v13 import effort as EF
    from v13 import focal as F
    from v13 import runtime as RT
    from v13.common import Limits
    from v13.config import initialize,save_config
    from v13.proofs import audit_event
    from v13.prompts import text as prompt
    rows=[];measures=[];sessions=[]
    tmp=tempfile.mkdtemp(prefix='v13-z5b-')
    try:
        home=Path(tmp);cfg=initialize(home)
        for n in ('models','bin'):shutil.rmtree(home/n);(home/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        save_config(home,cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'history_turns':0}|U2.BENCH_CFG|CFG)
        r=RT.Runtime(home);EF.set_mode(r.store,'max')
        cap={}
        orig_loop,orig_save,orig_admit=RT.FocalLoop,RT.save_context,F.admit
        def admit(cands,capacity,threshold,interrupt=F.BOOT['sal_interrupt']):
            a,rest=orig_admit(cands,capacity,threshold,interrupt)
            cap['admissions']=[c.get('admission') for c in a+rest];cap['n_candidates']=len(cands)
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
                base={'rep':rep,'fixture':fid,'kind':fid.rstrip('0123456789')}
                run=cap.get('run');msgs=cap.get('messages')
                rows.append(base|{'arm':'shipped_live','pass':all(ok.values()) and all(num.values()),'clean':clean(out,stale),'turn_s':turn_s,'status':a.get('status'),
                                  'answer_role':cap.get('answer_role'),'output':out[:400]})
                plan_applied=(meta.get('context_plan') or {}).get('applied')
                if run is None or msgs is None or plan_applied:
                    for arm in REPLAY:rows.append(base|{'arm':arm,'pass':False,'skipped':'NO_FOCAL_RUN' if run is None else 'NO_MESSAGES' if msgs is None else 'CONTEXT_PLAN_APPLIED'})
                    print(json.dumps({'rep':rep,'fixture':fid,'skipped':True}),flush=True);continue
                m=Z.focal_measure(r.store,eid,run,cap['slots'])
                coal_mem=[x for x in run['coalition'] if x['source_kind']=='MEMORY']
                m.update(recalled=len(cap['memories']),max_candidates=cap.get('max_candidates',0),coalition_memories=len(coal_mem),
                         coalition_bodies=len(run['coalition'])-len(coal_mem),selected_offers=len(run['selected']),
                         capacity_rejections_all_admits=cap.get('all_admissions',[]).count('CAPACITY'),
                         needed_note_in_coalition=None)
                measures.append(base|m)
                e,version=cap['e'],cap['version'];sysmsg=msgs[0]['content']
                live_mem=layer(mem_head,r.memory.report_context(text,cap['memories']) if cap['memories'] else None)
                live_hyp=layer(hyp_head,r.cognition.analyst_context(run['selected'],e,version) if run['selected'] else None)
                line={'rep':rep,'fixture':fid,'role':cap['answer_role'],'live':rows[-1]['pass'],'turn_s':turn_s,'cand':m['max_candidates'],'coal_mem':len(coal_mem),'sel':len(run['selected'])}
                for arm,(mems,subs) in arm_views(cap['memories'],run['offers'],run['selected'],run['coalition'],r.cfg['focal_slots']).items():
                    try:new=layer(mem_head,r.memory.report_context(text,mems) if mems else None)+layer(hyp_head,r.cognition.analyst_context(subs,e,version) if subs else None)
                    except Exception as exc:rows.append(base|{'arm':arm,'pass':False,'skipped':'CONTEXT_REJECTED','error':type(exc).__name__+': '+str(exc)[:200]});continue
                    try:system=swap_layers(sysmsg,(live_mem,live_hyp),new,anchor)
                    except ValueError as exc:rows.append(base|{'arm':arm,'pass':False,'skipped':'LAYER_SWAP_FAILED','error':str(exc)});continue
                    mm=[{'role':'system','content':system}]+msgs[1:];key=hashlib.sha256(dumps(mm).encode()).hexdigest()
                    t1=time.monotonic()
                    if key not in cache:
                        try:cache[key]=''.join(r.pool.get(cap['answer_role']).generate(mm,r.cancel_event,time.monotonic()+300))
                        except Limits as exc:rows.append(base|{'arm':arm,'pass':False,'skipped':'CONTEXT_WINDOW','context_chars':len(new),'error':str(exc)[:200]});continue
                    o=cache[key];ok,num=U.score(o,nums,checks)
                    rows.append(base|{'arm':arm,'pass':all(ok.values()) and all(num.values()),'clean':clean(o,stale),'gen_s':round(time.monotonic()-t1,2),'context_hash':key[:16],
                                      'context_chars':len(new),'memories':len(mems),'offers':len(subs),'answer_role':cap['answer_role'],'same_as_live':o.strip()==out.strip(),'output':o[:400]})
                    line[arm]=rows[-1]['pass']
                print(json.dumps(line),flush=True)
        finally:
            RT.FocalLoop,RT.save_context,F.admit=orig_loop,orig_save,orig_admit
            r.close()
        retention=Z.restart_retention(home,sessions)
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
    return rows,measures,retention

def analyse(rows,measures,retention):
    """Z5 statistics with the Z5b arm names; the gate-part comparison is coalition_gated vs full_context."""
    ren={'coalition_gated':'coalition'}
    rr=[x|{'arm':ren.get(x['arm'],x['arm'])} for x in rows if x['arm']!='shipped_live']+[x|{'arm':'coalition_live'} for x in rows if x['arm']=='shipped_live']
    saved=Z.CONTROLS;Z.CONTROLS=CONTROLS
    try:res=Z.analyse(rr,[x|{'all_offers_selected':False} for x in measures],retention)
    finally:Z.CONTROLS=saved
    res['summary']={({'coalition':'coalition_gated','coalition_live':'shipped_live'}).get(k,k):v for k,v in res['summary'].items()}
    res['by_kind']={({'coalition':'coalition_gated','coalition_live':'shipped_live'}).get(k,k):v for k,v in res['by_kind'].items()}
    res['paired']={k.replace('coalition_vs_','coalition_gated_vs_').replace('vs_coalition_live','vs_shipped_live'):v for k,v in res['paired'].items()}
    # replay fidelity is shipped (replay) vs shipped_live, not coalition vs live
    by={(x['rep'],x['fixture']):x for x in rows if x['arm']=='shipped' and not x.get('skipped')}
    res['verdict']['replay_fidelity']=round(sum(v.get('same_as_live',False) for v in by.values())/max(1,len(by)),3);res['verdict']['replay_caveat']=res['verdict']['replay_fidelity']<.95
    res['verdict']['noise_band']=_band(rows,'shipped_live')
    pf=res['paired'].get('coalition_gated_vs_full_context',{});band=res['verdict']['noise_band']
    beats='PASS' if pf.get('sign_test_p',1)<.05 and pf.get('coalition_only',0)>pf.get('control_only',0) and band is not None and pf.get('mean_lead_per_rep',0)>band else 'FAIL'
    res['verdict']['beats_full_context']=beats
    n=len(measures);bound=sum(m['max_candidates']>m['slots'] for m in measures)
    res['verdict']['capacity_bound_rate']=round(bound/max(1,n),3)
    if bound/max(1,n)<.5:res['verdict']['beats_full_context']='NOT_TESTABLE_CAPACITY_RARELY_BINDS'
    res['properties']['1_capacity_limit']={'turns_capacity_bound':bound,'turns':n,'capacity_rejections':sum(m['capacity_rejections_all_admits'] for m in measures)}
    res['verdict']['properties_observed']['1_capacity_limit']=bound>0
    obs=res['verdict']['properties_observed'];nw=res['verdict']
    res['verdict']['gate']='GREEN' if res['verdict']['beats_full_context']=='PASS' and all(obs.values()) and nw['not_worse_than_retrieval_only'] and nw['not_worse_than_fixed_slots'] else 'PARTIAL'
    res['clean']={arm:round(sum(x.get('clean',False) for x in rows if x['arm']==arm and not x.get('skipped'))/max(1,sum(1 for x in rows if x['arm']==arm and not x.get('skipped'))),3) for arm in ARMS}
    res['coalition_mix']={'mean_recalled':round(sum(m['recalled'] for m in measures)/max(1,n),2),'mean_max_candidates':round(sum(m['max_candidates'] for m in measures)/max(1,n),2),
                          'mean_coalition_memories':round(sum(m['coalition_memories'] for m in measures)/max(1,n),2),'mean_coalition_bodies':round(sum(m['coalition_bodies'] for m in measures)/max(1,n),2),
                          'mean_selected_offers':round(sum(m['selected_offers'] for m in measures)/max(1,n),2)}
    return res

def _band(rows,arm):
    reps=sorted({x['rep'] for x in rows});per=[sum(x['pass'] for x in rows if x['arm']==arm and x['rep']==rp) for rp in reps]
    return max(per)-min(per) if len(per)>1 else None

def main(installed,out,reps=5,limit=None):
    installed=Path(installed).resolve();out=Path(out);fx=tasks()
    if limit:fx=[f for i,f in enumerate(fx) if i%(len(fx)//limit)==0][:limit]
    prev=json.loads(out.read_text()) if out.exists() else {}
    rows,measures,retention=prev.get('rows',[]),prev.get('measures',[]),prev.get('retention',[])
    done={x['rep'] for x in rows}
    for rep in range(1,reps+1):
        if rep in done:continue
        rr,mm,ret=run_rep(installed,rep,fx);rows+=rr;measures+=mm;retention.append(ret|{'rep':rep})
        atomic_write(out,json.dumps({'kind':'WP_Z5B_CAPACITY','preregistration':'bench-results/z5b-capacity-20261021/PREREGISTRATION.md',
            'bench_cfg':U2.BENCH_CFG|CFG|{'effort':'max'},'fixtures':[f[0] for f in fx],'reps_done':sorted({x['rep'] for x in rows}),
            **analyse(rows,measures,retention),'rows':rows,'measures':measures,'retention':retention,
            'claim_limit':'generated English tasks, one seed, regex on the final answer, lexical recall, greedy bench decoding, cloud CPU'},indent=1))
    print(json.dumps(analyse(rows,measures,retention)['verdict'],indent=1))

if __name__=='__main__':
    a=sys.argv[1:];reps=5;lim=None
    if '--reps' in a:i=a.index('--reps');reps=int(a[i+1]);del a[i:i+2]
    if '--limit' in a:i=a.index('--limit');lim=int(a[i+1]);del a[i:i+2]
    main(a[0],a[1],reps,lim)
