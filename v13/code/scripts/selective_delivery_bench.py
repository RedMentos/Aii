#!/usr/bin/env python3
"""WP-T9 rest: serve a fact either as parametric fast trace or as exact block, not both (paired frozen corpus, native C3).

Arms (same native llama-server-mem binary, same C3 GGUF, same live system message as runtime._turn / memory_trainer.live_system):
  base        no trace, no exact block
  exact       exact block from the full exact store (all 40 facts), lexical recall as runtime (memory.relevance >= threshold, top_k)
  trace       trace only; the trace holds the 'consolidated' subset T (20 facts, corpus split seed), the rest is not in it
  combined    trace + exact block for every recalled fact (what the runtime would do today if the trace were served)
  selective   trace + exact block only for recalled facts NOT covered by the trace (dedupe: a fact goes one way, not both)
Sets: 40 fact questions, 40 paraphrases, 40 near-miss questions (stored key must not appear), 12 retention probes.
The trace is trained once on T with v13.memory_trainer.SparseMemoryAG6Trainer (keyed slots + entity guard, keys written on the
dequantized deployed Q4 weights in the live system context, as bench-results/memory-350m-20261010) and exported as V13SMEM1 .bin.
Native slot firing is recorded per answer (V13_MEMORY_AUDIT) for the trace arms. Every answer is checkpointed; --resume only with
identical binding. Nothing is activated; runtime code is imported read-only (frozen SourceHandoff cohort).
  python3 scripts/selective_delivery_bench.py --home HOME --master DIR --gguf C3.gguf --out DIR [--resume]
Preregistration: code/docs/proofs/selective-delivery-20261012/preregistration.json (decision rule there)."""
import argparse,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from selective_delivery_corpus import FACTS,split  # noqa: E402
from lora_bench import ANCHORS,PROBES  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.memory import relevance  # noqa: E402
from v13.memory_trainer import live_system,SparseMemoryAG6Trainer  # noqa: E402
from v13.config import DEFAULTS  # noqa: E402
from v13.common import atomic_write,dumps,digest,file_hash  # noqa: E402
from v13.sparse_audit import read_firing_window  # noqa: E402
from v13.memory_server import runtime_library_hashes  # noqa: E402

ARMS=('base','exact','trace','combined','selective')

def sets():
    return {'facts':[(q,k,i) for i,(q,_,k,_,_) in enumerate(FACTS)],'paraphrase':[(p,k,i) for i,(_,_,k,p,_) in enumerate(FACTS)],
            'near_miss':[(n,k,i) for i,(_,_,k,_,n) in enumerate(FACTS)],'probes':[(p['prompt'],p['expect'],None) for p in PROBES]}

def recalled(question,store):
    scored=sorted(((relevance(question,FACTS[i][0]),i) for i in store),reverse=True)
    return [i for sc,i in scored if sc>=DEFAULTS['memory_threshold']][:DEFAULTS['memory_top_k']]

def system(question,arm,trace_ids):
    if arm in ('base','trace'):return live_system(),[]
    rec=recalled(question,range(len(FACTS)))
    if arm=='selective':rec=[i for i in rec if i not in trace_ids]
    mem=[{'topic':FACTS[i][0],'correction':FACTS[i][1]} for i in rec]
    return (live_system(memories=mem) if mem else live_system()),rec

def serve(binary,model,mem,port,log,audit):
    env=dict(os.environ);env.pop('V13_MEMORY_FILE',None);env.pop('V13_MEMORY_AUDIT',None)
    if mem:env['V13_MEMORY_FILE']=str(mem)
    if mem and audit:env['V13_MEMORY_AUDIT']='1'
    with open(log,'a') as err:
        p=subprocess.Popen([str(binary),'-m',str(model),'--port',str(port),'-ngl','0','-t','4','-c','4096','-np','1','-b','128','-ub','128','--no-webui','--no-warmup'],
                           env=env,stdout=subprocess.DEVNULL,stderr=err)
    for _ in range(180):
        if p.poll() is not None:raise RuntimeError('server exited: '+open(log).read()[-400:])
        try:
            if json.loads(urllib.request.urlopen('http://127.0.0.1:%d/health'%port,timeout=2).read()).get('status')=='ok':return p
        except Exception:time.sleep(1)
    p.terminate();raise RuntimeError('server did not start')

