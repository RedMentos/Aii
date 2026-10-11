"""WP-S7 follow-up: does the sleep day digest help recall of facts that fell out of the history window?

Synthetic chats: 3 fact turns early, then filler turns; the model sees only the last HISTORY pairs (as the runtime with
history_turns) and is asked about one early fact. Condition A: no digest. Condition B: the extractive digest
(sleep_offline/context_os.compress, exact spans pinned) of the turns outside the window in the system prompt.
Greedy decoding; score = the exact fact value appears in the answer (a reformatted date counts as a miss).
Control C/D: the asked fact is inside the history window; D adds the digest of the other, older facts (harm check). Usage: digest_context_bench.py <home> <out.json>"""
import http.client
import json
import random
import socket
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.context_os import compress

HISTORY=4;N=24
FACTS=[('My locker code is {v}.','What is my locker code?'),('The dentist appointment is on {v}.','When is the dentist appointment?'),
       ('My sister lives in {v}.','Where does my sister live?'),('The wifi password is {v}.','What is the wifi password?'),
       ('Our project is called {v}.','What is our project called?'),('I parked on level {v}.','On which level did I park?')]
VALUES=[['4471','8823','1950','6604'],['2026-11-02','2026-12-14','2027-01-09','2026-10-30'],['Lisbon','Tromsø','Graz','Nantes'],
        ['blue-otter-77','ruby-fox-12','green-kite-40','sun-moth-93'],['Aurora','Kestrel','Juniper','Halcyon'],['3','5','7','2']]
FILLER=[('Can you suggest a quick breakfast?','Oatmeal with fruit is quick and filling.'),('How long should I boil an egg?','About nine minutes for a hard-boiled egg.'),
        ('Any tip for sleeping better?','Keep a regular bedtime and avoid screens late.'),('What is a good stretch for the back?','Try a gentle child pose for thirty seconds.'),
        ('How do I keep basil fresh?','Keep it in water at room temperature.'),('Is walking good exercise?','Yes, brisk walking is good daily exercise.'),
        ('How can I save on groceries?','Plan meals and buy staples in bulk.'),('What is a fun weekend idea?','Try a picnic in a nearby park.')]
SYSTEM='You are a helpful assistant. Answer briefly and use exact values from the conversation.'

def sessions(seed=13,recent=False):
    rnd=random.Random(seed);out=[]
    for i in range(N):
        fi=rnd.sample(range(len(FACTS)),3);turns=[]
        vals={}
        for f in fi:
            v=rnd.choice(VALUES[f]);vals[f]=v;turns.append((FACTS[f][0].format(v=v),'Noted, I will remember that.'))
        filler=rnd.sample(FILLER,HISTORY+1);ask=rnd.choice(fi)
        if recent:  # control: the asked fact sits inside the history window, the other facts are in the digest
            turns=[t for t,f in zip(turns,fi) if f!=ask]+filler[:HISTORY-1]+[t for t,f in zip(turns,fi) if f==ask]+filler[HISTORY-1:HISTORY]
        else:turns+=filler
        out.append({'turns':turns,'question':FACTS[ask][1],'answer':vals[ask]})
    return out

def digest(turns):
    from v13.sleep_offline import line
    return '\n'.join(line(compress(u,160)[0],compress(a,160)[0]) for u,a in turns)

def server(home,model,threads):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    p=subprocess.Popen([str(home/'bin/llama-server'),'-m',str(model),'--port',str(port),'-c','4096','-np','1','-t',str(threads),'-ngl','0','--no-warmup','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    end=time.time()+120
    while time.time()<end:
        try:
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=2);c.request('GET','/health');r=c.getresponse();r.read()
            if r.status==200:return p,port
        except OSError:pass
        time.sleep(.3)
    p.kill();raise RuntimeError('server did not start')

def ask(port,messages):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=300)
    c.request('POST','/v1/chat/completions',json.dumps({'messages':messages,'max_tokens':48,'temperature':0,'top_k':1,'seed':13,'chat_template_kwargs':{'enable_thinking':False}}),{'Content-Type':'application/json'})
    d=json.loads(c.getresponse().read());return d['choices'][0]['message']['content'],d.get('timings',{}).get('prompt_n')

def run(home,model,threads):
    p,port=server(home,model,threads);res={'A_no_digest':[],'B_digest':[],'C_in_window_no_digest':[],'D_in_window_digest':[]}
    try:
        for recent in (False,True):
          for s in sessions(recent=recent):
            last=s['turns'][-HISTORY:];old=s['turns'][:-HISTORY]
            hist=[m for u,a in last for m in ({'role':'user','content':u},{'role':'assistant','content':a})]
            names=('C_in_window_no_digest','D_in_window_digest') if recent else ('A_no_digest','B_digest')
            for cond,sys_text in ((names[0],SYSTEM),(names[1],SYSTEM+'\nEarlier in this chat (compressed digest; exact values kept):\n'+digest(old))):
                out,pn=ask(port,[{'role':'system','content':sys_text}]+hist+[{'role':'user','content':s['question']}])
                res[cond].append({'hit':s['answer'].lower() in out.lower(),'prompt_tokens':pn,'answer':out[:160],'expected':s['answer']})
    finally:p.terminate();p.wait(timeout=10)
    return {c:{'accuracy':round(sum(x['hit'] for x in v)/len(v),3),'mean_prompt_tokens':round(sum(x['prompt_tokens'] or 0 for x in v)/len(v),1),'samples':v[:4]} for c,v in res.items()}

def main(home,out,threads=4):
    home=Path(home);rep={'kind':'DIGEST_CONTEXT_BENCH','n':N,'history_pairs':HISTORY,'models':{}}
    for role in ('language','body','gist'):
        m=next((home/'models'/role).glob('*.gguf'),None)
        if m:rep['models'][m.name]=run(home,m,threads);print(m.name,{c:v['accuracy'] for c,v in rep['models'][m.name].items()},flush=True)
    Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(rep,indent=1,ensure_ascii=False))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 4)
