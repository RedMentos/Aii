#!/usr/bin/env python3
"""WP-KAL: measure BOOT start values against real llama.cpp models (cloud bench, English first).

Experiments (each writes <out>/<name>.json, nothing is promoted automatically):
  ag12    AG12 generality suite (88 EN items) per chat model; confidence = mean token probability.
  pairs   Curated EN statement pairs: lexical focal.disagreement vs LLM yes/no judge vs embedding cosine.
  offers  Real B1/B2 JSON offers (cognition.OFFER_SCHEMA) on checkable tasks: focal.offer_uncertainty and
          focal.disagreement against correctness; body latency (effort min_body_seconds).
  effort  C3 alone vs C3 + B1 offer on checkable tasks -> need labels; sweep effort escalation values.
  echo    Anti-echo decoder sweep for C3 candidates over several seeds (guards.turn_metrics).

Usage (after cloud_bench.sh setup):
  PYTHONPATH=code python3 code/scripts/calibrate_real.py --home /tmp/v13-bench/home --cache /tmp/v13-bench/candidates \
      --out bench-results/kalibrierung-<date> ag12 pairs offers effort echo
"""
import argparse,itertools,json,math,os,re,sys,time
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP));sys.path.insert(0,str(APP/'scripts'))
import cloud_candidates as cc
from v13 import focal,effort
from v13.cognition import OFFER_SCHEMA,scaffold_route,offer_instructions
from v13.prompts import text as rt_prompt
from v13.guards import C3_DECODER,turn_metrics
from v13.agi import generality as g12

SPEC=json.loads((APP/'specs/cloud-candidates.json').read_text())['candidates']
CHAT=['lfm25_230m_c3','lfm25_350m','gemma3_270m_it','qwen35_0p8b','lfm25_1p2b_body']

def model_path(cid,home,cache):
    c=next(x for x in SPEC if x['id']==cid)
    if c.get('baseline'):
        p=next(home.glob('models/**/'+c['local_name']),None)
        if p:return p
        raise SystemExit('baseline model missing: '+c['local_name'])
    return cc.fetch(c,cache)

class Server:
    def __init__(self,cid,a,extra=()):
        self.cid=cid;server=next((a.home/'bin').glob('b*/llama-*/llama-server'))
        log=open(a.out/f'server-{cid}.log','ab')
        self.proc,self.port,state=cc.serve(server,model_path(cid,a.home,a.cache),list(extra),log)
        if state!='OK':raise SystemExit(f'{cid}: server {state}')
    def __enter__(self):return self
    def __exit__(self,*x):self.proc.terminate();self.proc.wait(10)
    def chat(self,messages,max_tokens=64,temperature=0.,logprobs=False,schema=None,seed=13,**extra):
        body={'messages':messages,'max_tokens':max_tokens,'temperature':temperature,'seed':seed,
              'chat_template_kwargs':{'enable_thinking':False}}|extra
        if logprobs:body|={'logprobs':True,'top_logprobs':5}
        if schema:body['json_schema']=schema
        t0=time.monotonic();d=cc.post(self.port,'/v1/chat/completions',body,300)
        ch=d['choices'][0];lp=((ch.get('logprobs') or {}).get('content')) or []
        return {'text':ch['message'].get('content') or '','logprobs':lp,'seconds':time.monotonic()-t0,'timings':d.get('timings',{})}
    def native(self,messages,max_tokens=64,schema=None,seed=13,n_probs=0,**sampling):
        """Runtime-faithful path (runners.LlamaRunner): chat template -> /completion, raw logprobs via n_probs."""
        t0=time.monotonic()
        prompt=cc.post(self.port,'/apply-template',{'messages':messages,'add_generation_prompt':True,'chat_template_kwargs':{'enable_thinking':False}},60)['prompt']
        body={'prompt':prompt,'n_predict':max_tokens,'stream':False,'seed':seed,'cache_prompt':True}|sampling
        if schema:body['json_schema']=schema
        if n_probs:body['n_probs']=n_probs
        d=cc.post(self.port,'/completion',body,300)
        pairs=[(x.get('token',''),x['logprob']) for x in d.get('completion_probabilities') or [] if isinstance(x.get('logprob'),(int,float))]
        return {'text':d.get('content',''),'pairs':pairs,'seconds':time.monotonic()-t0,'timings':d.get('timings',{})}
    def embed(self,texts):return [x['embedding'] for x in cc.post(self.port,'/v1/embeddings',{'input':texts},120)['data']]

def auroc(scores,labels):
    """P(score_pos > score_neg); ties count half. labels 1 = positive."""
    pos=[s for s,l in zip(scores,labels) if l];neg=[s for s,l in zip(scores,labels) if not l]
    if not pos or not neg:return None
    return round(sum((p>n)+.5*(p==n) for p in pos for n in neg)/(len(pos)*len(neg)),4)
def best_threshold(scores,labels):
    """Youden-optimal threshold (predict positive if score >= t) and its accuracy/F1."""
    best=None
    for t in sorted(set(scores)):
        tp=sum(s>=t and l for s,l in zip(scores,labels));fp=sum(s>=t and not l for s,l in zip(scores,labels))
        P=sum(labels);N=len(labels)-P;tpr=tp/P if P else 0;fpr=fp/N if N else 0
        f1=2*tp/(tp+fp+P) if tp else 0.
        cand=(tpr-fpr,f1,t)
        if best is None or cand>best[0]:best=(cand,{'threshold':round(t,4),'tpr':round(tpr,4),'fpr':round(fpr,4),'f1':round(f1,4),
                                                     'accuracy':round((tp+N-fp)/len(labels),4)})
    return best[1] if best else None
