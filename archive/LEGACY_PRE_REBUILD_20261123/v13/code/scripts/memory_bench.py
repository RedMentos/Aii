#!/usr/bin/env python3
"""WP-S3 end to end: AG6 sparse-memory trainer (keyed + entity guard, keys written on the dequantized Q4 weights) and the
same memory served natively by llama.cpp (scripts/native_memory_hook.cpp) on the quantized C3 GGUF.
  python3 scripts/memory_bench.py --master DIR --gguf C3.gguf --hook BIN --out DIR
Facts/probes/paraphrases/near-miss: scripts/lora_bench.py. Nothing is activated.
"""
import argparse,json,subprocess,sys,time,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from lora_bench import FACTS,PARAPHRASES,NEAR_MISS,ANCHORS,PROBES  # noqa: E402
from v13.memory_trainer import SparseMemoryAG6Trainer  # noqa: E402
from v13.sparse_memory import export_native  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402

def native(hook,gguf,mem,prompts,tok,threads,sysp=None):
    pf=Path(mem).with_suffix('.prompts.jsonl')
    pf.write_text(''.join(json.dumps(tok.apply_chat_template(([{'role':'system','content':sysp}] if sysp else [])+[{'role':'user','content':p}],add_generation_prompt=True,tokenize=False))+'\n' for p in prompts))
    t=time.monotonic();out=subprocess.run([hook,gguf,mem,str(pf),str(threads),'40'],capture_output=True,text=True,errors='replace',timeout=1800)
    rows=[json.loads(l) for l in out.stdout.splitlines() if l.startswith('{')]
    if len(rows)!=len(prompts):raise RuntimeError('native hook: '+out.stderr[-500:])
    return rows,round(time.monotonic()-t,1)

def score(rows,prompts_keys):
    return [answer_hit(r['text'],k) for r,(_,k) in zip(rows,prompts_keys)]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--master',required=True);ap.add_argument('--gguf',required=True);ap.add_argument('--hook',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--threads',type=int,default=4);ap.add_argument('--no-guard',action='store_true')
    ap.add_argument('--system',action='store_true',help='write keys and measure in the runtime chat context (v13/prompts.py system prompt)');a=ap.parse_args()
    sysp=None
    if a.system:
        from v13.memory_trainer import live_system;sysp=live_system()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    items=[{'memory_id':'bench_%d'%k,'prompt':q,'target':t,'answer_keys':keys} for k,(q,t,keys) in enumerate(FACTS)]
    if (out/'torch.json').is_file() and Path(json.loads((out/'torch.json').read_text())['artifact']).is_file():r=json.loads((out/'torch.json').read_text())
    else:
      tr=SparseMemoryAG6Trainer(a.master,out/'work',background=ANCHORS,probes=PROBES,cfg=dict({'threads':a.threads,'base_gguf':a.gguf,'entity_guard':not a.no_guard},**({'system':sysp,'contexts':[''],'max_tokens':256} if sysp else {})))
      r=tr.fit(items,'bench');(out/'torch.json').write_text(json.dumps(r,default=str))
    rep={'torch':{'metrics':{k:v for k,v in r['metrics'].items() if k not in ('history','top_scores')},'eval':r['eval']}}
    print(json.dumps({'torch_eval':r['eval'],'kl':r['metrics']['kl_to_base']}),flush=True)
    mem=out/'memory.bin'
    if str(r['artifact']).endswith('.bin'):  # the AG6 trainer already binds the native file
        import shutil;shutil.copyfile(r['artifact'],mem);rep['export']=r['metrics'].get('native')
    else:rep['export']=export_native(r['artifact'],mem)
    empty=out/'empty.bin'
    with open(mem,'rb') as f:head=f.read(8+24+8)
    lay,hid,n,ew,topk,g=struct.unpack('<6i',head[8:32]);
    with open(empty,'wb') as f:f.write(b'V13SMEM1'+struct.pack('<6i',lay,hid,0,ew,topk,g)+head[32:40]+b'\0'*4*hid)
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(a.master)
    sets={'facts':[(q,k) for q,_,k in FACTS],'paraphrase':PARAPHRASES,'near_miss':NEAR_MISS,'probes':[(p['prompt'],p['expect']) for p in PROBES]}
    allp=[q for v in sets.values() for q,_ in v]
    for name,m in (('native_base',empty),('native_memory',mem)):
        rows,secs=native(a.hook,a.gguf,str(m),allp,tok,a.threads,sysp);i=0;res={'seconds':secs}
        for k,v in sets.items():
            hits=score(rows[i:i+len(v)],v);res[k]=sum(hits)/len(hits);res[k+'_rows']=[{'prompt':r['prompt'][-80:],'text':r['text'][:120],'fired':r['memory_fired']} for r in rows[i:i+len(v)]];i+=len(v)
        rep[name]=res;print(json.dumps({name:{k:v for k,v in res.items() if not k.endswith('_rows')}}),flush=True)
    b=rep['native_base']['probes_rows'];c=rep['native_memory']['probes_rows'];bo=[score([x],[sets['probes'][j]])[0] for j,x in enumerate(b)];co=[score([x],[sets['probes'][j]])[0] for j,x in enumerate(c)]
    rep['native_forgotten']=[sets['probes'][j][0] for j in range(len(bo)) if bo[j] and not co[j]]
    (out/'memory_bench.json').write_text(json.dumps(rep,indent=1,ensure_ascii=False));print(out/'memory_bench.json')

if __name__=='__main__':main()
