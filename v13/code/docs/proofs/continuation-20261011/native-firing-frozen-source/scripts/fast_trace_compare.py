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
import argparse,fcntl,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lora_bench import FACTS,NEAR_MISS,PROBES,PARAPHRASES  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.memory import relevance  # noqa: E402
from v13.memory_trainer import live_system  # noqa: E402
from v13.config import DEFAULTS  # noqa: E402
from v13.common import atomic_write,dumps,digest,file_hash  # noqa: E402
from v13.sparse_audit import read_firing_window  # noqa: E402
from v13.memory_server import runtime_library_hashes  # noqa: E402

def system(question,with_exact):
    if not with_exact:return live_system()
    scored=sorted(((relevance(question,q),q,t) for q,t,_ in FACTS),reverse=True)
    mem=[{'topic':q,'correction':t} for sc,q,t in scored if sc>=DEFAULTS['memory_threshold']][:DEFAULTS['memory_top_k']]
    return live_system(memories=mem)

def serve(binary,model,mem,port,log,*,audit_firing=False):
    env=dict(os.environ);env.pop('V13_MEMORY_FILE',None)
    env.pop('V13_MEMORY_AUDIT',None)
    if mem:env['V13_MEMORY_FILE']=mem
    if mem and audit_firing:env['V13_MEMORY_AUDIT']='1'
    with open(log,'w') as err:
        p=subprocess.Popen([binary,'-m',model,'--port',str(port),'-ngl','0','-t','4','-c','4096','-np','1','-b','128','-ub','128','--no-webui','--no-warmup'],
                           env=env,stdout=subprocess.DEVNULL,stderr=err)
    for _ in range(120):
        if p.poll() is not None:
            p.wait();raise RuntimeError('server exited during startup: '+open(log).read()[-400:])
        try:
            if json.loads(urllib.request.urlopen('http://127.0.0.1:%d/health'%port,timeout=2).read()).get('status')=='ok':return p
        except Exception:time.sleep(1)
    p.terminate()
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    raise RuntimeError('server did not start: '+open(log).read()[-400:])

def ask(port,sys_text,q):
    b=json.dumps({'messages':[{'role':'system','content':sys_text},{'role':'user','content':q}],'max_tokens':40,'temperature':0,'seed':13,'cache_prompt':True}).encode()
    t=time.monotonic();r=json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/v1/chat/completions'%port,b,{'Content-Type':'application/json'}),timeout=300).read())
    return r['choices'][0]['message']['content'],r['usage']['prompt_tokens'],time.monotonic()-t