def ask(port,sys_text,q):
    b=json.dumps({'messages':[{'role':'system','content':sys_text},{'role':'user','content':q}],'max_tokens':40,'temperature':0,'seed':13,'cache_prompt':True}).encode()
    t=time.monotonic();r=json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/v1/chat/completions'%port,b,{'Content-Type':'application/json'}),timeout=300).read())
    return r['choices'][0]['message']['content'],r['usage']['prompt_tokens'],time.monotonic()-t

def train(master,gguf,out,trace_ids):
    meta=out/'trace.json'
    if meta.is_file():
        r=json.loads(meta.read_text())
        if Path(r['artifact']).is_file() and file_hash(r['artifact'])==r['hash']:return r
    items=[{'memory_id':'sel_%d'%i,'prompt':FACTS[i][0],'target':FACTS[i][1],'answer_keys':FACTS[i][2]} for i in trace_ids]
    tr=SparseMemoryAG6Trainer(master,out/'work',background=ANCHORS,probes=PROBES,
                              cfg={'threads':4,'base_gguf':str(gguf),'entity_guard':True,'system':live_system(),'contexts':[''],'max_tokens':256})
    r=tr.fit(items,'selective-delivery-20261012')
    if not r.get('artifact'):raise RuntimeError('trace training produced no artifact: '+json.dumps(r.get('metrics'),default=str)[:400])
    r={'artifact':r['artifact'],'hash':r['hash'],'metrics':{k:v for k,v in r['metrics'].items() if k not in ('history','top_scores')},'eval':r['eval']}
    atomic_write(meta,json.dumps(r,indent=1,default=str));return r

def paired(rep,a,b,keys):
    w=l=0
    for k in keys:
        ra={(x['index']):x['hit'] for x in rep[a][k+'_rows']};rb={(x['index']):x['hit'] for x in rep[b][k+'_rows']}
        for i in ra:w+=ra[i] and not rb[i];l+=rb[i] and not ra[i]
    return {'wins':int(w),'losses':int(l)}

