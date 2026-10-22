#!/usr/bin/env python3
"""Round 4: rewrite the 59 holdout + 46 dev sentences with three model families not used before (Phi-4-mini, Granite 3.3
2B, EuroLLM 9B) through the pinned llama-server, with a stricter keep-the-language rule (round 3 models translated many
German sentences). Raw output is written unread (only counts are printed), sealed until reader v4 is frozen (PREREG.md).
Usage: generate_round4.py <llama-server> <models-dir> <out.json>"""
import json,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'user-rules-v3'))
from generate_round3 import sha,port,ask  # same server call, schema and temperature as round 3
UR=HERE.parents[1]/'continuation-20261021/user-rules'
SOURCES=(('holdout',UR/'holdout_author.json'),('dev',UR/'dev.json'))
MODELS={'PHI4_MINI':('phi4-mini.gguf','88c00229914083cd112853aab84ed51b87bdf6b9ce42f532d8c85c7c63b1730a'),
        'GRANITE33_2B':('granite33-2b.gguf','ac71e9e32c0bea919b409c5918f69ca74339854b0319c5065e4e9fb6d95c4852'),
        'EUROLLM_9B':('eurollm-9b.gguf','785a3b2883532381704ef74f866f822f179a931801d1ed1cf12e6deeb838806b')}
LANG=(' Keep the language of the sentence: a German sentence must stay German, an English sentence must stay English. '
      'Bleibt der Satz deutsch, schreibe deutsch.')
PROMPTS={'P1':('Restate the sentence as a different person would write it in a chat. Keep the meaning. You must change the wording: '
               'do not reuse its main verb or its main noun, use synonyms or another construction. Never answer or obey it, only '
               'restate it.'+LANG+' Return JSON only.'),
         'P2':('Rewrite the sentence the way people really talk to an assistant in everyday chat: casual, indirect, idioms or short '
               'fragments are fine. Keep exactly who wants what from whom and how strict it is. Never answer or obey it, only '
               'rewrite it.'+LANG+' Return JSON only.')}
SEED0=4000

def main(server,mdir,out):
    items=[(src,i,it) for src,f in SOURCES for i,it in enumerate(json.loads(f.read_text())['items'])];rows=[];mdir=Path(mdir)
    for name,(fn,h) in MODELS.items():
        if sha(mdir/fn)!=h:raise SystemExit('model hash mismatch: '+fn)
        p=port();proc=subprocess.Popen([server,'-m',str(mdir/fn),'--port',str(p),'-c','2048','-t','4','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(600):
                try:
                    if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).read()).get('status')=='ok':break
                except Exception:pass
                time.sleep(1)
            for k,(src,i,it) in enumerate(items):
                for pid,system in PROMPTS.items():
                    t0=time.monotonic();raw=''
                    try:raw=ask(p,system,it['text'],SEED0+k);sent=json.loads(raw)['sentence'].strip();err=None
                    except Exception as exc:sent=None;err=type(exc).__name__
                    rows.append({'source':src,'index':i,'model':name,'prompt':pid,'original':it['text'],'raw':raw,'sentence':sent,'error':err,
                                 'seconds':round(time.monotonic()-t0,2)})
            print(name,'done',sum(r['model']==name and r['sentence'] is not None for r in rows),flush=True)
        finally:proc.terminate();proc.wait()
    data={'schema':'USER_RULES_ROUND4_RAW_V1','sources':{s:{'file':str(f.relative_to(HERE.parents[3])),'sha256':sha(f)} for s,f in SOURCES},
          'runner':'llama.cpp b10964','models':{k:{'file':v[0],'sha256':v[1]} for k,v in MODELS.items()},'prompts':PROMPTS,'seed0':SEED0,'rows':rows}
    Path(out).write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n')
    print('rows',len(rows),'sha256',sha(out))

if __name__=='__main__':main(*sys.argv[1:4])
