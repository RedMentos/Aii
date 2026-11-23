#!/usr/bin/env python3
"""WP-T9 selective delivery v2: drop the exact block only for trace facts whose trace answer was verified natively.

Follow-up to bench-results/selective-delivery-20261012 (SELECTIVE_DOES_NOT_WIN). Part of those losses came from trace facts whose
trace value was wrong where the exact block was right. v2 adds a verification pass before measuring: each of the 20 trace facts is
asked once with its own stored question, trace only (live system message, no exact block); a fact is VERIFIED if the answer hits its
keys. Then three arms are measured on the same frozen corpus and the same bound trace artifact (sha256 checked):
  exact               exact block from the full store (control, re-measured)
  selective           v1 rule: exact block omitted for every recalled trace fact (re-measured for paired comparison)
  selective_verified  exact block omitted only for recalled VERIFIED trace facts
Unseen checks are paraphrases and near-miss questions (the verification only used the stored fact question). Same decision rule as v1,
applied to selective_verified vs exact. Runtime unchanged (frozen); nothing activated.
  python3 scripts/selective_delivery_v2_bench.py --home HOME --gguf C3.gguf --trace-dir V1_OUT --out DIR"""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import selective_delivery_bench as V1  # noqa: E402
from selective_delivery_corpus import FACTS,split  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.memory_trainer import live_system  # noqa: E402
from v13.common import atomic_write,dumps,digest,file_hash  # noqa: E402
from v13.sparse_audit import read_firing_window  # noqa: E402
from v13.memory_server import runtime_library_hashes  # noqa: E402

ARMS=('exact','selective','selective_verified')

