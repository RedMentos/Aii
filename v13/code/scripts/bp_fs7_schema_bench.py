"""WP-FS7: schema vs raw-episode replay on NEW values, new item counts and new wording (software, calc tool, no model).
Preregistered in v13/bench-results/fs7-schema-20261101/PREREG.md. Usage: python scripts/bp_fs7_schema_bench.py OUTDIR"""
import json,os,random,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from v13.agi import schema as sc
from v13.agi.tools import calc
out=sys.argv[1];rng=random.Random(7)
WORD={'train':['Expense report. Items cost {l}. What is the total?','Add up these costs: {l}. Give the sum.'],
      'test':['Receipts show {l}. What do they sum to?','The bill lists {l}. How much in total?']}
def task(kind,split):
    k=rng.choice([2,3] if split=='train' else [3,4,5]);v=[rng.randint(10,99) for _ in range(k)]
    if rng.random()<.5 or kind=='sum':
        t=rng.choice(WORD[split]).format(l=', '.join(map(str,v)));return {'text':t,'steps':[{'tool':'calc','args':{'expression':' + '.join(map(str,v))}}],'truth':sum(v)}
tr=[task('sum','train') for _ in range(2)];te=[task('sum','test') for _ in range(200)]
sch=sc.induce(tr,min_support=2)
def run(steps):
    try:return calc(steps[0]['args']['expression'])
    except Exception:return None
def correct(steps,t):
    r=run(steps) if steps else None;return r is not None and float(r)==t['truth']
res={}
def evalp(name,fn):res[name]=sum(correct(fn(t),t) for t in te)/len(te)
def raw(t):  # replay the literal steps of the most similar training episode
    w=set(t['text'].casefold().split());b=max(tr,key=lambda e:len(w&set(e['text'].casefold().split())));return b['steps']
def sch_fn(t):
    s=sc.select(sch,t['text']);return sc.instantiate(s,t['text']) if s else None
def sch_struct(t):  # selector by structure: first schema that instantiates on the question's numbers
    for s in sch:
        if s['stage']=='SCHEMA':
            r=sc.instantiate(s,t['text'])
            if r:return r
def raw_sub(t):  # control: nearest episode, its numbers replaced by the question's numbers position by position
    b=raw(t);ns=sc.nums(t['text']);e=b[0]['args']['expression'];old=sc.nums(e)
    it=iter(ns);return [{'tool':'calc','args':{'expression':sc._NUM.sub(lambda m:next(it,m.group(0)),e)}}]
evalp('raw_episode_replay',raw);evalp('raw_positional_substitution',raw_sub);evalp('schema_trigger_selector',sch_fn);evalp('schema_structure_selector',sch_struct)
res['schemas']=[{k:v for k,v in s.items()} for s in sch];res['n_test']=len(te)
os.makedirs(out,exist_ok=True);json.dump(res,open(os.path.join(out,'report.json'),'w'),indent=1);print({k:v for k,v in res.items() if k!='schemas'})