def at_threshold(scores,labels,t):
    tp=sum(s>=t and l for s,l in zip(scores,labels));fp=sum(s>=t and not l for s,l in zip(scores,labels));P=sum(labels);N=len(labels)-P
    return {'threshold':t,'tpr':round(tp/P,4) if P else None,'fpr':round(fp/N,4) if N else None,'accuracy':round((tp+N-fp)/len(labels),4)}
def mean_prob(lp):
    v=[x['logprob'] for x in lp if x.get('token','').strip()]
    return round(math.exp(sum(v)/len(v)),4) if v else 0.

ANS=re.compile(r'^(?:the\s+)?(?:final\s+)?(?:answer|result)\s*(?:is)?\s*[:=]?\s*',re.I)
def extract(text):
    t=(text or '').strip().splitlines()[0] if (text or '').strip() else ''
    t=ANS.sub('',t).strip().strip('`*"\' ').rstrip('.').strip()
    if '=' in t:t=t.split('=')[-1].strip()
    return t

# ---------------------------------------------------------------- ag12
SYS_AG12='Answer with only the final answer. No explanation, no units, no extra words.'
def run_ag12(a):
    suite=g12.build_suite(lang='en');out={'suite_hash':suite['hash'],'items':len(suite['items']),'models':{}}
    for cid in a.models:
        rows=[]
        with Server(cid,a) as s:
            for it in suite['items']:
                r=s.chat([{'role':'system','content':SYS_AG12},{'role':'user','content':it['prompt']}],max_tokens=24,logprobs=True)
                ans=extract(r['text']);ok=int(g12.normalize(ans)==g12.normalize(it['answer']))
                rows.append({'id':it['id'],'family':it['family'],'level':it['level'],'answer':ans,'gold':it['answer'],'correct':ok,
                             'confidence':mean_prob(r['logprobs']),'seconds':round(r['seconds'],3)})
        summ=g12.summarize(suite,rows)
        out['models'][cid]={'summary':summ,'mean_seconds':round(sum(r['seconds'] for r in rows)/len(rows),3),'rows':rows}
        print(cid,'overall',summ['overall'],'seen',summ['seen'],'unseen',summ['unseen'],'ece',summ['calibration']['ece'],flush=True)
    return out

# ---------------------------------------------------------------- pairs
# (a, b, contradiction 1/0, kind). Written to cover what the lexical proxy sees (numbers, negation) and what it misses
# (antonyms, entity swaps, paraphrase agreement with different wording or negation that agrees).
PAIRS=[
 ('The meeting starts at 9 am.','The meeting starts at 11 am.',1,'number'),
 ('The project budget is 120 euros.','The budget for the project is 150 euros.',1,'number'),
 ('Train 4 leaves from platform 2.','Train 4 departs from platform 7.',1,'number'),
 ('The total cost is 45 dollars.','Adding it up gives 45 dollars in total.',0,'number_same'),
 ('There are 3 apples left in the basket.','The basket still holds three apples.',0,'number_word'),
 ('The answer is 12.','12 is correct.',0,'number_same'),
 ('Paris is the capital of France.','Paris is not the capital of France.',1,'negation'),
 ('The file was saved successfully.','The file was not saved.',1,'negation'),
 ('The user wants a vegetarian recipe.','The user does not want meat in the recipe.',0,'negation_agree'),
 ('The battery is not full.','The battery still needs charging.',0,'negation_agree'),
 ('The road is closed today.','The road is open today.',1,'antonym'),
 ('The test passed.','The test failed.',1,'antonym'),
 ('The store is cheap.','The store is expensive.',1,'antonym'),
 ('Anna is older than Ben.','Ben is older than Anna.',1,'swap'),
 ('The meeting is with Lena from sales.','The meeting is with Tom from sales.',1,'entity'),
 ('The package goes to Berlin.','The package is shipped to Munich.',1,'entity'),
 ('The user asks for a short summary.','The goal is a brief overview of the text.',0,'paraphrase'),
 ('It will rain tomorrow.','Rain is expected tomorrow.',0,'paraphrase'),
 ('The function returns a list.','The function gives back a list of items.',0,'paraphrase'),
 ('The main constraint is the 100 euro budget.','The plan must stay within 100 euros.',0,'paraphrase'),
 ('The calculation is 7 * 8 = 56.','Seven times eight is fifty-six.',0,'number_word'),
 ('The calculation 7 * 8 = 54 is wrong.','7 * 8 = 56.',0,'negation_agree'),
 ('The cat sleeps on the sofa.','The dog barks in the garden.',0,'unrelated'),
 ('The deadline is Friday.','The report needs two charts.',0,'complementary'),
 ('The user lives in Hamburg.','The user works as a nurse.',0,'complementary'),
 ('The light is on.','The light is off.',1,'antonym'),
 ('The meeting was moved to Tuesday.','The meeting stays on Monday.',1,'entity'),
 ('The source says the bridge was built in 1890.','The bridge dates from 1890 according to the source.',0,'number_same'),
 ('The source says the bridge was built in 1890.','The bridge was built in 1920.',1,'number'),
 ('Water boils at 100 degrees Celsius at sea level.','At sea level water boils at 100 C.',0,'number_same'),
 ('The code has no bugs.','The code contains a bug in line 3.',1,'negation'),
 ('All tests pass.','Two tests fail.',1,'quantifier'),
 ('Nobody attended the event.','Many people came to the event.',1,'quantifier'),
 ('The answer is uncertain because the date is missing.','The date is not given, so the answer is unclear.',0,'hedge_agree'),
 ('The text asks for a plan.','The text asks for a comparison.',1,'entity'),
 ('Sum: 13 + 29 = 42.','13 + 29 equals 42.',0,'number_same'),
 ('Sum: 13 + 29 = 42.','13 + 29 equals 41.',1,'number'),
 ('The word reversed is elppa.','Backwards, apple is elppa.',0,'paraphrase'),
 ('The word reversed is elppa.','Backwards, apple is eppla.',1,'string'),
 ('The shortest path has 4 steps.','You need 6 steps on the shortest path.',1,'number'),
]
JUDGE_SYS='You check two statements. Reply with exactly one word: yes if they contradict each other, no if they do not.'
def judge_prob(s,a,b):
    r=s.chat([{'role':'system','content':JUDGE_SYS},{'role':'user','content':f'Statement A: {a}\nStatement B: {b}\nDo A and B contradict each other?'}],
             max_tokens=1,logprobs=True)
    top=(r['logprobs'][0].get('top_logprobs') if r['logprobs'] else []) or []
    py=sum(math.exp(t['logprob']) for t in top if t['token'].strip().lower().startswith('yes'))
    pn=sum(math.exp(t['logprob']) for t in top if t['token'].strip().lower().startswith('no'))
    return (py/(py+pn) if py+pn else .5),r['seconds']
