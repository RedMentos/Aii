#!/usr/bin/env python3
"""WP-G G1B utility with a real B2: does the Age-0 gist view (gist.plan: ~8 token-equivalent groups, 12 slots, older parts
coarser) help the B2 gist analyst compared with today's 960-char fixed segments and the WP-N8 event segments?

All three views carry the whole source text (lossless); they differ only in how it is cut and how old parts are merged.
B2 = Qwen3.5-0.8B Q4_0 (pinned), llama-server b10964, thinking off, temperature 0, OFFER_SCHEMA JSON, the same B2 instruction
text as cognition.offer (offer_instructions('B2_GIST') + the gist_slots sentence when that view is used).
Corpus: 36 deterministic project memos (2.2-2.8k chars) with one early fact (owner), one middle fact (budget) and one late
revision (deadline moved from X to Y); one question per memo, the three question kinds rotate.
Metrics per arm: answer hit (key in summary; for the revision: new value Y), stale answer (old X without Y), all quotes exact
substrings, a quote containing the key, prompt tokens, seconds. Paired per memo.
Preregistered decision (code/docs/proofs/gist-utility-20261012/preregistration.json): GIST_HELPS_CANDIDATE only if gist vs
fixed960 has paired hit wins > losses AND quote validity not lower AND prompt tokens not more than 10 % higher; else GIST_NO_GAIN.
Nothing is activated (`:gist` stays SHADOW); runtime modules are imported read-only.
  python3 scripts/gist_utility_bench.py --home HOME --out DIR"""
import argparse,json,random,socket,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13 import gist as G  # noqa: E402
from v13.cognition import segments,offer_instructions,OFFER_SCHEMA  # noqa: E402
from v13.common import atomic_write,dumps,digest,file_hash  # noqa: E402

SEED=20261012;N=36
NAMES=['Ingrid Solberg','Tomasz Wrona','Amara Okafor','Lucien Daventry','Mei Tanaka','Rafael Quintero','Ylva Berg','Kofi Mensah','Hana Novak']
PROJECTS=['the warehouse migration','the clinic booking app','the river cleanup','the school library refit','the solar roof pilot','the bakery expansion']
DATES=['March 3','April 17','May 22','June 9','July 28','August 14','September 30','October 21','November 6','December 12']
FILLER=['The team reviewed the open tickets and agreed to keep the weekly sync short.','Several people asked for clearer notes, so the minutes now follow a fixed template.',
 'A supplier sent a revised quote, which is still being compared with the old one.','The meeting room on the second floor will be closed for painting next week.',
 'Two volunteers offered to help with testing on weekends.','The shared drive was reorganised and old drafts were moved to an archive folder.',
 'Feedback from the last workshop was mostly positive, with some concerns about the pace.','Someone suggested a short demo for the neighbourhood association.',
 'The printer issue was fixed after the cable was replaced.','Lunch on Friday will be provided by the canteen as usual.',
 'There was a long discussion about naming conventions without a final decision.','The risk list was updated, mainly with minor items.',
 'A new intern joins the group and will shadow the coordinator for a month.','The old laptops will be donated once the data has been wiped.',
 'Travel costs for the site visit were approved without changes.','The safety briefing has to be repeated for everyone who missed it.']
KINDS=('owner','budget','deadline')

def make(seed=SEED):
    rnd=random.Random(seed);rows=[]
    for i in range(N):
        proj=rnd.choice(PROJECTS);owner=rnd.choice(NAMES);budget=rnd.randrange(12,98)*1000+rnd.choice([250,500,750])
        x,y=rnd.sample(DATES,2);kind=KINDS[i%3];fill=FILLER[:];rnd.shuffle(fill);k=rnd.randint(26,36)
        filler=[fill[j%len(fill)] for j in range(k)]
        a,b=len(filler)//3,2*len(filler)//3
        parts=[f'Memo about {proj}.',f'The person responsible for {proj} is {owner}, who signs off every change.']+filler[:a]+\
              [f'The approved budget for {proj} is {budget} euros, including a small reserve.']+filler[a:b]+[f'The original deadline was {x}.']+filler[b:]+\
              [f'Correction from the steering group: the deadline is moved from {x} to {y}, and {x} no longer applies.','End of memo.']
        text=' '.join(parts)
        q={'owner':f'Who is responsible for {proj}?','budget':f'What is the approved budget for {proj}?','deadline':f'What is the current deadline for {proj}?'}[kind]
        key={'owner':owner.split()[-1],'budget':str(budget),'deadline':y}[kind]
        rows.append({'text':text,'question':q,'kind':kind,'key':key,'stale':x if kind=='deadline' else None})
    return rows

def views(text):
    ref={'source_id':'bench','sha256':'0'*64,'char_start':0,'char_end':len(text),'modality':'text'}
    p=G.plan(text,ref,{'tokens_per_group':8,'slots':12})
    return {'fixed960':('source_segments',segments(text,ref,960,'fixed')),'event960':('source_segments',segments(text,ref,960,'event')),
            'gist':('gist_slots',[{'slot':x['slot'],'text':x['text'],'source_ref':x['source_ref'],'scale':x['scale']} for x in p['slots']])}

def serve(home,model,port,log):
    p=subprocess.Popen([str(home/'bin/llama-server'),'-m',str(model),'--port',str(port),'-c','8192','-t','4','-np','1','--no-webui','--no-warmup'],stdout=subprocess.DEVNULL,stderr=open(log,'a'))
    for _ in range(180):
        try:
            if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2).read()).get('status')=='ok':return p
        except Exception:time.sleep(1)
    p.terminate();raise RuntimeError('server did not start')

