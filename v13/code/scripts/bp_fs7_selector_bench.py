"""WP-FS7b: wording-independent schema selector, 2 families (sum of 2..5, difference of 2), new wordings, online feedback.
Usage: python scripts/bp_fs7_selector_bench.py OUTDIR"""
import json,os,random,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from v13.agi import schema as sc
from v13.agi.tools import calc
out=sys.argv[1];rng=random.Random(11)
TR={'sum':'Expense report. Items cost {l}. What is the total?','diff':'Stock check. Counted {l}. How many are missing?'}
TE={'sum':['Receipts show {l}. What do they sum to?','The bill lists {l}. How much in total?','Add {l} together.'],
    'diff':['Start with {l}. What is left over?','Between {l}, how large is the gap?','{l}: how much remains?']}
def mk(fam,tpl):
    k=rng.choice([2,3,4,5]) if fam=='sum' else 2;v=[rng.randint(10,99) for _ in range(k)]
    if fam=='diff':v.sort(reverse=True)
    ex=(' + ' if fam=='sum' else ' - ').join(map(str,v));l=(', ' if fam=='sum' else ' and ').join(map(str,v))
    return {'fam':fam,'text':tpl.format(l=l),'steps':[{'tool':'calc','args':{'expression':ex}}],'truth':calc(ex)}
train=[mk(f,TR[f]) for f in TR for _ in range(2)]
sch=sc.induce(train);stream=[mk(f,rng.choice(TE[f])) for f in rng.choices(['sum','diff'],k=300)]
def ok(steps,t):
    try:return steps is not None and float(calc(steps[0]['args']['expression']))==t['truth']
    except Exception:return False
sel=sc.Selector(sch);res={'trigger':[],'structure_first':[],'learned':[]}
for t in stream:
    s=sc.select(sch,t['text']);res['trigger'].append(ok(sc.instantiate(s,t['text']) if s else None,t))
    c=[x for x in sch if x['stage']=='SCHEMA' and sc.instantiate(x,t['text'])];res['structure_first'].append(ok(sc.instantiate(c[0],t['text']) if c else None,t))
    i=sel.choose(t['text']);r=ok(sc.instantiate(sel.sch[i],t['text']) if i is not None else None,t);res['learned'].append(r)
    if i is not None:sel.feedback(i,t['text'],r)
rep={k:{'all':sum(v)/len(v),'last100':sum(v[-100:])/100} for k,v in res.items()}
rep['by_family_last100_learned']={f:sum(r for r,t in zip(res['learned'][-100:],stream[-100:]) if t['fam']==f)/max(1,sum(t['fam']==f for t in stream[-100:])) for f in TR}
os.makedirs(out,exist_ok=True);json.dump(rep,open(os.path.join(out,'selector.json'),'w'),indent=1);print(json.dumps(rep))
