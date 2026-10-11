"""WP-S1 / WP-G / WP-V3: C3 candidate benchmark (cloud, English first). Diagnostic only, never promotes a model.

Candidates from specs/cloud-candidates.json (hash-checked GGUFs): LFM2.5-230M (installed C3), LFM2.5-350M,
Gemma-3-270M-it, Qwen3.5-0.8B. Same pinned llama-server, the production V13 system prompt + answer rules and the
production C3 decoder (guards.C3_DECODER, anti_echo) with 3 seeds; legacy sampling is run as the V3 comparison.
Task families (exact checks, no model judge): grounded exact value, abstention, format following, rewrite with
forbidden word, digest recall (WP-S7 digest format), open questions (query echo / repetition via guards.turn_metrics).
Speed: decode tokens/s, prompt tokens/s; memory: peak RSS (VmHWM) of the server.
Usage: c3_candidates_bench.py <home> <candidate_dir> <out.json> [threads]"""
import http.client
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.guards import C3_DECODER,LEGACY_DECODER,turn_metrics
from v13.prompts import TEXT

EN=TEXT['en'];SYSTEM=EN['system']+' '+EN['answer_rules'];SEEDS=(13,14,15)
G=[('Project Aurora has a budget of 120 euros.','How large is the budget?','120'),
   ('The train to Graz leaves at 7:45 from platform 3.','From which platform does the train leave?','3'),
   ('Mila was born in 1994 in Porto.','In which year was Mila born?','1994'),
   ('The invoice number is 55-1209 and it is due on 2026-11-02.','What is the invoice number?','55-1209'),
   ('The router password is blue-otter-77.','What is the router password?','blue-otter-77'),
   ('Our team has 14 members; 5 work remotely.','How many members work remotely?','5'),
   ('The recipe needs 250 grams of flour and 2 eggs.','How many grams of flour are needed?','250'),
   ('Room B212 is booked for the workshop on Friday.','Which room is booked?','B212'),
   ('The package weighs 3.4 kg and costs 12.90 euros to ship.','How much does shipping cost?','12.90'),
   ('Dr. Okafor moved the appointment to Tuesday at 10:30.','When is the appointment?','10:30')]
A=[('Project Aurora has a budget of 120 euros.','Who leads Project Aurora?'),
   ('The train to Graz leaves at 7:45.','How much does the ticket cost?'),
   ('Mila was born in 1994 in Porto.','What is Mila\'s job?'),
   ('The recipe needs 250 grams of flour.','How long does it bake?'),
   ('Room B212 is booked on Friday.','Who booked the room?'),
   ('The package weighs 3.4 kg.','When will the package arrive?')]
ABSTAIN=re.compile(r"\b(not|no|unknown|isn't|doesn't|does not|cannot|can't|unclear|nothing verified)\b",re.I)
F=[('Answer with exactly one word: what is the capital of France?',lambda o:len(o.split())<=2 and 'paris' in o.lower()),
   ('List exactly three fruits, comma-separated, nothing else.',lambda o:len([x for x in re.split(r',',o.strip().strip('.')) if x.strip()])==3),
   ('Reply only with the number: 17 plus 25?',lambda o:o.strip().strip('.')=='42'),
   ('Answer yes or no only: is water wet?',lambda o:o.strip().strip('.!').lower() in ('yes','no')),
   ('Write the word "ready" in capital letters and nothing else.',lambda o:o.strip().strip('.!"')=='READY'),
   ('Give a title of at most four words for a text about saving energy at home.',lambda o:0<len(o.strip().strip('"*#').split())<=4)]
R=[('Rephrase briefly: The test runs locally and uses no cloud.','local','online'),
   ('Rephrase briefly: The meeting moved from Monday to Wednesday.','wednesday','tuesday'),
   ('Rephrase briefly: Backups run every night at 2 am.','2','weekly'),
   ('Rephrase briefly: The shop closes at 6 pm on Saturdays.','6','sunday')]
D=[(['- user: My locker code is 4471.','- user: The wifi password is ruby-fox-12.'],'What is my locker code?','4471'),
   (['- user: My sister lives in Tromsø.','- user: Our project is called Kestrel.'],'What is our project called?','Kestrel'),
   (['- user: I parked on level 5.','- user: My locker code is 8823.'],'On which level did I park?','5'),
   (['- user: The wifi password is green-kite-40.','- user: My sister lives in Graz.'],'Where does my sister live?','Graz')]
O=['Explain in two sentences how a local assistant can remember corrections.','What are three steps to plan a small garden on a balcony?',
   'Compare trains and buses for a 50 km daily commute.','Why does a phone get warm when it runs a language model?']

def rss(pid):
    try:
        for line in open(f'/proc/{pid}/status'):
            if line.startswith('VmHWM:'):return int(line.split()[1])*1024
    except OSError:return None

