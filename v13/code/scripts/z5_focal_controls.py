"""WP-Z5: focal coalition (B4/C4) against the three §99 controls on the 60 WP-T3b tasks (real C3/B1/B2, cloud, English).

Preregistered in bench-results/z5-focal-controls-20261021/PREREGISTRATION.md before any model run.
Per repetition one fresh home, effort 'max' for every task (same candidate pool for every arm), WP-T3b bench mode.
  coalition_live   the shipped turn: focal loop picks the coalition, the organ C5 selects answers with it (live)
After the focal loop of that same turn the context of the other arms is built from the same offers with the real
analyst_context (binding/freshness checks still apply); the real answer message is reused and sent greedily to the same organ C5 picked live (with effort max mostly B1 or B2, not C3); only the hypotheses layer differs:
  coalition        replay with exactly the live coalition (replay fidelity against coalition_live)
  full_context     every offer of the turn (first offers and re-entry), no selection
  fixed_slots      one fixed slot per body holding its newest offer, no competition/threshold/interrupt
  retrieval_only   no body offer; the k=focal_slots sentences of the user message most relevant to the question, verbatim
  no_hypotheses    no hypotheses layer (reference; the answering organ alone with the user message)
The 7 G-FOCAL-CAPACITY-003 properties are measured from FocalCycle/FocalItem/Workspace telemetry of the live turns,
retention/recovery after a restart on the same home.
Claim limit: generated English tasks, one seed, regex checks on the final answer, lexical retrieval, greedy bench decoding.
Usage: z5_focal_controls.py <installed_home> <out.json> [--reps N] [--limit N]"""
import hashlib
import json
import re
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

ARMS=('coalition_live','coalition','full_context','fixed_slots','retrieval_only','no_hypotheses')
REPLAY=ARMS[1:]
CONTROLS=('full_context','fixed_slots','retrieval_only','no_hypotheses')
RETRIEVED_HEAD='\nRetrieved passages from the user message (exact quotes, ranked by relevance to the question): '
SENT=re.compile(r'(?<=[.!?])\s+')

def split_question(text):
    """Material and question of a WP-T3b task: the question is the last sentence(s) after the material."""
    for mark in ('Question:',' Is the summary',' Which ',' The notes disagree.'):
        i=text.rfind(mark)
        if i>0:return text[:i].strip(),text[i:].strip()
    return text,text

def retrieve(text,k):
    from v13.memory import relevance
    material,question=split_question(text)
    parts=[p.strip() for p in re.split(r'(?<=[.!?:])\s+|,\s+(?=[A-Z][a-z]+ \d)',material) if p.strip()]
    ranked=sorted(range(len(parts)),key=lambda i:(-relevance(question,parts[i]),i))[:k]
    return [parts[i] for i in sorted(ranked)]

def latest_per_role(offers):
    by={}
    for p in offers:by[p['role']]=p
    return [by[r] for r in ('B1_DETAIL','B2_GIST') if r in by]

def swap_layer(system,hyp_head,old_body,new_block,anchor):
    """Replace the hypotheses layer of the real C3 system message (or insert before the task-context layer)."""
    if old_body is not None:
        old=hyp_head+dumps(old_body)
        if system.count(old)!=1:raise ValueError('hypotheses layer not unique')
        return system.replace(old,new_block)
    if system.count(anchor)!=1:raise ValueError('task-context anchor not unique')
    return system.replace(anchor,new_block+anchor)

def focal_measure(store,eid,run,slots):
    """The 7 G-FOCAL-CAPACITY-003 properties of one live turn from its real focal telemetry."""
    items=[json.loads(r['payload']) for r in store.rows("SELECT payload FROM packets WHERE kind='FocalItem' AND event_id=?",(eid,))]
    traj=run['trajectory']
    first=[p for p in run['offers'] if p['packet_id'] not in {t.get('query_offer_id') for t in traj}]
    adm={}
    for c in run.get('_admissions',[]):adm[c]=adm.get(c,0)+1
    reentry=[t for t in traj if t.get('query_offer_id')]
    coal_ids={x['item_id'] for x in run['coalition']}
    bound=0
    for x in run['coalition']:
        try:
            for ref in x['source_refs']:store.read_source(ref)
            bound+=1
        except (ValueError,OSError,KeyError,TypeError):pass
    return {'candidates':run.get('_n_candidates',0),'slots':slots,'capacity_bound':run.get('_n_candidates',0)>slots,
            'coalition':len(run['coalition']),'offers':len(run['offers']),'first_offers':len(first),'admissions':adm,
            'rejected':adm.get('BELOW_THRESHOLD',0)+adm.get('CAPACITY',0),'displaced':adm.get('DISPLACED_BY_SALIENCE_INTERRUPT',0),
            'salience_interrupt':adm.get('SALIENCE_INTERRUPT',0),'reentry':len(reentry),
            'reentry_in_coalition':sum(t['query_offer_id'] in coal_ids for t in reentry),'source_bound':bound,
            'all_offers_selected':len(run['selected'])==len(run['offers']),'cycles':len(traj),'decision':run['decision'],
            'inquisition':[x['verdict'] for x in run['inquisition']],'focal_items_logged':len(items)}