def run_pairs(a):
    labels=[p[2] for p in PAIRS];res={'n':len(PAIRS),'positives':sum(labels),'detectors':{}}
    lex=[focal.disagreement(x,y) for x,y,_,_ in PAIRS]
    res['detectors']['lexical_focal']={'auroc':auroc(lex,labels),'best':best_threshold(lex,labels),
        'at_boot':at_threshold(lex,labels,focal.BOOT['disagreement_trigger']),'scores':lex}
    for cid in a.judges:
        with Server(cid,a) as s:
            sc=[];sec=[]
            for x,y,_,_ in PAIRS:p,t=judge_prob(s,x,y);sc.append(round(p,4));sec.append(t)
        res['detectors']['judge_'+cid]={'auroc':auroc(sc,labels),'best':best_threshold(sc,labels),'at_0.5':at_threshold(sc,labels,.5),
            'mean_seconds':round(sum(sec)/len(sec),3),'scores':sc}
        # combination: max(lexical, judge) keeps the cheap proxy's hits
        comb=[max(l,j) for l,j in zip(lex,sc)]
        res['detectors']['max_lexical_judge_'+cid]={'auroc':auroc(comb,labels),'best':best_threshold(comb,labels),'scores':comb}
        print(cid,'judge auroc',res['detectors']['judge_'+cid]['auroc'],flush=True)
    if 'embeddinggemma_300m' not in a.skip:
        with Server('embeddinggemma_300m',a,['--embedding']) as s:
            sc=[]
            for x,y,_,_ in PAIRS:
                e=s.embed([x,y]);sc.append(round(cc.cos(e[0],e[1]),4))
        res['detectors']['embedding_cosine']={'auroc':auroc(sc,labels),'best':best_threshold(sc,labels),'scores':sc}
    kinds={}
    for (x,y,l,k),s in zip(PAIRS,lex):kinds.setdefault(k,[]).append({'label':l,'lexical':s})
    res['by_kind']=kinds;res['pairs']=[{'a':x,'b':y,'label':l,'kind':k} for x,y,l,k in PAIRS]
    print('lexical auroc',res['detectors']['lexical_focal']['auroc'],flush=True)
    return res

# ---------------------------------------------------------------- offers
B1_INS=('You are an internal detail analyst. Check exact details, calculations and contradictions. Return JSON only. summary is a short '
        'hypothesis, NOT a final user answer. quotes must be exact substrings of the supplied source. Use at most two short quotes. '
        'uncertainty is concise. needs_reentry indicates a material unresolved issue. Keep all fields short.')