def system(question,arm,trace_ids,verified):
    if arm=='selective_verified':
        rec=[i for i in V1.recalled(question,range(len(FACTS))) if i not in verified]
        mem=[{'topic':FACTS[i][0],'correction':FACTS[i][1]} for i in rec]
        return (live_system(memories=mem) if mem else live_system()),rec
    return V1.system(question,arm,trace_ids)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--home',required=True);ap.add_argument('--gguf',required=True)
    ap.add_argument('--trace-dir',required=True);ap.add_argument('--out',required=True);ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    home,out=Path(a.home),Path(a.out);out.mkdir(parents=True,exist_ok=True);binary=home/'bin/llama-server-mem'
    tr=json.loads((Path(a.trace_dir)/'trace.json').read_text())
    if file_hash(tr['artifact'])!=tr['hash']:raise SystemExit('trace artifact hash mismatch')
    trace_ids,_=split()
    binding={'binary_sha256':file_hash(binary),'runtime_libraries_sha256':runtime_library_hashes(binary),'model_sha256':file_hash(a.gguf),
             'trace_sha256':tr['hash'],'corpus_file_sha256':file_hash(Path(__file__).parent/'selective_delivery_corpus.py'),
             'script_sha256':file_hash(__file__),'v1_script_sha256':file_hash(V1.__file__),'prompts_sha256':digest(live_system()),'trace_ids':trace_ids}
    target=out/'report.json'
    if target.exists() and not a.resume:raise SystemExit('report exists; use --resume')
    rep=json.loads(target.read_text()) if target.exists() else {}
    if rep and rep.get('binding')!=binding:raise SystemExit('binding differs')
    rep.update(kind='V13_SELECTIVE_DELIVERY_T9_V2',binding=binding,
               claim_limit='Linux x86_64 cloud CPU, not Redmi; invented facts; one greedy answer per question; same trace as v1; verification used the stored fact questions, so the facts set is not unseen for selective_verified; runtime unchanged')
    save=lambda:atomic_write(target,json.dumps(rep,indent=1,ensure_ascii=False,default=str))
    save();port=8790
    if 'verification' not in rep:
        log=out/'verify.server.log';p=V1.serve(binary,a.gguf,tr['artifact'],port,log,audit=False);rows=[]
        try:
            for i in trace_ids:
                ans,_,_=V1.ask(port,live_system(),FACTS[i][0]);rows.append({'fact':i,'a':ans,'hit':answer_hit(ans,FACTS[i][2])})
        finally:p.terminate();p.wait()
        rep['verification']={'rows':rows,'verified':[r['fact'] for r in rows if r['hit']]};save()
    verified=set(rep['verification']['verified'])
    for n,arm in enumerate(ARMS):
        res=rep.setdefault(arm,{});mem=tr['artifact'] if arm!='exact' else None;p=None;log=out/(arm+'.server.log')
        try:
            for k,v in V1.sets().items():
                rows=res.setdefault(k+'_rows',[]);done={r['index'] for r in rows}
                for idx,(q,keys,fact) in enumerate(v):
                    if idx in done:continue
                    if p is None:p=V1.serve(binary,a.gguf,mem,port+1+n,log,audit=bool(mem))
                    off=log.stat().st_size if mem else None
                    s,ex=system(q,arm,set(trace_ids),verified);ans,nt,sec=V1.ask(port+1+n,s,q)
                    row={'index':idx,'fact':fact,'q':q,'a':ans,'hit':answer_hit(ans,keys),'prompt_tokens':nt,'seconds':round(sec,3),'exact_ids':ex}
                    if off is not None:row['native_firing']=read_firing_window(log,off)
                    rows.append(row);save()
        finally:
            if p is not None:p.terminate();p.wait()
        print(arm,'done',flush=True)
    # reuse v1 summaries: base forgotten-probe reference comes from the v1 report's base arm (same binary/model/prompts)
    v1=json.loads((Path(a.trace_dir)/'report.json').read_text())
    rep['base']=v1['base'];rep['base_source']='v1 report (same binary, model, prompts)'
    T=set(trace_ids)
    for arm in ARMS+('base',):
        r=rep[arm];rows=[x for k in V1.sets() for x in r[k+'_rows']]
        for k in V1.sets():
            rr=r[k+'_rows'];r[k]=round(sum(x['hit'] for x in rr)/len(rr),4)
        r['prompt_tokens_mean']=round(sum(x['prompt_tokens'] for x in rows)/len(rows),2)
        base={x['index']:x['hit'] for x in rep['base']['probes_rows']}
        r['forgotten_probes']=[x['q'] for x in r['probes_rows'] if base[x['index']] and not x['hit']]
    recall=('facts','paraphrase')
    rep['paired']={'selective_verified_vs_exact':V1.paired(rep,'selective_verified','exact',recall),'selective_verified_vs_exact_paraphrase_only':V1.paired(rep,'selective_verified','exact',('paraphrase',)),
                   'selective_vs_exact':V1.paired(rep,'selective','exact',recall),'selective_verified_vs_selective':V1.paired(rep,'selective_verified','selective',recall)}
    s,e=rep['selective_verified'],rep['exact'];p=rep['paired']['selective_verified_vs_exact']
    crit={'recall_not_worse_than_exact':p['losses']<=p['wins'],'leak_not_higher_than_exact':s['near_miss']<=e['near_miss'],
          'fewer_prompt_tokens_than_exact':s['prompt_tokens_mean']<e['prompt_tokens_mean'],'no_probe_forgotten_beyond_exact':len(s['forgotten_probes'])<=len(e['forgotten_probes'])}
    rep['decision']={'criteria':crit,'verdict':'SELECTIVE_VERIFIED_WINS_CANDIDATE' if all(crit.values()) else 'SELECTIVE_VERIFIED_DOES_NOT_WIN',
                     'consequence':'candidate for a separately preregistered runtime change after the freeze; nothing activated' if all(crit.values()) else 'keep exact delivery'}
    save()
    print(json.dumps({arm:{k:rep[arm][k] for k in ('facts','paraphrase','near_miss','probes','prompt_tokens_mean')} for arm in ARMS}))
    print(json.dumps(rep['verification']['verified']),json.dumps(rep['paired']),json.dumps(rep['decision']))

if __name__=='__main__':main()
