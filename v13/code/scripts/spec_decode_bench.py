"""§22.6 speculative decoding on the native runner (cloud bench). Greedy, same prompts, per config:
decode tokens/s, draft acceptance, output identical to baseline, peak RSS of the server process.
Usage: python3 scripts/spec_decode_bench.py <home> <out.json> [threads]"""
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

PROMPTS=['Explain in five sentences why regular backups matter for a small business.',
         'List the steps to plant a tomato seedling in a pot, one step per line.',
         'Repeat this sentence exactly three times: The quick brown fox jumps over the lazy dog.',
         'Write a short Python function that returns the sum of squares of a list, then explain it.']

def rss(pid):
    try:
        for line in open(f'/proc/{pid}/status'):
            if line.startswith('VmHWM:'):return int(line.split()[1])*1024
    except OSError:return None

def run(home,model,extra,threads,n=128):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    cmd=[str(home/'bin/llama-server'),'-m',str(model),'--host','127.0.0.1','--port',str(port),'-c','2048','-np','1','-t',str(threads),'-ngl','0','--no-warmup','--no-webui']+extra
    p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    try:
        end=time.time()+120
        while time.time()<end:
            if p.poll() is not None:return {'error':'server exited','stderr':p.stderr.read()[-800:]}
            try:
                c=http.client.HTTPConnection('127.0.0.1',port,timeout=2);c.request('GET','/health');r=c.getresponse();r.read()
                if r.status==200:break
            except OSError:pass
            time.sleep(.3)
        outs=[]
        for q in PROMPTS:
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=300)
            body={'messages':[{'role':'user','content':q}],'max_tokens':n,'temperature':0,'top_k':1,'seed':13,'chat_template_kwargs':{'enable_thinking':False}}
            c.request('POST','/v1/chat/completions',json.dumps(body),{'Content-Type':'application/json'});d=json.loads(c.getresponse().read())
            t=d.get('timings',{})
            outs.append({'text':d['choices'][0]['message']['content'],'predicted_n':t.get('predicted_n'),'predicted_per_second':t.get('predicted_per_second'),
                         'draft_n':t.get('draft_n'),'draft_n_accepted':t.get('draft_n_accepted')})
        return {'runs':outs,'peak_rss_bytes':rss(p.pid)}
    finally:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill()

def main(home,out,threads=4):
    home=Path(home);body=next((home/'models/body').glob('*.gguf'));lang=next((home/'models/language').glob('*.gguf'))
    configs={'baseline':[],'ngram_simple':['--spec-type','ngram-simple'],'draft_230m':['-md',str(lang),'--spec-draft-n-max','4','-td',str(threads)]}
    rep={'kind':'SPEC_DECODE_BENCH','target':body.name,'draft':lang.name,'threads':threads,'configs':{}}
    for name,extra in configs.items():
        r=run(home,body,extra,threads);rep['configs'][name]=r
        if 'runs' in r:r['mean_tps']=round(sum(x['predicted_per_second'] or 0 for x in r['runs'])/len(r['runs']),2)
        print(name,r.get('mean_tps'),r.get('error'),flush=True)
    base=rep['configs']['baseline'].get('runs')
    for name,r in rep['configs'].items():
        if base and 'runs' in r:
            r['identical_to_baseline']=[a['text']==b['text'] for a,b in zip(r['runs'],base)]
            acc=[(x['draft_n_accepted'] or 0)/(x['draft_n'] or 1) for x in r['runs'] if x.get('draft_n')]
            r['acceptance']=round(sum(acc)/len(acc),3) if acc else None
            r['speedup']=round(r['mean_tps']/rep['configs']['baseline']['mean_tps'],3) if rep['configs']['baseline'].get('mean_tps') else None
    Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(rep,indent=1))
    print(json.dumps({k:{x:v.get(x) for x in ('mean_tps','speedup','acceptance','identical_to_baseline','peak_rss_bytes','error')} for k,v in rep['configs'].items()},indent=1))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 4)