def run_rep(installed,rep,fixtures):
    from v13 import effort as EF
    from v13 import focal as F
    from v13 import runtime as RT
    from v13.config import initialize,save_config
    from v13.proofs import audit_event
    from v13.prompts import text as prompt
    rows=[];measures=[];sessions=[]
    tmp=tempfile.mkdtemp(prefix='v13-z5-')
    try:
        home=Path(tmp);cfg=initialize(home)
        for n in ('models','bin'):shutil.rmtree(home/n);(home/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        save_config(home,cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'history_turns':0}|U2.BENCH_CFG)
        r=RT.Runtime(home);EF.set_mode(r.store,'max')
        cap={}
        orig_loop,orig_save,orig_admit=RT.FocalLoop,RT.save_context,F.admit
        def admit(cands,capacity,threshold,interrupt=F.BOOT['sal_interrupt']):
            a,rest=orig_admit(cands,capacity,threshold,interrupt)
            cap['admissions']=[c.get('admission') for c in a+rest];cap['n_candidates']=len(cands)
            return a,rest
        class Loop(orig_loop):
            def run(self,e,version,offers,**kw):
                out=super().run(e,version,offers,**kw);cap['run']=out;cap['slots']=max(1,min(int((kw.get('plan') or {}).get('focal_slots') or 1),r.cfg['focal_slots']))
                out['_admissions']=cap.get('admissions',[]);out['_n_candidates']=cap.get('n_candidates',0)
                ctx={}
                for arm,sub in (('coalition',out['selected']),('full_context',out['offers']),('fixed_slots',latest_per_role(out['offers']))):
                    try:ctx[arm]=r.cognition.analyst_context(sub,e,version) if sub else None
                    except Exception as exc:ctx[arm]={'error':type(exc).__name__+': '+str(exc)[:200]}
                cap['ctx']=ctx;return out
        def save(store,session,eid,role,messages):
            cap['messages']=json.loads(json.dumps(messages));cap['answer_role']=role
            return orig_save(store,session,eid,role,messages)
        RT.FocalLoop,RT.save_context,F.admit=Loop,save,admit
        try:
            hyp_head='\n'+prompt(r.cfg,'hypotheses');anchor='\n'+prompt(r.cfg,'task_context')
            cache={}
            for fid,text,nums,checks in fixtures:
                cap.clear();r.session=r.store.new_session();sessions.append(r.session);t0=time.monotonic();eid=r.submit(text);end=t0+900
                while not r.idle():
                    if time.monotonic()>end:r.cancel();break
                    time.sleep(.1)
                a=audit_event(r.store,eid);out=a.get('output') or '';meta=a.get('output_metadata') or {};turn_s=round(time.monotonic()-t0,2)
                ok,num=U.score(out,nums,checks)
                base={'rep':rep,'fixture':fid,'kind':fid.rstrip('0123456789')}
                rows.append(base|{'arm':'coalition_live','pass':all(ok.values()) and all(num.values()),'turn_s':turn_s,'status':a.get('status'),
                                  'context_chars':len(dumps(cap['ctx']['coalition'])) if cap.get('ctx',{}).get('coalition') else 0,'output':out[:400]})
                run=cap.get('run');msgs=cap.get('messages')
                plan_applied=(meta.get('context_plan') or {}).get('applied')
                if run is None or msgs is None or plan_applied:
                    for arm in REPLAY:rows.append(base|{'arm':arm,'pass':False,'skipped':'NO_FOCAL_RUN' if run is None else 'NO_C3_MESSAGES' if msgs is None else 'CONTEXT_PLAN_APPLIED'})
                    print(json.dumps({'rep':rep,'fixture':fid,'skipped':True,'roles':[o['role'] for o in a.get('offers',[])]}),flush=True);continue
                measures.append(base|focal_measure(r.store,eid,run,cap['slots']))
                sysmsg=msgs[0]['content'];coal=cap['ctx'].get('coalition')
                blocks={'no_hypotheses':'','retrieval_only':RETRIEVED_HEAD+dumps(retrieve(text,r.cfg['focal_slots']))}
                for arm in ('coalition','full_context','fixed_slots'):
                    body=cap['ctx'].get(arm)
                    blocks[arm]=None if isinstance(body,dict) and 'error' in body else ('' if body is None else hyp_head+dumps(body))
                line={'rep':rep,'fixture':fid,'role':cap['answer_role'],'live':rows[-1]['pass'],'turn_s':turn_s,'offers':len(run['offers']),'coalition':len(run['coalition'])}
                for arm in REPLAY:
                    if blocks[arm] is None:rows.append(base|{'arm':arm,'pass':False,'skipped':'ANALYST_CONTEXT_REJECTED','error':cap['ctx'][arm]['error']});continue
                    try:system=swap_layer(sysmsg,hyp_head,coal,blocks[arm],anchor)
                    except ValueError as exc:rows.append(base|{'arm':arm,'pass':False,'skipped':'LAYER_SWAP_FAILED','error':str(exc)});continue
                    m=[{'role':'system','content':system}]+msgs[1:];key=hashlib.sha256(dumps(m).encode()).hexdigest()
                    t1=time.monotonic()
                    if key not in cache:cache[key]=''.join(r.pool.get(cap['answer_role']).generate(m,r.cancel_event,time.monotonic()+300))
                    o=cache[key];ok,num=U.score(o,nums,checks)
                    rows.append(base|{'arm':arm,'pass':all(ok.values()) and all(num.values()),'gen_s':round(time.monotonic()-t1,2),'context_hash':key[:16],
                                      'context_chars':len(blocks[arm]),'answer_role':cap['answer_role'],'same_as_live':o.strip()==out.strip(),'output':o[:400]})
                    line[arm]=rows[-1]['pass']
                print(json.dumps(line),flush=True)
        finally:
            RT.FocalLoop,RT.save_context,F.admit=orig_loop,orig_save,orig_admit
            r.close()
        retention=restart_retention(home,sessions)
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
    return rows,measures,retention

