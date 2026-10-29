"""WP-HB0: tasks where the bodies (B1 detail, B2 gist) can matter at all (generated English long documents, regex-scored).

Why: earlier benches (utility_bench2, Z6e/Z6m) used one short paragraph, which C3 (350M) solves alone; the oracle of
perfect waking gained only 3 of 60 (R4).  Here the document is longer than C3's live window (context_tokens 2048) and the
answer needs several scattered pieces, so a reader with a bigger window, retrieval, or a body pipeline has room to win.

Families (seeded, deterministic gold sentences known to the generator):
  D  scattered sum      all orders of one project among look-alike orders of other projects -> total
  S  revision chain     one budget revised several times in different wording -> final value
  G  global comparison  three teams report output first and last -> team with biggest growth and the growth
  C  late correction    a date is announced early, moved late (other wording) -> final day and reason
Arms (temperature 0, answers regex-scored on the final text):
  c3_head / c3_tail   C3 sees the part of the document that fits 2048 tokens (start / end)
  c3_rag              C3 + top chunks by word overlap with the question (fits the window)
  b1_long / b2_long   body reads the whole document alone (window 8192)
  or_c3 / or_b1       ORACLE: model gets only the gold sentences (ceiling of any extraction pipeline)
  pipe                real pipeline: B1 extracts question-relevant lines per chunk, B2 writes a gist, C3 answers from both
Usage: hb0_body_needed_tasks.py gen <out.json> | run <tasks.json> <out.json> [arm,arm] [--limit N]
Servers: llama-server on 8101 (C3), 8102 (B1), 8103 (B2), see the proof folder README."""
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

PORTS={'c3':8101,'b1':8102,'b2':8103}
C3_CHARS=6400            # ~2048-token window minus question and answer room (4 chars/token)
NAMES=('Mira','Jonas','Aylin','Tomas','Greta','Elif','Noah','Lena','Omar','Sofia','Pavel','Ines')
PROJECTS=('Falcon','Harbor','Lantern','Meadow','Orchid','Quartz','Ridge','Summit','Tundra','Willow')
GOODS=('widgets','sensors','brackets','cables','filters','valves')
TEAMS=('Alpha','Bravo','Cedar','Delta','Ember','Fjord')
DAYS=('Monday','Tuesday','Wednesday','Thursday','Friday')
REASONS=('the hall was double booked','the auditor could only come later','a supplier delivery was delayed','the main speaker fell ill','the budget review ran over')
FILLER=('The kitchen team replaced the old coffee machine and nobody complained.','Parking near the east entrance was repainted over the weekend.',
 'A short fire drill took place and everyone reached the yard in four minutes.','The newsletter went out one day late because of a layout problem.',
 'Two interns joined the department and shared a desk near the window.','The printer on the second floor jammed again and was reset by facilities.',
 'Visitors from a partner company toured the workshop in the afternoon.','The canteen offered a vegetarian special that sold out by noon.',
 'Maintenance checked the elevators and found nothing unusual.','A delegation asked about the schedule for the autumn training weeks.',
 'The library returned a box of old manuals that had been missing for a year.','Rain delayed the roof inspection until the following week.',
 'Someone left an umbrella in the meeting room and it stayed there for days.','The security desk updated the visitor badge template.',
 'A neighbour company asked to borrow the projector for a trade fair.','The staff survey reminder was sent a second time.')

