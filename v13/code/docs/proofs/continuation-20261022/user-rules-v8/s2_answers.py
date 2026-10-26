#!/usr/bin/env python3
"""S2 (comparison only, stays off): LFM2.5-1.2B-Instruct answers the fixed question of PREREG v8 for every sentence of a cohort,
temperature 0, JSON schema {"regel": bool}. Writes {text: true|false|null} (null = no valid answer, counted as yes = ask).
Usage: s2_answers.py <llama-server> <model.gguf> <sha256> <cohort.json> <out.json>"""
import json,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'user-rules-v3'))
from generate_round3 import sha,port
QUESTION=('Verbietet oder beschränkt dieser Satz etwas, das der Assistent tun darf, oder verlangt er, vorher gefragt zu werden? '
          'Auch unsicher oder zitiert zählt als ja.')
SCHEMA={'type':'object','properties':{'regel':{'type':'boolean'}},'required':['regel']}

def ask(p,text):
    body={'messages':[{'role':'system','content':QUESTION+' Gib nur JSON zurück.'},{'role':'user','content':'Satz: '+text}],'temperature':0,'seed':1,
          'max_tokens':20,'response_format':{'type':'json_schema','json_schema':{'name':'r','schema':SCHEMA}}}
    req=urllib.request.Request(f'http://127.0.0.1:{p}/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
    return json.loads(json.loads(urllib.request.urlopen(req,timeout=120).read())['choices'][0]['message']['content'])['regel']

def main(server,model,h,cohort,out):
    if sha(model)!=h:raise SystemExit('model hash mismatch')
    texts=[it['text'] for it in json.loads(Path(cohort).read_text())['items']];res={}
    p=port();proc=subprocess.Popen([server,'-m',model,'--port',str(p),'-c','1024','-t','4','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(300):
            try:
                if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).read()).get('status')=='ok':break
            except Exception:pass
            time.sleep(1)
        for t in texts:
            try:res[t]=bool(ask(p,t))
            except Exception:res[t]=None
    finally:proc.terminate();proc.wait()
    Path(out).write_text(json.dumps({'model':Path(model).name,'sha256':h,'question':QUESTION,'answers':res},ensure_ascii=False,indent=1)+'\n')
    print('answers',len(res),'yes',sum(v is True for v in res.values()),'none',sum(v is None for v in res.values()))

if __name__=='__main__':main(*sys.argv[1:6])
