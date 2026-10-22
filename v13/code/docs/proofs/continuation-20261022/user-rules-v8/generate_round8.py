#!/usr/bin/env python3
"""Round 8: rewrite the 60 German sentences of holdout_de5.json with three model families not used before (DeepSeek-V2-Lite
Chat, StableLM 2 12B Chat, Nemotron-Mini 4B Instruct; fallbacks in this order: MiniCPM3 4B, ERNIE 4.5 21B-A3B, see PREREG),
with the German-only instructions of rounds 5-7. One model at a time (disk), raw output written unread (only counts are
printed), sealed until reader v8 and the second-opinion reader are frozen.
Usage: generate_round8.py <llama-server> <models-dir> <out.json> <hashes-json> [MODEL ...]  (default: the three primaries;
       an existing <out.json> is extended, so models can run one after another)"""
import json,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'user-rules-v3'));sys.path.insert(0,str(HERE.parent/'user-rules-v7'))
from generate_round3 import sha,port,ask  # same server call, schema and temperature as rounds 3-7
from generate_round7 import PROMPTS  # unchanged German-only P1/P2 of rounds 5-7
SRC=HERE/'holdout_de5.json'
MODELS={'DEEPSEEK_V2_LITE':'deepseek-v2-lite-chat.gguf','STABLELM2_12B':'stablelm-2-12b-chat.gguf','NEMOTRON_MINI_4B':'nemotron-mini-4b.gguf',
        'MINICPM3_4B':'minicpm3-4b.gguf','ERNIE45_21B_A3B':'ernie45-21b-a3b.gguf'}
PRIMARY=('DEEPSEEK_V2_LITE','STABLELM2_12B','NEMOTRON_MINI_4B')
SEED0=8000

def main(server,mdir,out,hashes,names):
    items=json.loads(SRC.read_text())['items'];mdir=Path(mdir);hs=json.loads(Path(hashes).read_text())
    old=json.loads(Path(out).read_text()) if Path(out).exists() else None
    rows=old['rows'] if old else [];used=dict(old['models']) if old else {}
    for name in names:
        fn=MODELS[name]
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
            used[name]={'file':fn,'sha256':hs[name]}
            print(name,'done',sum(r['model']==name and r['sentence'] is not None for r in rows),flush=True)
        finally:proc.terminate();proc.wait()
    data={'schema':'USER_RULES_ROUND8_RAW_V1','source':SRC.name,'source_sha256':sha(SRC),'runner':'llama.cpp b10964',
          'models':used,'prompts':PROMPTS,'seed0':SEED0,'rows':rows}
    Path(out).write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n')
    print('rows',len(rows),'sha256',sha(out))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5:] or PRIMARY)