def pad(rng,pieces,target_chars):
    # pieces are (text, is_gold); insert filler between them until the document is long enough
    out=[];n=len(pieces)
    gaps=max(1,target_chars//max(1,n))
    for text,g in pieces:
        k=max(1,int(gaps/70));out+= [(rng.choice(FILLER),False) for _ in range(rng.randint(max(1,k-1),k+1))];out.append((text,g))
    out+=[(rng.choice(FILLER),False) for _ in range(3)]
    return out

def render(parts):
    paras=[];cur=[]
    for i,(t,_) in enumerate(parts):
        cur.append(t)
        if len(cur)>=4:paras.append(' '.join(cur));cur=[]
    if cur:paras.append(' '.join(cur))
    return '\n\n'.join('Day %d. %s'%(i+1,p) for i,p in enumerate(paras))

def fam_d(rng,i):
    proj,*others=rng.sample(PROJECTS,4);good=rng.choice(GOODS);k=rng.randint(4,6);qs=rng.sample(range(12,90),k)
    tpl=('Procurement ordered %d %s for Project %s.','For Project %s the site manager requested %d more %s.','Project %s received a purchase order of %d %s.')
    pieces=[]
    for q in qs:
        c=rng.randrange(3);pieces.append(((tpl[c]%(q,good,proj)) if c==0 else (tpl[c]%(proj,q,good)),True))
    for _ in range(k+3):
        p=rng.choice(others);c=rng.randrange(3);q=rng.randint(12,90)
        while q in qs:q=rng.randint(12,90)
        pieces.append(((tpl[c]%(q,good,p)) if c==0 else (tpl[c]%(p,q,good)),False))
    rng.shuffle(pieces)
    chk={'n%d'%j:r'\b%d\b'%q for j,q in enumerate(qs)}
    return ('d%02d'%i,pieces,'List the quantity of every single order of %s for Project %s.'%(good,proj),chk,qs)

def fam_s(rng,i):
    proj=rng.choice(PROJECTS);vals=rng.sample(range(40,99),4);vals=[v*1000 for v in vals];final=vals[-1]
    seq=[('The budget for Project %s was set at %d euros.'%(proj,vals[0]),True),
         ('After the first review the board revised the Project %s budget to %d euros.'%(proj,vals[1]),True),
         ('Finance later changed the %s allowance to %d euros.'%(proj,vals[2]),True),
         ('Following the audit the %s team now works with %d euros.'%(proj,vals[3]),True)]
    oth=[]
    for p in rng.sample([x for x in PROJECTS if x!=proj],3):
        oth.append(('The budget for Project %s was set at %d euros.'%(p,rng.randrange(40,99)*1000),False))
        oth.append(('The board revised the Project %s budget to %d euros.'%(p,rng.randrange(40,99)*1000),False))
    pieces=list(seq)
    for o in oth:pieces.insert(rng.randint(0,len(pieces)),o)
    return ('s%02d'%i,pieces,'What is the current budget of Project %s in euros? Give the number.'%proj,{'final':r'\b%s\b'%re.escape('{:,}'.format(final))+'|\\b%d\\b'%final},[final])

def fam_g(rng,i):
    ts=rng.sample(TEAMS,3);first={t:rng.randint(40,80) for t in ts};grow={t:rng.randint(-10,35) for t in ts}
    while len(set(grow.values()))<3:grow={t:rng.randint(-10,35) for t in ts}
    last={t:first[t]+grow[t] for t in ts};best=max(ts,key=lambda t:grow[t])
    pieces=[]
    for t in ts:
        pieces.append(('In the first report Team %s delivered %d units.'%(t,first[t]),True))
    for t in ts:
        pieces.append(('In the final report Team %s delivered %d units.'%(t,last[t]),True))
    pieces.append(('In a mid-term report Team %s delivered %d units.'%(rng.choice(ts),rng.randint(30,100)),False))
    rng.shuffle(pieces)
    return ('g%02d'%i,pieces,'Which team grew its output the most between the first and the final report, and by how many units?',{'team':r'\b%s\b'%best,'!others':r'\b(%s)\b'%'|'.join(t for t in ts if t!=best),'grow':r'\b%d\b'%grow[best]},[grow[best]])

def fam_c(rng,i):
    d1,d2=rng.sample(DAYS,2);why=rng.choice(REASONS);proj=rng.choice(PROJECTS)
    pieces=[('The %s kickoff meeting will be held on %s at ten.'%(proj,d1),True),
            ('Please note a change for %s: the session has been pushed to %s because %s.'%(proj,d2,why),True)]
    for p in rng.sample([x for x in PROJECTS if x!=proj],2):
        pieces.insert(rng.randint(0,len(pieces)),('The %s kickoff meeting will be held on %s at ten.'%(p,rng.choice(DAYS)),False))
    return ('c%02d'%i,pieces,'On which day is the %s kickoff finally held, and why was it moved?'%proj,{'day':r'\b%s\b'%d2,'why':'(?i)'+re.escape(why.split(' ',1)[1] if why.startswith('the ') else why).replace('\\ ','.{0,6}')},[d2])

FAMS={'D':fam_d,'S':fam_s,'G':fam_g,'C':fam_c}

def gen(seed=20261029,per=38,chars=11000):
    rng=random.Random(seed);out=[]
    for f,fn in FAMS.items():
        for i in range(per):
            tid,pieces,q,checks,_=fn(rng,i);parts=pad(rng,pieces,chars)
            out.append({'id':f+tid[1:],'family':f,'document':render(parts),'question':q,'checks':checks,
                        'gold':[t for t,g in parts if g]})
    return out

def call(role,system,user,max_tokens=160,timeout=900):
    body={'messages':[{'role':'system','content':system},{'role':'user','content':user}],'temperature':0,'max_tokens':max_tokens,'chat_template_kwargs':{'enable_thinking':False}}
    req=urllib.request.Request('http://127.0.0.1:%d/v1/chat/completions'%PORTS[role],json.dumps(body).encode(),{'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=timeout).read())['choices'][0]['message']['content'].strip()

SYS='Answer the question using only the text given. Be brief: give the exact number or name, and the reason if the question asks why.'
def prompt(doc,q):return 'Text:\n%s\n\nQuestion: %s'%(doc,q)

def words(s):return set(re.findall(r'[a-z0-9]+',s.lower()))
def chunks(doc,size=1100):
    paras=doc.split('\n\n');cs=[];cur=''
    for p in paras:
        if len(cur)+len(p)>size and cur:cs.append(cur);cur=''
        cur+=('\n\n' if cur else '')+p
    if cur:cs.append(cur)
    return cs
def rag(doc,q,budget=C3_CHARS-600):
    qw=words(q)-{'the','a','of','is','and','in','to','how','many','what','which','on','for','was','were','did','give','number','by'}
    sents=[s for s in re.split(r'(?<=[.!?])\s+',doc.replace('\n\n',' ')) if s]
    ranked=sorted(range(len(sents)),key=lambda j:-len(words(sents[j])&qw)+j*1e-6)
    keep=[];n=0
    for j in ranked:
        if n+len(sents[j])>budget:break
        keep.append(j);n+=len(sents[j])+1
    return ' '.join(sents[j] for j in sorted(keep))

def run_arm(arm,t):
    doc,q=t['document'],t['question']
    if arm=='c3_head':return call('c3',SYS,prompt(doc[:C3_CHARS],q))
    if arm=='c3_tail':return call('c3',SYS,prompt(doc[-C3_CHARS:],q))
    if arm=='c3_rag':return call('c3',SYS,prompt(rag(doc,q),q))
    if arm=='b1_long':return call('b1',SYS,prompt(doc,q))
    if arm=='b2_long':return call('b2',SYS,prompt(doc,q))
    if arm=='or_c3':return call('c3',SYS,prompt(' '.join(t['gold']),q))
    if arm=='or_b1':return call('b1',SYS,prompt(' '.join(t['gold']),q))
    if arm=='pipe':
        notes=[];gists=[]
        for c in chunks(doc):
            notes.append(call('b1','Copy every sentence of the text that could help answer the question, word for word, one per line. If none, write NONE.',prompt(c,q),max_tokens=200))
            gists.append(call('b2','Write one short sentence that says what this text is about.',c,max_tokens=40))
        ev='\n'.join(n for n in notes if n.strip().upper()!='NONE')[:C3_CHARS-1200]
        return call('c3',SYS,'Relevant lines:\n%s\n\nOverview of the document: %s\n\nQuestion: %s'%(ev,' | '.join(gists)[:700],q))
    raise ValueError(arm)

def score(ans,checks):return {k:(not re.search(v,ans)) if k.startswith('!') else bool(re.search(v,ans)) for k,v in checks.items()}

ARMS=('c3_head','c3_tail','c3_rag','b1_long','b2_long','or_c3','or_b1','pipe')
def main(argv):
    if argv[0]=='gen':
        ts=gen();Path(argv[1]).write_text(json.dumps(ts,indent=1));print(len(ts),'tasks, doc chars',min(len(t['document']) for t in ts),max(len(t['document']) for t in ts));return
    tasks=json.loads(Path(argv[1]).read_text());out=Path(argv[2]);arms=argv[3].split(',') if len(argv)>3 and not argv[3].startswith('--') else ARMS
    if '--limit' in argv:
        n=int(argv[argv.index('--limit')+1]);by={}
        for t in tasks:by.setdefault(t['family'],[]).append(t)
        tasks=[x for f in by.values() for x in f[:n//len(by)]]
    rows=json.loads(out.read_text()) if out.exists() else []
    done={(r['arm'],r['id']) for r in rows}
    for arm in arms:
        for t in tasks:
            if (arm,t['id']) in done:continue
            t0=time.monotonic();ans=run_arm(arm,t);ok=score(ans,t['checks'])
            rows.append({'arm':arm,'id':t['id'],'family':t['family'],'pass':all(ok.values()),'checks':ok,'s':round(time.monotonic()-t0,1),'answer':ans[:300]})
            out.write_text(json.dumps(rows,indent=1))
        print(arm,sum(r['pass'] for r in rows if r['arm']==arm),'/',sum(r['arm']==arm for r in rows),flush=True)

if __name__=='__main__':main(sys.argv[1:])
