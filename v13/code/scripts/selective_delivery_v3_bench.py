#!/usr/bin/env python3
"""WP-T9 v3: key separation for the fast trace, measured by native slot firing (paired frozen corpus, native C3).

Per-slot analysis of the v1 audit records (bench-results/selective-delivery-20261012) showed two causes of foreign firing:
  (1) shared frame words: the guard of 'What is my favourite dish?' is {favourite, dish}, so 'favourite' opens it on
      'favourite colour/flower/cheese'; same for 'play', 'best', 'live';
  (2) guard context = the whole prompt: an exact block in the system message that names another fact opens that fact's
      slot (combined arm: 121 foreign firings vs 31 in trace alone; 'tortoise' fires on every 'name of my ...' question).
Fix candidate (v13/sparse_memory, default off): guard_distinct (guard words with document frequency 1 over the store's fact
questions, guard_vocab = the 40 exact-store questions) + guard_scope='last_user' (guard sees only the last user turn and the
assistant header; native V13SMEM1 header field 6 = 2 + chat marker token).

Arms (one patched llama-server-mem binary, same C3 GGUF, same live system message as runtime._turn):
  base, exact                    as v1
  trace_v1, selective_v1         v1 trace recipe (old guard), retrained here so both traces share binary and run
  trace, combined, selective     fixed trace (same 20 facts, same training recipe otherwise)
Native firing (V13_MEMORY_AUDIT) is recorded for every trace answer and mapped to memory ids via the .bin row map.
  python3 scripts/selective_delivery_v3_bench.py --home HOME --master DIR --gguf C3.gguf --out DIR [--resume]
Preregistration: code/docs/proofs/selective-delivery-v3-20261021/preregistration.json (decision rule there)."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import selective_delivery_bench as V1  # noqa: E402
from selective_delivery_corpus import FACTS,split  # noqa: E402
from lora_bench import ANCHORS,PROBES  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.memory_trainer import live_system,SparseMemoryAG6Trainer  # noqa: E402
from v13.config import DEFAULTS  # noqa: E402
from v13.common import atomic_write,dumps,digest,file_hash  # noqa: E402
from v13.sparse_audit import read_firing_window  # noqa: E402
from v13.memory_server import runtime_library_hashes  # noqa: E402

ARMS={'base':(None,'base'),'exact':(None,'exact'),'trace_v1':('v1','trace'),'selective_v1':('v1','selective'),
      'trace':('fix','trace'),'combined':('fix','combined'),'selective':('fix','selective')}
FIX={'guard_distinct':True,'guard_vocab':[f[0] for f in FACTS],'guard_scope':'last_user'}

def train(master,gguf,out,trace_ids,variant):
    d=out/('trace-'+variant);meta=d/'trace.json'
    if meta.is_file():
        r=json.loads(meta.read_text())
        if Path(r['artifact']).is_file() and file_hash(r['artifact'])==r['hash']:return r
    items=[{'memory_id':'sel_%d'%i,'prompt':FACTS[i][0],'target':FACTS[i][1],'answer_keys':FACTS[i][2]} for i in trace_ids]
    cfg={'threads':4,'base_gguf':str(gguf),'entity_guard':True,'system':live_system(),'contexts':[''],'max_tokens':256}
    if variant=='fix':cfg.update(FIX)
    t0=time.monotonic();tr=SparseMemoryAG6Trainer(master,d/'work',background=ANCHORS,probes=PROBES,cfg=cfg);r=tr.fit(items,'selective-delivery-v3-'+variant)
    if not r.get('artifact'):raise RuntimeError('trace training produced no artifact: '+json.dumps(r.get('metrics'),default=str)[:400])
    r={'artifact':r['artifact'],'hash':r['hash'],'train_seconds':round(time.monotonic()-t0,1),
       'metrics':{k:v for k,v in r['metrics'].items() if k not in ('history','top_scores')},'eval':r['eval']}
    d.mkdir(parents=True,exist_ok=True);atomic_write(meta,json.dumps(r,indent=1,default=str));return r

def fired_ids(row,slot_rows):
    f=row.get('native_firing') or {}
    if f.get('status')!='OBSERVED_NATIVE_WRITES':return None
    return sorted({int(str(slot_rows[i]).split('_')[1]) for i in f.get('fired_rows',[]) if slot_rows[i] is not None})

def firing(res,slot_rows,trace_ids):
    """Rows with >=1 foreign memory fired (any fired memory that is not the row's own fact; near-miss/probe rows: any),
    own firing on the trace facts per set, unobserved rows. The own fact of a near-miss question is someone else's."""
    T=set(trace_ids);out={'foreign_rows':0,'foreign_firings':0,'unobserved':0,'rows':0,'per_set':{}}
    for k in ('facts','paraphrase','near_miss','probes'):
        s={'rows':0,'foreign_rows':0,'own_fired_trace':0,'trace_rows':0}
        for x in res[k+'_rows']:
            ids=fired_ids(x,slot_rows);s['rows']+=1
            if ids is None:out['unobserved']+=1;continue
            own=x['fact'] if k in ('facts','paraphrase') else None
            foreign=[i for i in ids if i!=own];out['foreign_firings']+=len(foreign);s['foreign_rows']+=bool(foreign)
            if own is not None and own in T:s['trace_rows']+=1;s['own_fired_trace']+=own in ids
        out['per_set'][k]=s;out['rows']+=s['rows'];out['foreign_rows']+=s['foreign_rows']
    return out

def decide(rep):
    f1,f=rep['trace_v1']['firing'],rep['trace']['firing'];own=f['per_set']['facts']['own_fired_trace']
    h1={'foreign_rows_trace_lower_than_trace_v1':f['foreign_rows']<f1['foreign_rows'],'own_firing_trace_facts_at_least_18_of_20':own>=18,
        'no_unobserved_rows':f['unobserved']==0 and f1['unobserved']==0}
    s,e=rep['selective'],rep['exact'];p=V1.paired(rep,'selective','exact',('facts','paraphrase'))
    h2={'recall_not_worse_than_exact':p['losses']<=p['wins'],'leak_not_higher_than_exact':s['near_miss']<=e['near_miss'],
        'fewer_prompt_tokens_than_exact':s['prompt_tokens_mean']<e['prompt_tokens_mean'],'no_probe_forgotten_beyond_exact':len(s['forgotten_probes'])<=len(e['forgotten_probes'])}
    rep['paired']={'selective_vs_exact':p,'selective_v1_vs_exact':V1.paired(rep,'selective_v1','exact',('facts','paraphrase')),
                   'selective_vs_selective_v1':V1.paired(rep,'selective','selective_v1',('facts','paraphrase')),
                   'combined_vs_exact':V1.paired(rep,'combined','exact',('facts','paraphrase')),'trace_vs_trace_v1':V1.paired(rep,'trace','trace_v1',('facts','paraphrase'))}
    rep['decision']={'h1_key_separation':{'criteria':h1,'verdict':'KEY_SEPARATION_SUPPORTED' if all(h1.values()) else 'KEY_SEPARATION_NOT_SUPPORTED'},
                     'h2_selective_utility':{'criteria':h2,'verdict':'SELECTIVE_WINS_CANDIDATE' if all(h2.values()) else 'SELECTIVE_DOES_NOT_WIN'},
                     'consequence':'nothing activated; a WIN only allows a separately preregistered runtime/AG6 change'}

def summarize(rep,trace_ids,slot_rows):
    T=set(trace_ids)
    for arm,(variant,_) in ARMS.items():
        r=rep[arm];rows=[x for k in V1.sets() for x in r[k+'_rows']]
        for k in V1.sets():
            rr=r[k+'_rows'];r[k]=round(sum(x['hit'] for x in rr)/len(rr),4)
            if k!='probes':r[k+'_in_trace']=round(sum(x['hit'] for x in rr if x['fact'] in T)/len(T),4)
        r['prompt_tokens_mean']=round(sum(x['prompt_tokens'] for x in rows)/len(rows),2)
        r['exact_blocks_mean']=round(sum(len(x['exact_ids']) for x in rows)/len(rows),3)
        base={x['index']:x['hit'] for x in rep['base']['probes_rows']}
        r['forgotten_probes']=[x['q'] for x in r['probes_rows'] if base[x['index']] and not x['hit']]
        if variant:r['firing']=firing(r,slot_rows[variant],trace_ids)
    decide(rep)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--home',required=True);ap.add_argument('--master',required=True);ap.add_argument('--gguf',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    home,out=Path(a.home),Path(a.out);out.mkdir(parents=True,exist_ok=True);binary=home/'bin/llama-server-mem'
    trace_ids,_=split();traces={v:train(a.master,a.gguf,out,trace_ids,v) for v in ('v1','fix')}
    slot_rows={v:json.loads(Path(t['artifact']+'.items.json').read_text())['rows'] for v,t in traces.items()}
    binding={'binary_sha256':file_hash(binary),'runtime_libraries_sha256':runtime_library_hashes(binary),'model_sha256':file_hash(a.gguf),
             'master_sha256':file_hash(Path(a.master)/'model.safetensors'),'trace_sha256':{v:t['hash'] for v,t in traces.items()},
             'corpus_sha256':digest(dumps({'facts':FACTS,'probes':PROBES,'anchors':ANCHORS,'trace_ids':trace_ids})),
             'script_sha256':file_hash(__file__),'v1_script_sha256':file_hash(V1.__file__),'sparse_memory_sha256':file_hash(Path(__file__).parents[1]/'v13/sparse_memory.py'),
             'hook_header_sha256':file_hash(Path(__file__).parent/'v13_memory_hook.h'),'prompts_sha256':digest(live_system()),'fix_cfg':FIX,
             'memory_threshold':DEFAULTS['memory_threshold'],'memory_top_k':DEFAULTS['memory_top_k'],'temperature':0,'max_tokens':40,'seed':13,'cache_prompt':True}
    target=out/'report.json'
    if target.exists() and not a.resume:raise SystemExit('report exists; use --resume')
    rep=json.loads(target.read_text()) if target.exists() else {}
    if rep and rep.get('binding')!=binding:raise SystemExit('binding differs; keep this proof and use a new --out')
    rep.update(kind='V13_SELECTIVE_DELIVERY_T9_V3_KEY_SEPARATION',binding=binding,trace_ids=trace_ids,
               traces={v:{k:t[k] for k in ('train_seconds','metrics','eval')} for v,t in traces.items()},
               claim_limit='Linux x86_64 cloud CPU, not Redmi; invented facts and lexical answer keys; one greedy answer per question; trace on 20 facts only; guard_vocab = the 40 corpus questions (the exact store); runtime unchanged, nothing activated')
    save=lambda:atomic_write(target,json.dumps(rep,indent=1,ensure_ascii=False,default=str))
    save()
    for n,(arm,(variant,mode)) in enumerate(ARMS.items()):
        res=rep.setdefault(arm,{});mem=traces[variant]['artifact'] if variant else None;p=None;log=out/(arm+'.server.log')
        try:
            for k,v in V1.sets().items():
                rows=res.setdefault(k+'_rows',[]);done={r['index'] for r in rows}
                for idx,(q,keys,fact) in enumerate(v):
                    if idx in done:continue
                    if p is None:p=V1.serve(binary,a.gguf,mem,8731+n,log,audit=bool(mem))
                    off=log.stat().st_size if mem else None
                    s,ex=V1.system(q,mode,set(trace_ids));ans,nt,sec=V1.ask(8731+n,s,q)
                    row={'index':idx,'fact':fact,'q':q,'a':ans,'hit':answer_hit(ans,keys),'prompt_tokens':nt,'seconds':round(sec,3),'exact_ids':ex}
                    if off is not None:
                        row['native_firing']=read_firing_window(log,off);row['fired_memories']=fired_ids(row,slot_rows[variant])
                    rows.append(row);save()
        finally:
            if p is not None:p.terminate();p.wait()
        print(arm,'done',flush=True)
    summarize(rep,trace_ids,slot_rows);save()
    print(json.dumps({arm:{k:rep[arm][k] for k in ('facts','paraphrase','near_miss','probes','prompt_tokens_mean')}|({'foreign_rows':rep[arm]['firing']['foreign_rows']} if 'firing' in rep[arm] else {}) for arm in ARMS}))
    print(json.dumps(rep['paired']),json.dumps(rep['decision']))

if __name__=='__main__':main()
