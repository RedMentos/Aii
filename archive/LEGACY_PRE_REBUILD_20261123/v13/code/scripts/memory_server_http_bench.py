"""WP-S3 live path over HTTP: patched llama-server (v13/memory_server.py) with and without V13_MEMORY_FILE.
  python3 scripts/memory_server_http_bench.py SERVER_BIN MODEL.gguf MEMORY.bin OUT.json"""
import json,os,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lora_bench import FACTS,NEAR_MISS,PROBES,PARAPHRASES
from v13.lora_trainer import answer_hit
V,G,MEM,OUT=sys.argv[1:5];LOG=str(Path(OUT).with_suffix(''))
def run(env_mem,port):
    env=dict(os.environ);env.pop('V13_MEMORY_FILE',None)
    if env_mem:env['V13_MEMORY_FILE']=env_mem
    p=subprocess.Popen([V,'-m',G,'--port',str(port),'-ngl','0','-t','4','-c','2048','--parallel','1','--no-webui'],env=env,stdout=subprocess.DEVNULL,stderr=open(LOG+'.srv%d.log'%port,'w'))
    for _ in range(120):
        try:
            if json.loads(urllib.request.urlopen('http://127.0.0.1:%d/health'%port,timeout=2).read()).get('status')=='ok':break
        except Exception:time.sleep(1)
    def ask(q):
        b=json.dumps({'messages':[{'role':'user','content':q}],'max_tokens':40,'temperature':0,'cache_prompt':True}).encode()
        r=json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/v1/chat/completions'%port,b,{'Content-Type':'application/json'}),timeout=300).read())
        return r['choices'][0]['message']['content']
    sets={'facts':[(q,k) for q,_,k in FACTS],'paraphrase':PARAPHRASES,'near_miss':NEAR_MISS,'probes':[(p['prompt'],p['expect']) for p in PROBES]}
    res={}
    try:
        for k,v in sets.items():
            rows=[(q,ask(q)) for q,_ in v];hits=[answer_hit(t,kk) for (q,t),(_,kk) in zip(rows,v)]
            res[k]=sum(hits)/len(hits);res[k+'_rows']=[{'q':q,'a':t[:100]} for q,t in rows]
        # same slot, fact again after unrelated turn (ctx reset across requests)
        res['repeat_fact']=[ask(FACTS[0][0])[:80],ask('Tell me about dogs.')[:40],ask(FACTS[0][0])[:80]]
    finally:p.terminate();p.wait()
    log=open(LOG+'.srv%d.log'%port).read()
    res['log_v13']=[l for l in log.splitlines() if 'v13' in l.lower()][:5]
    return res
out={'without_env':run(None,8591),'with_memory':run(MEM,8592)}
json.dump(out,open(OUT,'w'),indent=1,ensure_ascii=False)
for k,v in out.items():print(k,{a:b for a,b in v.items() if not a.endswith('_rows')})