def ask(port,system,user):
    b=json.dumps({'messages':[{'role':'system','content':system},{'role':'user','content':user}],'max_tokens':220,'temperature':0,'seed':13,'cache_prompt':False,
                  'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_schema','json_schema':{'schema':OFFER_SCHEMA}}}).encode()
    t=time.monotonic();r=json.loads(urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',b,{'Content-Type':'application/json'}),timeout=600).read())
    return r['choices'][0]['message']['content'],r['usage']['prompt_tokens'],time.monotonic()-t

def score(row,content):
    try:o=json.loads(content)
    except Exception:return {'parsed':False,'hit':False,'stale':False,'quotes_valid':False,'quote_has_key':False}
    s=str(o.get('summary',''));qs=[str(q) for q in (o.get('quotes') or [])];low=s.lower();key=row['key'].lower()
    hit=key in low;stale=bool(row['stale']) and row['stale'].lower() in low and not hit
    return {'parsed':True,'hit':hit,'stale':stale,'quotes_valid':all(q in row['text'] for q in qs),'quote_has_key':any(key in q.lower() and q in row['text'] for q in qs),'n_quotes':len(qs)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--home',required=True);ap.add_argument('--out',required=True);ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    home,out=Path(a.home),Path(a.out);out.mkdir(parents=True,exist_ok=True);model=next((home/'models/gist').glob('*.gguf'));rows=make()
    binding={'script_sha256':file_hash(__file__),'gist_sha256':file_hash(Path(G.__file__)),'cognition_sha256':file_hash(Path(G.__file__).parent/'cognition.py'),
             'episodes_sha256':file_hash(Path(G.__file__).parent/'episodes.py'),'model_sha256':file_hash(model),'runner_sha256':file_hash(home/'bin/llama-server'),
             'corpus_sha256':digest(dumps(rows))}
    target=out/'report.json'
    if target.exists() and not a.resume:raise SystemExit('report exists; use --resume')
    rep=json.loads(target.read_text()) if target.exists() else {}
    if rep and rep.get('binding')!=binding:raise SystemExit('binding differs')
    rep.update(kind='V13_G1B_GIST_UTILITY',binding=binding,claim_limit='Linux x86_64 cloud CPU, not Redmi; synthetic memos; one greedy JSON offer per memo; B2 offer only (no C3 answer, no B1, no re-entry); gist stays SHADOW')
    save=lambda:atomic_write(target,json.dumps(rep,indent=1,ensure_ascii=False))
    save();port=8830;p=serve(home,model,port,out/'server.log')
    try:
        for arm in ('fixed960','event960','gist'):
            res=rep.setdefault(arm,[]);done={r['index'] for r in res}
            for i,row in enumerate(rows):
                if i in done:continue
                field,view=views(row['text'])[arm];ins=offer_instructions('B2_GIST')
                if field=='gist_slots':ins+=' gist_slots are exact source groups in order (older parts are coarser); quotes must be exact substrings of them.'
                content,nt,sec=ask(port,ins,dumps({'user_message':row['question'],field:view}))
                res.append({'index':i,'kind':row['kind'],'content':content,'prompt_tokens':nt,'seconds':round(sec,3),'n_view':len(view)}|score(row,content));save()
            print(arm,'done',flush=True)
    finally:p.terminate();p.wait()
    summ={}
    for arm in ('fixed960','event960','gist'):
        r=rep[arm];n=len(r);summ[arm]={'hit':round(sum(x['hit'] for x in r)/n,4),'stale':sum(x['stale'] for x in r),'parsed':sum(x['parsed'] for x in r),
            'quotes_valid':round(sum(x['quotes_valid'] for x in r)/n,4),'quote_has_key':round(sum(x['quote_has_key'] for x in r)/n,4),
            'prompt_tokens_mean':round(sum(x['prompt_tokens'] for x in r)/n,1),'seconds_mean':round(sum(x['seconds'] for x in r)/n,2),'view_items_mean':round(sum(x['n_view'] for x in r)/n,2),
            'hit_by_kind':{k:round(sum(x['hit'] for x in r if x['kind']==k)/sum(1 for x in r if x['kind']==k),4) for k in KINDS}}
    def paired(a,b):
        A={x['index']:x['hit'] for x in rep[a]};B={x['index']:x['hit'] for x in rep[b]}
        return {'wins':sum(A[i] and not B[i] for i in A),'losses':sum(B[i] and not A[i] for i in A)}
    rep['summary']=summ;rep['paired']={'gist_vs_fixed960':paired('gist','fixed960'),'gist_vs_event960':paired('gist','event960'),'event960_vs_fixed960':paired('event960','fixed960')}
    g,f=summ['gist'],summ['fixed960'];pg=rep['paired']['gist_vs_fixed960']
    crit={'hit_wins_gt_losses':pg['wins']>pg['losses'],'quote_validity_not_lower':g['quotes_valid']>=f['quotes_valid'],'prompt_tokens_within_10pct':g['prompt_tokens_mean']<=1.1*f['prompt_tokens_mean']}
    rep['decision']={'criteria':crit,'verdict':'GIST_HELPS_CANDIDATE' if all(crit.values()) else 'GIST_NO_GAIN','consequence':'gist stays SHADOW either way; a candidate only justifies a separately preregistered ACTIVE trial by the user'}
    save();print(json.dumps(summ,indent=1));print(json.dumps(rep['paired']),json.dumps(rep['decision']))

if __name__=='__main__':main()
