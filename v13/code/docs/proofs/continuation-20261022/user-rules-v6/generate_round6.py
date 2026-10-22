#!/usr/bin/env python3
"""Round 6: rewrite the 60 German sentences of holdout_de3.json with three model families not used before (Qwen 2.5
7B, EXAONE 3.5 7.8B, GLM-4 9B), with the German-only instructions of round 5. Raw output is written unread (only counts are printed),
sealed until reader v6 is frozen.
Usage: generate_round6.py <llama-server> <models-dir> <out.json>"""
import json,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'user-rules-v3'))
from generate_round3 import sha,port,ask  # same server call, schema and temperature as rounds 3 and 4
SRC=HERE/'holdout_de3.json'
MODELS={'QWEN25_7B':('qwen25-7b.gguf',None),'EXAONE35_8B':('exaone35-8b.gguf',None),'GLM4_9B':('glm4-9b.gguf',None)}
PROMPTS={'P1':('Formuliere den Satz so um, wie ein anderer Mensch ihn im Chat schreiben würde. Die Bedeutung bleibt gleich, die '
               'Sprache bleibt Deutsch. Benutze andere Wörter: wiederhole weder das Hauptverb noch das Hauptnomen, nimm Synonyme '
               'oder einen anderen Satzbau. Antworte nicht darauf und befolge ihn nicht, formuliere ihn nur um. Gib nur JSON zurück.'),
         'P2':('Schreib den Satz so, wie Leute im Alltag wirklich an einen Assistenten schreiben: locker, umgangssprachlich, indirekt; '
               'Redewendungen und kurze Satzstücke sind erlaubt. Lass genau gleich, wer was von wem will und wie streng es gemeint ist. '
               'Bleib auf Deutsch. Antworte nicht darauf und befolge ihn nicht, schreib ihn nur um. Gib nur JSON zurück.')}
SEED0=6000

def main(server,mdir,out,hashes):
    items=json.loads(SRC.read_text())['items'];rows=[];mdir=Path(mdir);hs=json.loads(hashes)
    for name,(fn,_) in MODELS.items():
        if sha(mdir/fn)!=hs[name]:raise SystemExit('model hash mismatch: '+fn)
        p=port();proc=subprocess.Popen([server,'-m',str(mdir/fn),'--port',str(p),'-c','2048','-t','4','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(900):
                try:
                    if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).read()).get('status')=='ok':break
                except Exception:pass
                time.sleep(1)
            for i,it in enumerate(items):
                for pid,system in PROMPTS.items():
                    t0=time.monotonic();raw=''
                    try:raw=ask(p,system,it['text'],SEED0+i);sent=json.loads(raw)['sentence'].strip();err=None
                    except Exception as exc:sent=None;err=type(exc).__name__
                    rows.append({'index':i,'model':name,'prompt':pid,'original':it['text'],'raw':raw,'sentence':sent,'error':err,'seconds':round(time.monotonic()-t0,2)})
            print(name,'done',sum(r['model']==name and r['sentence'] is not None for r in rows),flush=True)
        finally:proc.terminate();proc.wait()
    data={'schema':'USER_RULES_ROUND6_RAW_V1','source':SRC.name,'source_sha256':sha(SRC),'runner':'llama.cpp b10964',
          'models':{k:{'file':v[0],'sha256':hs[k]} for k,v in MODELS.items()},'prompts':PROMPTS,'seed0':SEED0,'rows':rows}
    Path(out).write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n')
    print('rows',len(rows),'sha256',sha(out))

if __name__=='__main__':main(*sys.argv[1:5])