def restart_retention(home,sessions):
    """Property 7: after a restart (new Store on the same home) the saved workspace slots must be restorable from the store."""
    from v13.focal import Workspace
    from v13.store import Store
    s=Store(home);saved=restored=bound=0
    try:
        for sid in sessions:
            ws=Workspace(s,sid);st,_=s.state(ws.key,{})
            for slot in (st or {}).get('slots',[]):
                saved+=1;txt=ws._text(slot);restored+=txt is not None
                try:
                    for ref in slot['source_refs']:s.read_source(ref)
                    bound+=1
                except (ValueError,OSError,KeyError,TypeError):pass
    finally:
        close=getattr(s,'close',None)
        if close:close()
    return {'sessions':len(sessions),'slots_saved':saved,'slots_restored':restored,'slots_source_bound':bound}

def analyse(rows,measures,retention):
    by={}
    for x in rows:
        if x.get('skipped'):continue
        by.setdefault(x['arm'],{})[(x['rep'],x['fixture'])]=x
    reps=sorted({x['rep'] for x in rows})
    summary={arm:{'n':len(m),'pass':sum(v['pass'] for v in m.values()),'pass_rate':round(sum(v['pass'] for v in m.values())/max(1,len(m)),3),
                  'per_rep':[sum(v['pass'] for k,v in m.items() if k[0]==rp) for rp in reps],
                  'mean_context_chars':round(sum(v.get('context_chars',0) for v in m.values())/max(1,len(m)),1)} for arm,m in by.items()}
    live=summary.get('coalition_live',{}).get('per_rep',[])
    band=max(live)-min(live) if len(live)>1 else None
    paired={}
    coal=by.get('coalition',{})
    for arm in CONTROLS+('coalition_live',):
        m=by.get(arm,{});common=[k for k in m if k in coal]
        w=sum(coal[k]['pass'] and not m[k]['pass'] for k in common);l=sum(m[k]['pass'] and not coal[k]['pass'] for k in common)
        per=[sum(coal[k]['pass'] for k in common if k[0]==rp)-sum(m[k]['pass'] for k in common if k[0]==rp) for rp in reps]
        paired['coalition_vs_'+arm]={'n':len(common),'coalition_only':w,'control_only':l,'sign_test_p':round(U2.sign_test(w,l),4),
                                     'mean_lead_per_rep':round(sum(per)/max(1,len(per)),2),'lead_per_rep':per,
                                     'identical_context':sum(m[k].get('context_hash')==coal[k].get('context_hash') for k in common)}
    by_kind={}
    for arm,m in by.items():
        k={}
        for (rp,f),v in m.items():kk=v['kind'];k.setdefault(kk,[0,0]);k[kk][0]+=v['pass'];k[kk][1]+=1
        by_kind[arm]={kk:round(a/b,3) for kk,(a,b) in sorted(k.items())}
    fid=by.get('coalition',{});lv=by.get('coalition_live',{})
    fidelity=sum(fid[k].get('same_as_live',False) for k in fid if k in lv)/max(1,len(fid))
    n=len(measures)
    props={'1_capacity_limit':{'turns_capacity_bound':sum(m['capacity_bound'] for m in measures),'turns':n},
           '2_competition':{'rejected_candidates':sum(m['rejected'] for m in measures),'candidates':sum(m['candidates'] for m in measures)},
           '3_priority_replacement':{'displaced':sum(m['displaced'] for m in measures)},
           '4_salience_interrupt':{'admitted_by_interrupt':sum(m['salience_interrupt'] for m in measures)},
           '5_reentry':{'turns_with_reentry':sum(m['reentry']>0 for m in measures),'reentry_offers':sum(m['reentry'] for m in measures),
                        'reentry_offers_in_coalition':sum(m['reentry_in_coalition'] for m in measures)},
           '6_source_binding':{'coalition_items':sum(m['coalition'] for m in measures),'source_bound':sum(m['source_bound'] for m in measures)},
           '7_retention_recovery':{k:sum(x[k] for x in retention) for k in ('sessions','slots_saved','slots_restored','slots_source_bound')}}
    observed={'1_capacity_limit':props['1_capacity_limit']['turns_capacity_bound']>0,'2_competition':props['2_competition']['rejected_candidates']>0,
              '3_priority_replacement':props['3_priority_replacement']['displaced']>0,'4_salience_interrupt':props['4_salience_interrupt']['admitted_by_interrupt']>0,
              '5_reentry':props['5_reentry']['reentry_offers_in_coalition']>0,
              '6_source_binding':props['6_source_binding']['coalition_items']>0 and props['6_source_binding']['source_bound']==props['6_source_binding']['coalition_items'],
              '7_retention_recovery':props['7_retention_recovery']['slots_saved']>0 and props['7_retention_recovery']['slots_restored']==props['7_retention_recovery']['slots_saved']}
    all_sel=sum(m['all_offers_selected'] for m in measures)/max(1,n)
    pf=paired.get('coalition_vs_full_context',{})
    if all_sel>=.95:beats='NOT_TESTABLE_CAPACITY_NEVER_BINDS'
    elif pf.get('sign_test_p',1)<.05 and pf.get('coalition_only',0)>pf.get('control_only',0) and band is not None and pf.get('mean_lead_per_rep',0)>band:beats='PASS'
    else:beats='FAIL'
    def not_worse(arm):
        p=paired.get('coalition_vs_'+arm,{});return not (p.get('sign_test_p',1)<.05 and p.get('control_only',0)>p.get('coalition_only',0))
    verdict={'beats_full_context':beats,'not_worse_than_retrieval_only':not_worse('retrieval_only'),'not_worse_than_fixed_slots':not_worse('fixed_slots'),
             'all_offers_selected_rate':round(all_sel,3),'replay_fidelity':round(fidelity,3),'replay_caveat':fidelity<.95,'noise_band':band,
             'properties_observed':observed,
             'gate':'GREEN' if beats=='PASS' and all(observed.values()) and not_worse('retrieval_only') and not_worse('fixed_slots') else 'PARTIAL'}
    return {'summary':summary,'paired':paired,'by_kind':by_kind,'properties':props,'verdict':verdict}

