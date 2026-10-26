#!/usr/bin/env python3
"""WP-UR8 measurement on holdout_de5 (T1) and the round-8 cohort (T2): fixed reader v8 alone, v7 for comparison, and
fixed v8 + second reader for every candidate (exploratory after the selection found none within the cost rule; Gemma 3 1B
prompt A named beforehand). Checks freeze_v8.json first; model verdicts are cached in measure_cache.json (resumable).
Usage: run_round8.py <llama-server> <models-dir> [ask|score]"""
import hashlib,json,subprocess,sys,time,types,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];P=HERE.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(P.parent/'continuation-20261021/user-rules'));sys.path.insert(0,str(P/'user-rules-v3'))
import userrules_eval as E
sys.path.insert(0,str(HERE));import snapshot
U,S=snapshot.load()
from generate_round3 import sha,port
from select_second import CANDS,shim
CACHE=HERE/'measure_cache.json';SETS={'T1':HERE/'holdout_de5.json','T2':HERE/'cohort_round8.json'}

def ref(path,name):
    src=Path(path).read_text().replace('from .agi.base import StateBox','StateBox=None')
    m=types.ModuleType(name);m.__file__=str(path);exec(compile(src,str(path),'exec'),m.__dict__);return m

def ask(server,mdir):
    cache=json.loads(CACHE.read_text()) if CACHE.exists() else {}
    texts=sorted({it['text'] for f in SETS.values() for it in json.loads(f.read_text())['items']})
    for name,fn in CANDS.items():
        p=port();proc=subprocess.Popen([server,'-m',str(Path(mdir)/fn),'--port',str(p),'-c','2048','-t','4','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(600):
                try:
                    if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).read()).get('status')=='ok':break
                except Exception:pass
                time.sleep(1)
            for pr in S.PROMPTS:
                c=cache.setdefault(name+'/'+pr,{'sha256':sha(Path(mdir)/fn),'v':{}})
                for t in texts:
                    if t not in c['v']:c['v'][t]=S.ask_llama(f'http://127.0.0.1:{p}',pr,t)
                CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=0)+'\n');print(name,pr,'done',flush=True)
        finally:proc.terminate();proc.wait()

def stats(its,mod):
    E.U=mod;tot,rows=E.score(its);none=[r for r in rows if r['want_kind']=='NONE']
    return {'failure_sentences':sum(1 for r in rows if r['safety_failures']),'safety_failures':tot['safety_failures'],
            'missed_prohibitions':sum(1 for r in rows if r['want_kind']=='FORBID' and r['safety_failures']),
            'weaker_than_label':sum(1 for r in rows if r['want_kind'] in ('FORBID','ASK_FIRST','UNCLEAR') and r['got_kind'] in ('NONE','LOOSEN')),
            'none_fired_share':round(sum(r['got_kind']!='NONE' for r in none)/max(len(none),1),3),'none_sentences':len(none),
            'over_caution':tot['over_caution'],'soft_deny_as_ask':tot['soft_deny_as_ask'],'items':len(its)},rows

def score():
    cache=json.loads(CACHE.read_text());v7=ref(HERE/'reference_v7/userrules.py','u7');res={}
    for tn,f in SETS.items():
        its=json.loads(f.read_text())['items'];fx,frows=stats(its,U);r7,_=stats(its,v7)
        out={'fixed_v8':fx,'v7':r7,'fixed_v8_failures':[r['text'] for r in frows if r['safety_failures']],'second':{}}
        rank={'ALLOW':0,'ASK':1,'DENY':2}
        for key,c in cache.items():
            s,rows=stats(its,shim(c['v']))
            s['weaker_than_fixed_probes']=sum(1 for a,b in zip(frows,rows) for p in a['verdicts'] if rank[b['verdicts'][p]]<rank[a['verdicts'][p]])
            s['invalid_share']=round(sum(c['v'].get(it['text']) is None for it in its)/len(its),3)
            s['caught']=[b['text'] for a,b in zip(frows,rows) if a['safety_failures'] and not b['safety_failures']]
            out['second'][key]=s
        res[tn]=out
        print(tn,'fixed v8',fx);print(tn,'v7',r7)
        for k,s in out['second'].items():print(tn,k,{x:s[x] for x in ('failure_sentences','none_fired_share','weaker_than_fixed_probes','invalid_share')})
        for t in out['fixed_v8_failures']:print('   FIXED FAIL |',t)
    (HERE/'result_round8.json').write_text(json.dumps(res,ensure_ascii=False,indent=1)+'\n')

if __name__=='__main__':
    if sys.argv[3]=='ask':ask(sys.argv[1],sys.argv[2])
    else:score()