def server(home,model,threads):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    p=subprocess.Popen([str(home/'bin/llama-server'),'-m',str(model),'--port',str(port),'-c','2048','-np','1','-t',str(threads),'-ngl','0','--no-warmup','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    end=time.time()+120
    while time.time()<end:
        if p.poll() is not None:raise RuntimeError('server exited')
        try:
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=2);c.request('GET','/health');r=c.getresponse();r.read()
            if r.status==200:return p,port
        except OSError:pass
        time.sleep(.3)
    p.kill();raise RuntimeError('server did not start')

def chat(port,system,user,decoder,seed,n=160):
    body={'messages':[{'role':'system','content':system},{'role':'user','content':user}],'max_tokens':n,'seed':seed,'chat_template_kwargs':{'enable_thinking':False}}|decoder
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=300);c.request('POST','/v1/chat/completions',json.dumps(body),{'Content-Type':'application/json'})
    d=json.loads(c.getresponse().read());return d['choices'][0]['message']['content'] or '',d.get('timings',{})

def run_model(home,model,threads,decoder,seeds):
    p,port=server(home,model,threads);rows=[];tps=[];pps=[]
    def ask(system,user,family,check,query=None):
        for seed in seeds:
            out,t=chat(port,system,user,decoder,seed);tps.append(t.get('predicted_per_second') or 0);pps.append(t.get('prompt_per_second') or 0)
            m=turn_metrics(out,query or user);rows.append({'family':family,'ok':bool(check(out)) if check else None,'echo':m['query_echo'],'rep':m['repetition_rate'],'out':out[:200],'seed':seed,'q':user[:80]})
    try:
        for src,q,v in G:ask(SYSTEM,'Source: '+src+' Question: '+q,'grounded',lambda o,v=v:v.lower() in o.lower())
        for src,q in A:ask(SYSTEM,'Source: '+src+' Question: '+q,'abstain',lambda o:bool(ABSTAIN.search(o)))
        for q,f in F:ask(SYSTEM,q,'format',f)
        for q,keep,forbid in R:ask(SYSTEM,q,'rewrite',lambda o,k=keep,f=forbid:k in o.lower() and f not in o.lower())
        for lines,q,v in D:ask(SYSTEM+'\n'+EN['digest']+'\n'+'\n'.join(lines),q,'digest',lambda o,v=v:v.lower() in o.lower())
        for q in O:ask(SYSTEM,q,'open',None)
        peak=rss(p.pid)
    finally:p.terminate();p.wait(timeout=10)
    fam={}
    for r in rows:
        f=fam.setdefault(r['family'],{'n':0,'ok':0,'echo':0.,'rep':0.})
        f['n']+=1;f['ok']+=int(bool(r['ok']));f['echo']+=r['echo'];f['rep']+=r['rep']
    out={k:{'accuracy':round(v['ok']/v['n'],3) if k!='open' else None,'query_echo':round(v['echo']/v['n'],3),'repetition':round(v['rep']/v['n'],3)} for k,v in fam.items()}
    scored=[r for r in rows if r['family']!='open']
    return {'families':out,'overall':round(sum(r['ok'] for r in scored)/len(scored),3),'decode_tps':round(sum(tps)/len(tps),1),'prompt_tps':round(sum(pps)/len(pps),1),
            'peak_rss_bytes':peak,'samples':[r for r in rows if not r['ok'] and r['family']!='open'][:6]}

def main(home,cand_dir,out,threads=4):
    home,cand_dir=Path(home),Path(cand_dir)
    models={'lfm25_230m (installed)':next((home/'models/language').glob('*.gguf')),'lfm25_350m':cand_dir/'LFM2.5-350M-QAD-Q4_0.gguf',
            'gemma3_270m_it':cand_dir/'gemma-3-270m-it-Q4_0.gguf','qwen35_0p8b':next((home/'models/gist').glob('*.gguf'))}
    rep={'kind':'C3_CANDIDATES_BENCH','threads':threads,'seeds':list(SEEDS),'decoder':'anti_echo (guards.C3_DECODER)','models':{},'legacy_v3':{}}
    for name,m in models.items():
        if not m.exists():rep['models'][name]={'error':'missing'};continue
        rep['models'][name]=run_model(home,m,threads,C3_DECODER,SEEDS);r=rep['models'][name]
        print(name,r['overall'],{k:v['accuracy'] for k,v in r['families'].items()},r['decode_tps'],r['peak_rss_bytes'],flush=True)
    for name in ('lfm25_230m (installed)','lfm25_350m'):  # WP-V3: same model, legacy sampling, same seeds
        rep['legacy_v3'][name]=run_model(home,models[name],threads,{'temperature':.1}|LEGACY_DECODER,SEEDS)
        print('legacy',name,rep['legacy_v3'][name]['overall'],rep['legacy_v3'][name]['families'].get('open'),flush=True)
    Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(rep,indent=1,ensure_ascii=False))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]) if len(sys.argv)>4 else 4)