def main(installed,out,reps=5,limit=None):
    installed=Path(installed).resolve();out=Path(out);fx=U2.tasks()
    if limit:fx=[f for i,f in enumerate(fx) if i%(len(fx)//limit)==0][:limit]
    prev=json.loads(out.read_text()) if out.exists() else {}
    rows,measures,retention=prev.get('rows',[]),prev.get('measures',[]),prev.get('retention',[])
    done={x['rep'] for x in rows}
    for rep in range(1,reps+1):
        if rep in done:continue
        rr,mm,ret=run_rep(installed,rep,fx);rows+=rr;measures+=mm;retention.append(ret|{'rep':rep})
        atomic_write(out,json.dumps({'kind':'WP_Z5_FOCAL_CONTROLS','preregistration':'bench-results/z5-focal-controls-20261021/PREREGISTRATION.md',
            'bench_cfg':U2.BENCH_CFG|{'effort':'max'},'fixtures':[f[0] for f in fx],'reps_done':sorted({x['rep'] for x in rows}),
            **analyse(rows,measures,retention),'rows':rows,'measures':measures,'retention':retention,
            'claim_limit':'generated English tasks, one seed, regex on the final answer, lexical retrieval, greedy bench decoding, cloud CPU'},indent=1))
    print(json.dumps(analyse(rows,measures,retention)['verdict'],indent=1))

if __name__=='__main__':
    a=sys.argv[1:];reps=5;lim=None
    if '--reps' in a:i=a.index('--reps');reps=int(a[i+1]);del a[i:i+2]
    if '--limit' in a:i=a.index('--limit');lim=int(a[i+1]);del a[i:i+2]
    main(a[0],a[1],reps,lim)