def summarize(rep,trace_ids):
    T=set(trace_ids)
    for arm in ARMS:
        r=rep[arm];rows=[x for k in sets() for x in r[k+'_rows']]
        for k in sets():
            rr=r[k+'_rows'];r[k]=round(sum(x['hit'] for x in rr)/len(rr),4)
            if k!='probes':
                r[k+'_in_trace']=round(sum(x['hit'] for x in rr if x['fact'] in T)/len(T),4)
                r[k+'_not_in_trace']=round(sum(x['hit'] for x in rr if x['fact'] not in T)/(len(FACTS)-len(T)),4)
        r['prompt_tokens_mean']=round(sum(x['prompt_tokens'] for x in rows)/len(rows),2)
        r['seconds_mean']=round(sum(x['seconds'] for x in rows)/len(rows),3)
        r['exact_blocks_mean']=round(sum(len(x['exact_ids']) for x in rows)/len(rows),3)
        fired=[x['native_firing'] for x in rows if 'native_firing' in x]
        if fired:r['firing_status']={s:sum(1 for f in fired if f.get('status')==s) for s in sorted({f.get('status') for f in fired})}
        base={x['index']:x['hit'] for x in rep['base']['probes_rows']}
        r['forgotten_probes']=[x['q'] for x in r['probes_rows'] if base[x['index']] and not x['hit']]
    recall=('facts','paraphrase')
    rep['paired']={'selective_vs_exact':paired(rep,'selective','exact',recall),'selective_vs_combined':paired(rep,'selective','combined',recall),
                   'trace_vs_exact':paired(rep,'trace','exact',recall),'combined_vs_exact':paired(rep,'combined','exact',recall),
                   'near_miss_leak_selective_minus_exact':round(rep['selective']['near_miss']-rep['exact']['near_miss'],4)}
    s,e,c=rep['selective'],rep['exact'],rep['combined'];p=rep['paired']['selective_vs_exact']
    crit={'recall_not_worse_than_exact':p['losses']<=p['wins'],'leak_not_higher_than_exact':s['near_miss']<=e['near_miss'],
          'fewer_prompt_tokens_than_exact':s['prompt_tokens_mean']<e['prompt_tokens_mean'],'no_probe_forgotten_beyond_exact':len(s['forgotten_probes'])<=len(e['forgotten_probes'])}
    rep['decision']={'criteria':crit,'verdict':'SELECTIVE_WINS_CANDIDATE' if all(crit.values()) else 'SELECTIVE_DOES_NOT_WIN',
                     'combined_vs_exact_recall':rep['paired']['combined_vs_exact'],
                     'consequence':'candidate for a separately preregistered runtime change after the SourceHandoff freeze; nothing activated' if all(crit.values()) else 'keep exact delivery; AG6 auto keeps not choosing the sparse trainer'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--home',required=True);ap.add_argument('--master',required=True);ap.add_argument('--gguf',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    home,out=Path(a.home),Path(a.out);out.mkdir(parents=True,exist_ok=True);binary=home/'bin/llama-server-mem'
    trace_ids,_=split();t0=time.monotonic();tr=train(a.master,a.gguf,out,trace_ids);train_s=round(time.monotonic()-t0,1)
    binding={'binary_sha256':file_hash(binary),'runtime_libraries_sha256':runtime_library_hashes(binary),'model_sha256':file_hash(a.gguf),
             'master_sha256':file_hash(Path(a.master)/'model.safetensors'),'trace_sha256':tr['hash'],
             'corpus_sha256':digest(dumps({'facts':FACTS,'probes':PROBES,'anchors':ANCHORS,'trace_ids':trace_ids})),
             'script_sha256':file_hash(__file__),'corpus_file_sha256':file_hash(Path(__file__).parent/'selective_delivery_corpus.py'),
             'memory_py_sha256':file_hash(Path(__file__).parents[1]/'v13/memory.py'),'prompts_sha256':digest(live_system()),
             'memory_threshold':DEFAULTS['memory_threshold'],'memory_top_k':DEFAULTS['memory_top_k'],'temperature':0,'max_tokens':40,'seed':13,'cache_prompt':True}
    target=out/'report.json'
    if target.exists() and not a.resume:raise SystemExit('report exists; use --resume')
    rep=json.loads(target.read_text()) if target.exists() else {}
    if rep and rep.get('binding')!=binding:raise SystemExit('binding differs; keep this proof and use a new --out')
    rep.update(kind='V13_SELECTIVE_DELIVERY_T9',binding=binding,trace_ids=trace_ids,trace={'train_seconds':train_s if 'train_seconds' not in rep.get('trace',{}) else rep['trace']['train_seconds'],
               'metrics':tr['metrics'],'eval':tr['eval']},
               claim_limit='Linux x86_64 cloud CPU, not Redmi; invented facts and lexical answer keys; one greedy answer per question; trace on 20 facts only; runtime unchanged (frozen), nothing activated')
    save=lambda:atomic_write(target,json.dumps(rep,indent=1,ensure_ascii=False,default=str))
    save()
    for n,arm in enumerate(ARMS):
        res=rep.setdefault(arm,{});mem=tr['artifact'] if arm in ('trace','combined','selective') else None;p=None;log=out/(arm+'.server.log')
        try:
            for k,v in sets().items():
                rows=res.setdefault(k+'_rows',[]);done={r['index'] for r in rows}
                for idx,(q,keys,fact) in enumerate(v):
                    if idx in done:continue
                    if p is None:p=serve(binary,a.gguf,mem,8711+n,log,audit=bool(mem))
                    off=log.stat().st_size if mem else None
                    s,ex=system(q,arm,set(trace_ids));ans,nt,sec=ask(8711+n,s,q)
                    row={'index':idx,'fact':fact,'q':q,'a':ans,'hit':answer_hit(ans,keys),'prompt_tokens':nt,'seconds':round(sec,3),'exact_ids':ex}
                    if off is not None:row['native_firing']=read_firing_window(log,off)
                    rows.append(row);save()
        finally:
            if p is not None:p.terminate();p.wait()
        print(arm,'done',flush=True)
    summarize(rep,trace_ids);save()
    print(json.dumps({arm:{k:rep[arm][k] for k in ('facts','paraphrase','near_miss','probes','prompt_tokens_mean')} for arm in ARMS}))
    print(json.dumps(rep['paired']),json.dumps(rep['decision']))

if __name__=='__main__':main()
