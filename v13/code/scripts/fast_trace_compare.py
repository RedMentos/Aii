#!/usr/bin/env python3
"""Blueprint §9.1 'Parametric Fast Trace' comparison on the deployed C3 through llama-server (HTTP chat API):
  base                no memory
  exact               exact episodic retrieval only: lexically recalled corrections in the system prompt (as runtime.py)
  trace               tiny parametric fast trace only (keyed sparse memory via llama-server-mem, V13_MEMORY_FILE)
  exact+trace         both
Same system message as runtime._turn in a fresh chat (memory_trainer.live_system). Recall: memory.relevance >= memory_threshold, top memory_top_k.
Measures fact recall, paraphrase recall, near-miss leak, retention probes, prompt tokens and latency per turn.
  python3 scripts/fast_trace_compare.py SERVER_BIN MODEL.gguf MEMORY.bin OUT.json
"""
import json,os,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lora_bench import FACTS,NEAR_MISS,PROBES,PARAPHRASES  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.memory import relevance  # noqa: E402
from v13.memory_trainer import live_system  # noqa: E402
from v13.config import DEFAULTS  # noqa: E402

def system(question,with_exact):
    if not with_exact:return live_system()
    scored=sorted(((relevance(question,q),q,t) for q,t,_ in FACTS),reverse=True)
    mem=[{'topic':q,'correction':t} for sc,q,t in scored if sc>=DEFAULTS['memory_threshold']][:DEFAULTS['memory_top_k']]
    return live_system(memories=mem)

def serve(binary,model,mem,port,log):
    env=dict(os.environ);env.pop('V13_MEMORY_FILE',None)
    if mem:env['V13_MEMORY_FILE']=mem
    p=subprocess.Popen([binary,'-m',model,'--port',str(port),'-ngl','0','-t','4','-c','4096','-np','1','-b','128','-ub','128','--no-webui','--no-warmup'],
                       env=env,stdout=subprocess.DEVNULL,stderr=open(log,'w'))
    for _ in range(120):
        try:
            if json.loads(urllib.request.urlopen('http://127.0.0.1:%d/health'%port,timeout=2).read()).get('status')=='ok':return p
        except Exception:time.sleep(1)
    p.terminate();raise RuntimeError('server did not start: '+open(log).read()[-400:])

def ask(port,sys_text,q):
    b=json.dumps({'messages':[{'role':'system','content':sys_text},{'role':'user','content':q}],'max_tokens':40,'temperature':0,'cache_prompt':True}).encode()
    t=time.monotonic();r=json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/v1/chat/completions'%port,b,{'Content-Type':'application/json'}),timeout=300).read())
    return r['choices'][0]['message']['content'],r['usage']['prompt_tokens'],time.monotonic()-t

def main():
    binary,model,mem,out=sys.argv[1:5]
    sets={'facts':[(q,k) for q,_,k in FACTS],'paraphrase':PARAPHRASES,'near_miss':NEAR_MISS,'probes':[(p['prompt'],p['expect']) for p in PROBES]}
    rep={}
    for name,use_mem,exact,port in (('base',None,False,8611),('exact',None,True,8612),('trace',mem,False,8613),('exact+trace',mem,True,8614)):
        p=serve(binary,model,use_mem,port,out+'.'+name+'.log');res={}
        try:
            toks=[];secs=[]
            for k,v in sets.items():
                rows=[]
                for q,keys in v:
                    a,n,s=ask(port,system(q,exact),q);rows.append({'q':q,'a':a[:100],'hit':answer_hit(a,keys)});toks.append(n);secs.append(s)
                res[k]=sum(r['hit'] for r in rows)/len(rows);res[k+'_rows']=rows
            res['prompt_tokens_mean']=sum(toks)/len(toks);res['seconds_mean']=round(sum(secs)/len(secs),3)
        finally:p.terminate();p.wait()
        rep[name]=res;print(name,{k:v for k,v in res.items() if not k.endswith('_rows')},flush=True)
    b=rep['base']
    for name in ('exact','trace','exact+trace'):
        rep[name]['forgotten']=[r['q'] for r,c in zip(b['probes_rows'],rep[name]['probes_rows']) if r['hit'] and not c['hit']]
    Path(out).write_text(json.dumps(rep,indent=1,ensure_ascii=False));print(out)

if __name__=='__main__':main()
