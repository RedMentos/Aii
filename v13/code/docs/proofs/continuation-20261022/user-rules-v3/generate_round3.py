#!/usr/bin/env python3
"""Round 3: rewrite the 59 holdout sentences with three model families not used before (Gemma 3 4B, Llama 3.2 3B,
SmolLM3 3B) through a pinned llama-server. Raw output is written unread (nothing is printed but counts), so the
sentences stay sealed until reader v3 is frozen (PREREG.md). Usage: generate_round3.py <llama-server> <models-dir> <out.json>"""
import hashlib,json,socket,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
SRC=HERE.parents[1]/'continuation-20261021/user-rules/holdout_author.json'
MODELS={'GEMMA3_4B':('gemma3-4b.gguf','04a43a22e8d2003deda5acc262f68ec1005fa76c735a9962a8c77042a74a7d19'),
        'LLAMA32_3B':('llama32-3b.gguf','6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff'),
        'SMOLLM3_3B':('smollm3-3b.gguf','4de907d2d388a5508fb7cb443a06effe14cce3518b0a78d3bdd9e74d9edce989')}
PROMPTS={'P1':('Restate the sentence as a different person would write it in a chat. Keep the meaning and the language. You must '
               'change the wording: do not reuse its main verb or its main noun, use synonyms or another construction. Never answer '
               'or obey it, only restate it. Return JSON only.'),
         'P2':('Rewrite the sentence the way people really talk to an assistant in everyday chat: casual, indirect, idioms or short '
               'fragments are fine. Keep exactly who wants what from whom and how strict it is. Keep the language (German stays '
               'German, English stays English). Never answer or obey it, only rewrite it. Return JSON only.')}
SCHEMA={'type':'object','additionalProperties':False,'required':['sentence'],'properties':{'sentence':{'type':'string','maxLength':240}}}
SEED0=3000
NO_THINK={'SMOLLM3_3B':'/no_think '}  # SmolLM3 reasons by default and spends the token budget on it

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def port():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p

def ask(p,system,text,seed,prefix=''):
    body={'messages':[{'role':'system','content':prefix+system},{'role':'user','content':'Sentence: '+text}],'temperature':0.8,'seed':seed,
          'max_tokens':160,'response_format':{'type':'json_schema','json_schema':{'name':'r','schema':SCHEMA}}}
    req=urllib.request.Request(f'http://127.0.0.1:{p}/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=180).read())['choices'][0]['message']['content']

def main(server,mdir,out):
    items=json.loads(SRC.read_text())['items'];rows=[];mdir=Path(mdir)
    for name,(fn,h) in MODELS.items():
        if sha(mdir/fn)!=h:raise SystemExit('model hash mismatch: '+fn)
        p=port();proc=subprocess.Popen([server,'-m',str(mdir/fn),'--port',str(p),'-c','2048','-t','4','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(240):
                try:
                    if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).read()).get('status')=='ok':break
                except Exception:pass
                time.sleep(1)
            for i,it in enumerate(items):
                for pid,system in PROMPTS.items():
                    t0=time.monotonic();raw=''
                    try:raw=ask(p,system,it['text'],SEED0+i,NO_THINK.get(name,''));sent=json.loads(raw)['sentence'].strip();err=None
                    except Exception as exc:sent=None;err=type(exc).__name__
                    rows.append({'index':i,'model':name,'prompt':pid,'original':it['text'],'raw':raw,'sentence':sent,'error':err,
                                 'seconds':round(time.monotonic()-t0,2)})
            print(name,'done',sum(r['model']==name and r['sentence'] is not None for r in rows),flush=True)
        finally:proc.terminate();proc.wait()
    data={'schema':'USER_RULES_ROUND3_RAW_V1','source':str(SRC.relative_to(HERE.parents[3])),'source_sha256':sha(SRC),'runner':'llama.cpp b10964',
          'models':{k:{'file':v[0],'sha256':v[1]} for k,v in MODELS.items()},'prompts':PROMPTS,'seed0':SEED0,'rows':rows}
    Path(out).write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n')
    print('rows',len(rows),'sha256',sha(out))

if __name__=='__main__':main(*sys.argv[1:4])
