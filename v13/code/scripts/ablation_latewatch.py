"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_LATEWATCH (WP-U3 F2 §5.2, thread L,
2026-10-12): does the late-offer cut rule interrupt wrong answers and leave right ones alone?

Real `latewatch.Watcher.check` in mode active (it calls the unchanged `latewatch.disagreement` and the same "look again
until REENTRY_CHARS" loop as the token stream); only the runtime around it is a stub (`read_source` returns the task).
Per turn: an arithmetic question about two numbers from the source; C3's streamed answer derives the result (wrong with
p .30, off by 1-20) after 0-2 filler sentences; the late body offer arrives at a uniform character position in
[0, len(answer)+30] (after the end = too late, no cut in any arm). The body summary is right (p .80), derives another
wrong number (p .10) or is unresolved with needs_reentry and a source quote (p .10). The stream is checked every 4 chars.

Score per turn: +1 cut of a wrong answer whose body is not wrong itself (useful interrupt); -1 cut of a right answer
(needless interrupt); 0 otherwise. Primary = mean score per turn (net useful interrupts).
Arms (same turns per seed):
  rule      Watcher.check (RESULT_CONFLICT / BODY_REENTRY, BOOT MIN_CHARS 24 / REENTRY_CHARS 48)
  never     latewatch off / shadow (no cut)
  always    cut as soon as any late offer arrives before the end
  random    same number of cuts as `rule`, random turns among those whose offer arrived before the end
Streams: `standard` (integers below 1000, written plainly) and `format` (half of the turns use numbers >= 1000 written
with a thousands comma in source and answer, the body writes them plainly; reported, no pass rule).
PREREG (fixed before the first run): "helps" only if rule beats never, always and random in >= 4/5 seeds on `standard`
-> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED.
Claim limit: synthetic arithmetic turns, number-based conflict only, BOOT char thresholds; no model output.
"""
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd
from v13 import latewatch as L

PREREG={'schema':'ABLATION_LATEWATCH_PREREG_V1','seeds':list(SEEDS),'turns':400,'p_answer_wrong':.30,
        'body':{'right':.80,'wrong_number':.10,'unresolved_reentry':.10},'arrival':'uniform char in [0, len(answer)+30]','check_every_chars':4,
        'score':'+1 cut of wrong answer with non-wrong body, -1 cut of right answer, else 0','primary':'mean score per turn',
        'streams':['standard','format'],
        'win_rule':'rule beats never, always and random in >=4/5 seeds on standard -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
TURNS=400;STEP=4;ARMS=('rule','never','always','random')
OPS={'plus':('+',lambda a,b:a+b),'minus':('-',lambda a,b:a-b),'times':('*',lambda a,b:a*b)}
FILL=('Let me work through this carefully. ','You asked a quick arithmetic question. ','I will take the two values from your message. ')

def fmt(x,comma):return f'{x:,}' if comma else str(x)

def turns(seed,stream):
    rng=random.Random(seed);out=[]
    for _ in range(TURNS):
        big=stream=='format' and rng.random()<.5
        a,b=(rng.randint(1000,9999),rng.randint(10,999)) if big else (rng.randint(10,999),rng.randint(10,999))
        word=rng.choice(sorted(OPS));sym,f=OPS[word];r=f(a,b)
        wrong=rng.random()<.30;said=r+rng.choice((-1,1))*rng.randint(1,20) if wrong else r
        src=f'What is {fmt(a,big)} {word} {fmt(b,big)}?'
        ans=''.join(rng.sample(FILL,rng.randint(0,2)))+f'The result is {fmt(said,big)}, because I applied {word} to the two numbers from your question.'
        u=rng.random()
        if u<.80:body='right';offer={'summary':f'{a} {sym} {b} = {r}','needs_reentry':False,'quotes':[]}
        elif u<.90:
            body='wrong';v=r+rng.choice((-1,1))*rng.randint(1,20)
            while v==said:v+=1
            offer={'summary':f'{a} {sym} {b} = {v}','needs_reentry':False,'quotes':[]}
        else:body='unresolved';offer={'summary':'The operation is not clear from the source.','needs_reentry':True,'quotes':[src]}
        out.append({'src':src,'answer':ans,'wrong':wrong,'body':body,'offer':{'role':'B1_DETAIL','packet_id':'p','offer':offer},'arrive':rng.randint(0,len(ans)+30)})
    return out

def rule_cut(t):
    """Drive the real Watcher.check over the stream from the arrival position on; True if it stops the stream."""
    r=SimpleNamespace(store=SimpleNamespace(read_source=lambda ref:t['src']))
    w=L.Watcher(r,{'source_ref':None},{},'active','B1_DETAIL');w.thread=object();w.offer=t['offer'];w.done.set()
    ans=t['answer'];pos=list(range(t['arrive'],len(ans),STEP))+[len(ans)]
    for p in pos:
        if w.check(ans[:p]):return True
        if w.decided:return False
    return False

def score(t,cut):
    if not cut:return 0
    if not t['wrong']:return -1
    return 1 if t['body']!='wrong' else 0

def run(seed,stream):
    ts=turns(seed,stream);rng=random.Random(seed*11+3);early=[i for i,t in enumerate(ts) if t['arrive']<len(t['answer'])]
    cuts={'rule':{i for i,t in enumerate(ts) if t['arrive']<len(t['answer']) and rule_cut(t)},'never':set(),'always':set(early)}
    cuts['random']=set(rng.sample(early,len(cuts['rule'])))
    res={}
    for a in ARMS:
        s=[score(t,i in cuts[a]) for i,t in enumerate(ts)]
        res[a]={'primary':round(_mean(s),5),'cuts':len(cuts[a]),'useful':s.count(1),'needless':s.count(-1)}
    return res

def run_all(seeds=SEEDS):
    out={}
    for stream in PREREG['streams']:
        per={s:run(s,stream) for s in seeds}
        wins={a:sum(per[s]['rule']['primary']>per[s][a]['primary'] for s in seeds) for a in ARMS if a!='rule'}
        out[stream]={'per_seed':per,'wins_of_5':wins,
                     'summary':{a:{k:{'mean':round(_mean([per[s][a][k] for s in seeds]),4),'sd':round(_sd([per[s][a][k] for s in seeds]),4)} for k in ('primary','cuts','useful','needless')} for a in ARMS}}
    beat=[a for a,n in out['standard']['wins_of_5'].items() if n>=4]
    return {'prereg':PREREG,'streams':out,'beats_on_standard':beat,
            'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==3 else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic arithmetic turns, number-based conflict only, BOOT char thresholds; no model output'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'])
    for k,v in r['streams'].items():print(k,v['wins_of_5'],{a:{m:x['mean'] for m,x in d.items()} for a,d in v['summary'].items()})