def compare(binary,model,mem,out,*,resume=False,repeats=1,audit_firing=False):
    target=Path(out);target.parent.mkdir(parents=True,exist_ok=True)
    with open(str(target)+'.lock','a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('This proof is already running; no concurrent resume')
        return _compare(binary,model,mem,out,resume=resume,repeats=repeats,audit_firing=audit_firing)

def _compare(binary,model,mem,out,*,resume=False,repeats=1,audit_firing=False):
    """Checkpoint every real answer; resume only the identical corpus/runner/artifact.

    Rows are raw native observations, not automatic approval of memory delivery.
    A failed attempt is retained and retried only on an explicit --resume invocation.
    Historical comparison files are never consumed or overwritten implicitly.
    """
    if repeats<1:raise ValueError('repeats must be positive')
    sets={'facts':[(q,k) for q,_,k in FACTS],'paraphrase':PARAPHRASES,'near_miss':NEAR_MISS,'probes':[(p['prompt'],p['expect']) for p in PROBES]}
    binding={'binary_sha256':file_hash(binary),'runtime_libraries_sha256':runtime_library_hashes(binary),
             'model_sha256':file_hash(model),'memory_sha256':file_hash(mem),
             'corpus_sha256':digest(dumps({'facts':FACTS,'sets':sets})),
             'script_sha256':file_hash(__file__),'relevance_sha256':file_hash(Path(__file__).parents[1]/'v13/memory.py'),
             'prompts_sha256':digest(live_system()),'memory_threshold':DEFAULTS['memory_threshold'],
             'memory_top_k':DEFAULTS['memory_top_k'],'repeats':repeats,'temperature':0,'cache_prompt':True,'max_tokens':40,'seed':13,
             'audit_firing':audit_firing,'audit_parser_sha256':file_hash(Path(__file__).parents[1]/'v13/sparse_audit.py')}
    target=Path(out)
    if target.exists() and not resume:raise ValueError('Output exists; choose a new file or explicit --resume')
    rep=json.loads(target.read_text()) if resume and target.exists() else {}
    if rep and rep.get('_checkpoint',{}).get('binding')!=binding:raise ValueError('Resume binding differs; retain this proof and use a new output')
    cp=rep.setdefault('_checkpoint',{'schema':'v13-fast-trace-checkpoint-v1','binding':binding,'attempts':[]})
    for previous in cp['attempts']:
        if previous['status']=='RUNNING':previous.update(status='INTERRUPTED',identified_on_resume=True)
    attempt={'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'RUNNING'}
    cp['attempts'].append(attempt);cp['status']='RUNNING'
    def save():atomic_write(target,json.dumps(rep,indent=1,ensure_ascii=False,allow_nan=False))
    save()
    for name,use_mem,exact,port in (('base',None,False,8611),('exact',None,True,8612),('trace',mem,False,8613),('exact+trace',mem,True,8614)):
        res=rep.setdefault(name,{});p=None
        try:
            for k,v in sets.items():
                rows=res.setdefault(k+'_rows',[])
                completed={(r['repeat'],r['index']) for r in rows}
                for repeat in range(repeats):
                    for index,(q,keys) in enumerate(v):
                        if (repeat,index) in completed:continue
                        log=str(out)+'.'+name+'.attempt%d.log'%len(cp['attempts'])
                        if p is None:p=serve(binary,model,use_mem,port,log,audit_firing=audit_firing)
                        offset=Path(log).stat().st_size if audit_firing and use_mem else None
                        a,n,s=ask(port,system(q,exact),q)
                        row={'repeat':repeat,'index':index,'q':q,'a':a,'hit':answer_hit(a,keys),
                             'prompt_tokens':n,'seconds':s,'attempt':len(cp['attempts'])}
                        if offset is not None:row['native_firing']=read_firing_window(log,offset)
                        rows.append(row)
                        save()  # durable before another native call or app/session interruption
                res[k]=sum(r['hit'] for r in rows)/len(rows)
            all_rows=[r for k in sets for r in res[k+'_rows']]
            res['prompt_tokens_mean']=sum(r['prompt_tokens'] for r in all_rows)/len(all_rows)
            res['seconds_mean']=round(sum(r['seconds'] for r in all_rows)/len(all_rows),3)
            res['status']='COMPLETE';save()
        except BaseException as exc:
            attempt.update(status='ERROR',arm=name,error=type(exc).__name__,detail=str(exc)[:600]);cp['status']='INCOMPLETE';save();raise
        finally:
            if p is not None:p.terminate();p.wait()
        print(name,{k:v for k,v in res.items() if not k.endswith('_rows')},flush=True)
    b=rep['base']
    for name in ('exact','trace','exact+trace'):
        cand={(r['repeat'],r['index']):r for r in rep[name]['probes_rows']}
        rep[name]['forgotten']=[{'q':r['q'],'repeat':r['repeat']} for r in b['probes_rows'] if r['hit'] and not cand[(r['repeat'],r['index'])]['hit']]
    attempt['status']='COMPLETE';cp['status']='COMPLETE';save();return rep

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('binary');ap.add_argument('model');ap.add_argument('memory');ap.add_argument('out')
    ap.add_argument('--resume',action='store_true');ap.add_argument('--repeats',type=int,default=1)
    ap.add_argument('--audit-firing',action='store_true',help='Opt-in native slot write diagnostics; requires rebuilt memory server; never authorizes Exact omission')
    a=ap.parse_args();compare(a.binary,a.model,a.memory,a.out,resume=a.resume,repeats=a.repeats,audit_firing=a.audit_firing);print(a.out)

if __name__=='__main__':main()