B2_INS=B1_INS.replace('detail analyst. Check exact details, calculations and contradictions.','gist analyst. Identify the main goal, constraints and broader context.')
def checkable(n_per_family=4):
    """Checkable tasks: AG12 items (first n per family, levels mixed) + short reading tasks with a fact answer."""
    suite=g12.build_suite(lang='en');fam={}
    for it in suite['items']:fam.setdefault(it['family'],[]).append(it)
    items=[{'id':x['id'],'kind':x['family'],'text':x['prompt'],'gold':x['answer']} for v in fam.values() for x in v[::max(1,len(v)//n_per_family)][:n_per_family]]
    reading=[('The order has 3 boxes with 12 pens each. How many pens are in the order?','36'),
             ('Lena paid 45 euros and Tom paid 30 euros. How much did they pay together?','75'),
             ('The train leaves at 14:10 and the trip takes 50 minutes. At what time does it arrive?','15:00'),
             ('Project Aurora has a budget of 120 euros and has spent 85. How much is left?','35'),
             ('Anna is 31. Ben is 4 years younger than Anna. How old is Ben?','27'),
             ('A recipe needs 250 g flour per cake. How many grams for 3 cakes?','750'),
             ('The meeting is on Monday. It was moved two days later. Which day is it now?','wednesday'),
             ('Mia has 5 apples, eats 2 and buys 6 more. How many apples does she have?','9'),
             ('What is the capital of Australia?','canberra'),
             ('How many legs does a spider have?','8'),
             ('Which planet is closest to the sun?','mercury'),
             ('What is 15 percent of 200?','30')]
    return items+[{'id':f'read{i}','kind':'reading','text':t,'gold':g} for i,(t,g) in enumerate(reading)]
def contains(text,gold):
    t=' '.join(re.sub(r'[^\w:]+',' ',(text or '').casefold()).split());g=gold.casefold()
    return int(re.search(r'(?<![\w])'+re.escape(g)+r'(?![\w])',t) is not None)
B1_SOLVE=B1_INS.replace('summary is a short hypothesis, NOT a final user answer.','summary is a short hypothesis that states the exact result you computed or found (another component writes the user answer).')
RUNNER_SAMPLING={'temperature':.1,'top_k':50,'repeat_penalty':1.05}  # runners.LlamaRunner payload for offers (cfg temperature .1)
def style_name(st):return 'hypothesis' if st=='boot' else st
def offer(s,ins,text,native=True):
    q={'source_segments':[{'text':text[i:i+240]} for i in range(0,len(text),240)],'peer_message':None,'prior_hypothesis':''}
    msgs=[{'role':'system','content':ins},{'role':'user','content':json.dumps(q)}]
    if native:
        r=s.native(msgs,max_tokens=160,schema=OFFER_SCHEMA,n_probs=1,**RUNNER_SAMPLING);tc=focal.token_confidence(r['pairs'])
    else:
        r=s.chat(msgs,max_tokens=160,schema=OFFER_SCHEMA,logprobs=True);tc=focal.token_confidence([(x.get('token',''),x['logprob']) for x in r['logprobs']])
    try:obj=json.loads(r['text'])
    except Exception:obj={'summary':r['text'][:200],'quotes':[],'uncertainty':'invalid json','needs_reentry':True,'_invalid':True}
    refs=[q for q in obj.get('quotes',[]) if isinstance(q,str) and q and q in text]
    p={'offer':obj,'evidence_refs':refs,'rejected_quotes':len(obj.get('quotes',[]))-len(refs)}
    return {'offer':obj,'valid_quotes':len(refs),'rejected_quotes':p['rejected_quotes'],'focal_uncertainty_legacy':focal.offer_uncertainty(p),
            'focal_uncertainty':focal.offer_uncertainty(p|{'native_metrics':{'token_confidence':tc}}),'token_confidence':tc,
            'token_conf':tc['mean_prob'] or 0.,'seconds':round(r['seconds'],3),'gen_tokens':r['timings'].get('predicted_n'),
            'correct':contains(obj.get('summary',''),'')}
def run_offers(a):
    items=checkable();rows={x['id']:dict(x) for x in items};st=style_name(a.offer_style)
    for role,cid,pol in (('B1',a.b1,'B1_DETAIL'),('B2',a.b2,'B2_GIST')):
        with Server(cid,a) as s:
            for x in items:
                o=offer(s,offer_instructions(pol,st),x['text']);o['correct']=contains(o['offer'].get('summary',''),x['gold']);rows[x['id']][role]=o
        print(role,cid,'done',flush=True)
    R=list(rows.values());res={'b1':a.b1,'b2':a.b2,'offer_style':st,'path':'native /completion, runner sampling, raw logprobs','token_unc':focal.TOKEN_UNC,'n':len(R),'rows':R,'per_role':{}}
    for role in ('B1','B2'):
        err=[1-r[role]['correct'] for r in R]
        tcv=lambda k:[1-(r[role]['token_confidence'].get(k) if r[role]['token_confidence'].get(k) is not None else 1.) for r in R]
        fu=[r[role]['focal_uncertainty'] for r in R];fl=[r[role]['focal_uncertainty_legacy'] for r in R]
        nr=[float(r[role]['offer'].get('needs_reentry') is True) for r in R]
        hedge=[float(bool(focal.HEDGE.search(r[role]['offer'].get('uncertainty','') or '')) and not focal.CALM.search(r[role]['offer'].get('uncertainty','') or '')) for r in R]
        sec=sorted(r[role]['seconds'] for r in R)
        res['per_role'][role]={'accuracy':round(1-sum(err)/len(R),4),'invalid_json':sum(1 for r in R if r[role]['offer'].get('_invalid')),
            'auroc_error':{'focal_offer_uncertainty':auroc(fu,err),'focal_legacy_text':auroc(fl,err),'tok_mean':auroc(tcv('mean_prob'),err),
                           'tok_field_mean':auroc(tcv('field_mean_prob'),err),'tok_field_min':auroc(tcv('field_min_prob'),err),
                           'needs_reentry':auroc(nr,err),'hedge_regex':auroc(hedge,err)},
            'needs_reentry_rate':round(sum(nr)/len(R),4),'hedge_rate':round(sum(hedge)/len(R),4),
            'best':{k:best_threshold(tcv(k),err) for k in ('mean_prob','field_mean_prob','field_min_prob')},
            'at_boot_uncertainty_trigger':{'new':at_threshold(fu,err,focal.BOOT['uncertainty_trigger']),'legacy':at_threshold(fl,err,focal.BOOT['uncertainty_trigger'])},
            'seconds':{'p50':sec[len(sec)//2],'p90':sec[int(len(sec)*.9)],'max':sec[-1],'mean':round(sum(sec)/len(sec),3)}}
        print(role,json.dumps(res['per_role'][role]['auroc_error']),'acc',res['per_role'][role]['accuracy'],flush=True)
    lab=[int(r['B1']['correct']!=r['B2']['correct']) for r in R]
    dis=[focal.disagreement(r['B1']['offer'].get('summary',''),r['B2']['offer'].get('summary','')) for r in R]
    res['pair_disagreement']={'positives':sum(lab),'auroc':auroc(dis,lab),'best':best_threshold(dis,lab),
                              'at_boot':at_threshold(dis,lab,focal.BOOT['disagreement_trigger']),'scores':dis}
    return res

# ---------------------------------------------------------------- effort
SMALLTALK=['Hi there!','Thanks, that helps.','Good morning, how are you?','Okay, see you later.','Tell me a fun fact about cats.',
           'What is your name?','Nice, thank you!','Can you say hello to my friend?']
C3_SYS='You are a helpful assistant. Answer briefly. For tasks with one result, give only the result.'
def run_effort(a):
    items=checkable();res={'offer_style':a.offer_style,'c3':a.c3,'b1':a.b1,'cases':[]}
    offers={}
    with Server(a.b1,a) as s:
        for x in items:offers[x['id']]=offer(s,B1_SOLVE if a.offer_style=='solve' else B1_INS,x['text'])
    with Server(a.c3,a) as s:
        for x in items:
            alone=s.chat([{'role':'system','content':C3_SYS},{'role':'user','content':x['text']}],max_tokens=32)
            hint=offers[x['id']]['offer'].get('summary','')
            helped=s.chat([{'role':'system','content':C3_SYS+' An internal analyst hypothesis is given; it may be wrong.'},
                           {'role':'user','content':x['text']+'\n\n[internal hypothesis] '+hint}],max_tokens=32)
            ca,ch=contains(alone['text'],x['gold']),contains(helped['text'],x['gold'])
            res['cases'].append({'id':x['id'],'kind':x['kind'],'text':x['text'],'c3_alone':ca,'c3_with_b1':ch,
                                 'need':'detail' if (ch and not ca) else 'none','b1_correct':contains(hint,x['gold']),
                                 'c3_seconds':round(alone['seconds'],3),'b1_seconds':offers[x['id']]['seconds']})
    for t in SMALLTALK:res['cases'].append({'id':'talk','kind':'smalltalk','text':t,'need':'none'})
    C=res['cases'];chk=[c for c in C if c['kind']!='smalltalk']
    res['summary']={'c3_alone_acc':round(sum(c['c3_alone'] for c in chk)/len(chk),4),'c3_with_b1_acc':round(sum(c['c3_with_b1'] for c in chk)/len(chk),4),
                    'helped':sum(c['need']=='detail' for c in C),'hurt':sum(c['c3_alone'] and not c['c3_with_b1'] for c in chk),
                    'b1_acc':round(sum(c['b1_correct'] for c in chk)/len(chk),4)}
    res['sweep']=sweep_effort(C)
    return res
def policy_cost(cases,p,cost_body=1.,cost_miss=3.):
    miss=over=0;spent=0.
    for c in cases:
        sig=effort.signals(c['text'],scaffold_route(c['text']))
        plan=effort.constrain(effort.plan_for(effort.adaptive_effort(sig,p),sig,p),p=p)
        woke=plan['wake'] in ('detail','both');need=c['need']=='detail'
        spent+=len(effort.roles(plan['wake']))*cost_body;miss+=need and not woke;over+=(not need) and woke
    n=len(cases);hard=sum(c['need']=='detail' for c in cases)
    return {'miss':miss,'over':over,'hard':hard,'easy':n-hard,'cost':round((spent+cost_miss*miss)/n,4),
            'underthinking':round(miss/hard,4) if hard else None,'overthinking':round(over/(n-hard),4) if n-hard else None}
def sweep_effort(cases):
    base=dict(effort.BOOT);out={'boot':policy_cost(cases,base),'grid':[]}
    for eu,ec,ob,dg in itertools.product((.35,.45,.55),(.30,.40,.50),(.25,.35,.45,.55),(.2,.4,.6)):
        p=base|{'escalate_uncertainty':eu,'escalate_conflict':ec,'one_body_need':ob,'default':base['default']}
        p['conflict_gain']=base['conflict_gain'];r=policy_cost(cases,p)|{'escalate_uncertainty':eu,'escalate_conflict':ec,'one_body_need':ob}
        out['grid'].append(r)
    out['grid'].sort(key=lambda r:(r['cost'],r['miss']));out['best']=out['grid'][:5];out['grid']=out['grid'][:40]
    return out

# ---------------------------------------------------------------- effort_rt
# Runtime-faithful: C3 sees the real system prompt (prompts.py) and offers as 'Internal hypotheses: [offer JSON]' like
# runtime.py, decoded with the runtime C3 sampler (anti-echo C3_DECODER or legacy). Variants per task: alone/+B1/+B2/+both.
def c3_messages(text,offers,rules=None,memories=None):
    cfg={'answer_language':'en'};sys_=rt_prompt(cfg,'system')+' '+rt_prompt(cfg,'conduct')+' '+(rt_prompt(cfg,'answer_rules') if rules is None else rules)
    if memories:sys_+='\n'+rt_prompt(cfg,'memories')+json.dumps(memories,ensure_ascii=False)
    if offers:sys_+='\n'+rt_prompt(cfg,'hypotheses')+json.dumps(offers,ensure_ascii=False)
    return [{'role':'system','content':sys_},{'role':'user','content':text}]
def c3_sampling(decoder):
    base={'temperature':.1,'top_k':50,'repeat_penalty':1.05}
    return base|C3_DECODER if decoder=='anti_echo' else base
WAKE_VARIANTS={'none':(),'detail':('B1',),'gist':('B2',),'both':('B1','B2')}
def run_effort_rt(a):
    items=checkable();st=style_name(a.offer_style);cache=a.out/f'effort_rt_offers_{st}.json'
    if cache.exists():offers=json.loads(cache.read_text())  # same bodies/prompt: reuse instead of re-running B1/B2
    else:
        offers={'B1':{},'B2':{}}
        for role,cid,pol in (('B1',a.b1,'B1_DETAIL'),('B2',a.b2,'B2_GIST')):
            with Server(cid,a) as s:
                for x in items:offers[role][x['id']]=offer(s,offer_instructions(pol,st),x['text'])
        cache.write_text(json.dumps(offers))
    res={'offer_style':st,'b1':a.b1,'b2':a.b2,'seeds':a.seeds,'c3':{}}
    for cid in a.c3_candidates:
        with Server(cid,a) as s:
            for dec in a.decoders:
                cases=[]
                for x in items:
                    row={'id':x['id'],'kind':x['kind'],'text':x['text'],'gold':x['gold'],'out':{},'answers':{},
                         'b1_correct':contains(offers['B1'][x['id']]['offer'].get('summary',''),x['gold']),'b2_correct':contains(offers['B2'][x['id']]['offer'].get('summary',''),x['gold'])}
                    for wake,rs in WAKE_VARIANTS.items():
                        ok=0;ans=[]
                        for seed in a.seeds:
                            r=s.native(c3_messages(x['text'],[offers[r_][x['id']]['offer'] for r_ in rs]),max_tokens=48,seed=seed,**c3_sampling(dec))
                            ok+=contains(r['text'],x['gold']);ans.append(r['text'][:120])
                        row['out'][wake]=round(ok/len(a.seeds),4);row['answers'][wake]=ans
                    cases.append(row)
                acc={w:round(sum(c['out'][w] for c in cases)/len(cases),4) for w in WAKE_VARIANTS}
                oracle=round(sum(max(c['out'].values()) for c in cases)/len(cases),4)
                helped={w:sum(c['out'][w]>c['out']['none'] for c in cases) for w in WAKE_VARIANTS if w!='none'}
                hurt={w:sum(c['out'][w]<c['out']['none'] for c in cases) for w in WAKE_VARIANTS if w!='none'}
                res['c3'][f'{cid}:{dec}']={'accuracy':acc,'oracle_wake':oracle,'helped':helped,'hurt':hurt,'sweep':sweep_effort_rt(cases),'cases':cases}
                print(cid,dec,'acc',acc,'oracle',oracle,'helped',helped,'hurt',hurt,flush=True)
    return res
def policy_eval(cases,p):
    acc=bodies=0.;wakes={}
    for c in cases:
        sig=effort.signals(c['text'],scaffold_route(c['text']))
        w=effort.constrain(effort.plan_for(effort.adaptive_effort(sig,p),sig,p),p=p)['wake']
        acc+=c['out'][w];bodies+=len(effort.roles(w));wakes[w]=wakes.get(w,0)+1
    n=len(cases);return {'accuracy':round(acc/n,4),'bodies_per_turn':round(bodies/n,4),'wakes':wakes}
def sweep_effort_rt(cases):
    base=dict(effort.BOOT);out={'boot':policy_eval(cases,base),'fixed':{w:{'accuracy':round(sum(c['out'][w] for c in cases)/len(cases),4),'bodies_per_turn':len(effort.roles(w))} for w in WAKE_VARIANTS},'grid':[]}
    for eu,ec,ob in itertools.product((.35,.45,.55),(.30,.40,.50),(.25,.35,.45,.55)):
        p=base|{'escalate_uncertainty':eu,'escalate_conflict':ec,'one_body_need':ob}
        out['grid'].append(policy_eval(cases,p)|{'escalate_uncertainty':eu,'escalate_conflict':ec,'one_body_need':ob})
    out['grid'].sort(key=lambda r:(-r['accuracy'],r['bodies_per_turn']));out['best']=out['grid'][:5]
    out['distinct_outcomes']=sorted({(r['accuracy'],r['bodies_per_turn']) for r in out['grid']});out['grid']=out['grid'][:20]
    return out

# ---------------------------------------------------------------- rules
# C3 answer_rules variants under the runtime prompt: task accuracy (alone / +B1), abstention on unsupported questions,
# use of a stored correction (memory-retrieval acceptance shape) and benchmark_c3 EN fixtures.
BASE_RULES="Do not repeat the question. At most two verbatim quotes; on conflict the user's version wins."
RULES={'current':None,'no_abstain':BASE_RULES,
       'dont_know':BASE_RULES+" If the question asks for a fact you were not given, say that you do not know it.",
       'answer_first':BASE_RULES+" Always give your best answer first. If a needed fact was not given, add that it is not verified."}
UNSUPPORTED=['Who leads Project Aurora?','What is the name of my sister?','What did I eat for breakfast yesterday?','What is the PIN of my locker?',
             'Which room is my next meeting in?','How old is my neighbour Tom?']
ABSTAIN=re.compile(r"not sure|don'?t know|do not know|unknown|not verified|nothing verified|no information|not (?:been )?(?:provided|given|mentioned)|cannot|can'?t|unable|no (?:data|record)",re.I)
MEM_CASES=[({'topic':'Project Kelmo16 budget','correction':'400 euros','matched_query':'Project Kelmo16: financial frame?'},'Project Kelmo16: financial frame?','400'),
           ({'topic':'Project Kelmo5 date','correction':'Project Kelmo5: 6 May','matched_query':'Project Kelmo5: when is the deadline?'},'Project Kelmo5: when is the deadline?','6 may'),
           ({'topic':'Project Kelmo2 lead','correction':'Project Kelmo2: Ms Berg2','matched_query':'Project Kelmo2: who is responsible?'},'Project Kelmo2: who is responsible?','berg2'),
           ({'topic':'Project Kelmo3 place','correction':'Project Kelmo3: Berlin, Weg 4','matched_query':'Project Kelmo3: where does it take place?'},'Project Kelmo3: where does it take place?','berlin'),
           ({'topic':'favourite colour','correction':'My favourite colour is teal.','matched_query':'What is my favourite colour?'},'What is my favourite colour?','teal')]
def run_rules(a):
    import importlib.util as u
    sp=u.spec_from_file_location('b',APP/'scripts/benchmark_c3.py');b=u.module_from_spec(sp);sp.loader.exec_module(b)
    fx=[f for f in b.FIXTURES if f.get('lang')=='en'];items=checkable();st=style_name(a.offer_style)
    cache=a.out/f'effort_rt_offers_{st}.json';offers=json.loads(cache.read_text()) if cache.exists() else None
    res={'seeds':a.seeds,'rules':{k:v for k,v in RULES.items()},'models':{}}
    for cid in a.c3_candidates:
        with Server(cid,a) as s:
            m={}
            for name,rules in RULES.items():
                if a.rules and name not in a.rules:continue
                for dec in a.decoders:
                    samp=c3_sampling(dec);r={'task_alone':0,'task_b1':0,'abstain':0,'memory':0,'fixtures':0,'examples':[]};n=len(a.seeds)
                    for seed in a.seeds:
                        for x in items:
                            r['task_alone']+=contains(s.native(c3_messages(x['text'],[],rules),max_tokens=48,seed=seed,**samp)['text'],x['gold'])
                            if offers:r['task_b1']+=contains(s.native(c3_messages(x['text'],[offers['B1'][x['id']]['offer']],rules),max_tokens=48,seed=seed,**samp)['text'],x['gold'])
                        for q in UNSUPPORTED:
                            t=s.native(c3_messages(q,[],rules),max_tokens=48,seed=seed,**samp)['text'];r['abstain']+=bool(ABSTAIN.search(t))
                            if seed==a.seeds[0]:r['examples'].append(('unsupported',q,t[:120]))
                        for mem,q,gold in MEM_CASES:
                            t=s.native(c3_messages(q,[],rules,[mem]),max_tokens=48,seed=seed,**samp)['text'];r['memory']+=contains(t,gold)
                            if seed==a.seeds[0]:r['examples'].append(('memory',q,t[:120]))
                        for f in fx:
                            t=s.native(c3_messages(f['user'],[],rules),max_tokens=96,seed=seed,**samp)['text'];c=b.lexical_checks(t,f);r['fixtures']+=bool(c) and all(c.values())
                    out={'task_alone':round(r['task_alone']/(n*len(items)),4),'task_b1':round(r['task_b1']/(n*len(items)),4) if offers else None,
                         'abstain_unsupported':round(r['abstain']/(n*len(UNSUPPORTED)),4),'memory_use':round(r['memory']/(n*len(MEM_CASES)),4),
                         'fixtures_en':round(r['fixtures']/(n*len(fx)),4),'examples':r['examples']}
                    m[f'{name}:{dec}']=out;print(cid,name,dec,{k:v for k,v in out.items() if k!='examples'},flush=True)
            res['models'][cid]=m
    return res

# ---------------------------------------------------------------- echo
OPEN=['Explain in two sentences how a local assistant can remember corrections.','What are three steps to plan a small garden on a balcony?',
      'Compare trains and buses for a 50 km daily commute.','Why does a phone get warm when it runs a language model?',
      'Describe what a good morning routine looks like.','How can I learn a new language with only ten minutes a day?',
      'What should I check before buying a used bicycle?','Summarize why sleep matters for memory.']
DECODERS={'legacy':{'temperature':.7,'top_k':50,'repeat_penalty':1.05},
          'anti_echo_boot':C3_DECODER,
          'anti_echo_no_dry':C3_DECODER|{'dry_multiplier':0.},
          'anti_echo_rp115':C3_DECODER|{'repeat_penalty':1.15},
          'anti_echo_t07':C3_DECODER|{'temperature':.7},
          'anti_echo_t05_dry12':C3_DECODER|{'temperature':.5,'dry_multiplier':1.2}}
def run_echo_exact(a):
    """Does a stronger repeat penalty cost exactness? C3 fixtures (EN) + AG12 arithmetic/seq items, each decoder, 3 seeds."""
    import importlib.util as u
    sp=u.spec_from_file_location('b',APP/'scripts/benchmark_c3.py');b=u.module_from_spec(sp);sp.loader.exec_module(b)
    fx=[f for f in b.FIXTURES if f.get('lang')=='en'];items=[i for i in g12.build_suite(lang='en')['items'] if i['family'] in ('arith_add','arith_mul','seq_next')]
    res={'models':{}}
    for cid in a.c3_candidates:
        with Server(cid,a) as s:
            m={}
            for name in ('legacy','anti_echo_boot','anti_echo_rp115'):
                checks=total=ok=0
                for seed in (13,21,34):
                    for f in fx:
                        d=dict(DECODERS[name]);r=s.chat([{'role':'system','content':f['system']},{'role':'user','content':f['user']}],max_tokens=96,seed=seed,temperature=d.pop('temperature',.6),**d)
                        c=b.lexical_checks(r['text'],f);checks+=bool(c) and all(c.values());total+=1
                    for it in items:
                        d=dict(DECODERS[name]);r=s.chat([{'role':'system','content':SYS_AG12},{'role':'user','content':it['prompt']}],max_tokens=24,seed=seed,temperature=d.pop('temperature',.6),**d)
                        ok+=g12.normalize(extract(r['text']))==g12.normalize(it['answer'])
                m[name]={'fixture_pass':round(checks/total,4),'fixture_n':total,'ag12_exact_acc':round(ok/(3*len(items)),4),'ag12_n':3*len(items)}
            res['models'][cid]=m;print(cid,m,flush=True)
    return res

def run_echo(a):
    res={'models':{}}
    for cid in a.c3_candidates:
        with Server(cid,a) as s:
            m={}
            for name,dec in DECODERS.items():
                rows=[]
                for q,seed in itertools.product(OPEN,(13,21,34)):
                    d=dict(dec);r=s.chat([{'role':'system','content':'You are a helpful assistant. Answer in English.'},{'role':'user','content':q}],
                                         max_tokens=128,seed=seed,temperature=d.pop('temperature',.6),**d)
                    rows.append(turn_metrics(r['text'],q)|{'chars':len(r['text'])})
                n=len(rows);mean=lambda k:round(sum(float(x[k]) for x in rows)/n,4)
                m[name]={'n':n,'query_echo':mean('query_echo'),'repetition_rate':mean('repetition_rate'),'type_token_ratio':mean('type_token_ratio'),
                         'below_min_new':sum(1 for x in rows if x.get('below_min_new')),'mean_chars':mean('chars')}
            res['models'][cid]=m;print(cid,json.dumps(m)[:400],flush=True)
    return res

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--home',type=Path,required=True);ap.add_argument('--cache',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('exp',nargs='+',choices=['ag12','pairs','offers','effort','effort_rt','rules','echo','echo_exact'])
    ap.add_argument('--offer-style',choices=['boot','hypothesis','solve'],default='solve')
    ap.add_argument('--seeds',nargs='*',type=int,default=[13]);ap.add_argument('--decoders',nargs='*',default=['anti_echo','legacy']);ap.add_argument('--rules',nargs='*',default=[]);ap.add_argument('--tag',default='')
    ap.add_argument('--models',nargs='*',default=CHAT);ap.add_argument('--judges',nargs='*',default=['qwen35_0p8b','lfm25_1p2b_body','lfm25_350m'])
    ap.add_argument('--b1',default='lfm25_1p2b_body');ap.add_argument('--b2',default='qwen35_0p8b');ap.add_argument('--c3',default='lfm25_230m_c3')
    ap.add_argument('--c3-candidates',nargs='*',default=['lfm25_230m_c3','lfm25_350m']);ap.add_argument('--skip',nargs='*',default=[])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);a.cache.mkdir(parents=True,exist_ok=True)
    for e in a.exp:
        t0=time.monotonic();r={'ag12':run_ag12,'pairs':run_pairs,'offers':run_offers,'effort':run_effort,'effort_rt':run_effort_rt,'rules':run_rules,'echo':run_echo,'echo_exact':run_echo_exact}[e](a)
        r|={'experiment':e,'seconds':round(time.monotonic()-t0,1),'cpu':os.cpu_count(),'claim':'cloud x86 CPU, not Redmi; English only'}
        (a.out/f'{e}{a.tag}.json').write_text(json.dumps(r,indent=1,ensure_ascii=False));print('wrote',e+a.tag,flush=True)

if __name__=='__main__':main()
