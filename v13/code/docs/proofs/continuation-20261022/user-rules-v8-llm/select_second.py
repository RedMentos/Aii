#!/usr/bin/env python3
"""WP-UR8 judge selection on KNOWN German sentences only (PREREG.md): run each candidate model x prompt once over the
selection set (temperature 0, grammar JSON), cache the verdicts, and score fixed reader v8 alone vs fixed v8 + second reader
with the unchanged probes of rounds 1-7 (userrules_eval.py). The rule picks the winner; nothing is tuned afterwards.
Usage: select_second.py <llama-server> <models-dir> [run|score]"""
import hashlib,json,subprocess,sys,time,types,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];P=HERE.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(P.parent/'continuation-20261021/user-rules'));sys.path.insert(0,str(P/'user-rules-v3'))
import userrules_eval as E
sys.path.insert(0,str(HERE));import snapshot
U,S=snapshot.load()
from generate_round3 import sha,port
SETS=[P/'user-rules-v5/holdout_de2.json',P/'user-rules-v6/holdout_de3.json',P/'user-rules-v7/holdout_de4.json',P/'user-rules-v5/cohort_round5.json',
      P/'user-rules-v6/cohort_round6.json',P/'user-rules-v7/cohort_round7.json',P/'user-rules-v7/dev_v7.json']
CANDS={'QWEN25_1B5':'judge-qwen25-1.5b.gguf','GEMMA3_1B':'judge-gemma3-1b.gguf','QWEN25_3B':'judge-qwen25-3b.gguf'}
CACHE=HERE/'select_cache.json'

def items():
    out=[]
    for f in SETS:out+=[dict(it,set=f.parent.name+'/'+f.name) for it in json.loads(f.read_text())['items']]
    return out

def run(server,mdir):
    cache=json.loads(CACHE.read_text()) if CACHE.exists() else {}
    texts=sorted({it['text'] for it in items()})
    for name,fn in CANDS.items():
        p=port();proc=subprocess.Popen([server,'-m',str(Path(mdir)/fn),'--port',str(p),'-c','2048','-t','2','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(600):
                try:
                    if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).read()).get('status')=='ok':break
                except Exception:pass
                time.sleep(1)
            for pr in S.PROMPTS:
                key=name+'/'+pr;c=cache.setdefault(key,{'sha256':sha(Path(mdir)/fn),'v':{}})
                for t in texts:
                    if t not in c['v']:c['v'][t]=S.ask_llama(f'http://127.0.0.1:{p}',pr,t)
                CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=0)+'\n');print(key,'done',flush=True)
        finally:proc.terminate();proc.wait()

def shim(verdicts):
    m=types.ModuleType('u_plus');m.__dict__.update(U.__dict__);m.parse=lambda text:S.combine(U.parse(text),verdicts.get(text),text);return m

def summary(its,mod):
    E.U=mod;tot,rows=E.score(its);none=[r for r in rows if r['want_kind']=='NONE']
    return {'failure_sentences':sum(1 for r in rows if r['safety_failures']),'safety_failures':tot['safety_failures'],
            'none_fired_share':round(sum(r['got_kind']!='NONE' for r in none)/max(len(none),1),3),'over_caution':tot['over_caution']},rows

def score():
    cache=json.loads(CACHE.read_text());its=items();base,_=summary(its,U);res={'fixed_v8':base,'candidates':{}}
    for key,c in cache.items():
        s,_=summary(its,shim(c['v']));s['invalid_share']=round(sum(v is None for v in c['v'].values())/max(len(c['v']),1),3);s['sha256']=c['sha256']
        res['candidates'][key]=s;print(key,s)
    ok={k:v for k,v in res['candidates'].items() if v['none_fired_share']<=base['none_fired_share']+0.10}
    size={'GEMMA3_1B':1,'QWEN25_1B5':2,'QWEN25_3B':3}
    res['winner']=min(ok,key=lambda k:(ok[k]['failure_sentences'],size[k.split('/')[0]],k)) if ok else None
    res['rule']='fewest failure sentences with none_fired_share <= fixed + 0.10; tie -> smaller model (PREREG.md)'
    print('fixed',base,'winner',res['winner'])
    (HERE/'select_second.json').write_text(json.dumps(res,ensure_ascii=False,indent=1)+'\n')

if __name__=='__main__':
    if sys.argv[3]=='run':run(sys.argv[1],sys.argv[2])
    else:score()
