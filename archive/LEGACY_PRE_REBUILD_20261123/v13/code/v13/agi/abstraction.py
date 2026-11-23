"""WP-AG7 transfer / abstraction: from many cases to one rule, tested on cases it has not seen.

Sleep-B extension: similar episodes are clustered, a rule is induced from part of the
cluster and checked on the held-out rest (and optionally on another domain). Only rules
that hold on unseen cases become VALIDATED hypotheses; they never gain fact authority by
themselves (fact_write_authority = 0), a human promotes them.
Built-in inducer: enumerative search over a tiny program DSL (DreamCoder idea, no model)
for input→output string pairs. A model-based inducer plugs in through the same contract:
inducer(train_pairs) -> list of (name, fn).
"""
import itertools
import re
import time
from .base import StateBox

KEY='G7_ABSTRACTION';REVISION='g7-abstraction-v1'
MIN_SUPPORT=3;HOLDOUT_SHARE=.34;SIM=.5;MAX_RULES=256

def _int(f):
    def g(x):
        try:return str(f(int(x)))
        except ValueError:return None
    return g
def _shift(k):return lambda x:''.join(chr((ord(c)-97+k)%26+97) if 'a'<=c<='z' else c for c in x)
PRIMS=[('identity',lambda x:x),('reverse',lambda x:x[::-1]),('upper',str.upper),('lower',str.lower),('sort',lambda x:''.join(sorted(x))),
       ('dedup',lambda x:''.join(dict.fromkeys(x))),('first',lambda x:x[:1]),('last',lambda x:x[-1:]),('length',lambda x:str(len(x)))]
PRIMS+=[(f'shift{k}',_shift(k)) for k in range(1,26)]
PRIMS+=[(f'add{k}',_int(lambda v,k=k:v+k)) for k in (-10,-5,-3,-2,-1,1,2,3,5,10)]+[(f'mul{k}',_int(lambda v,k=k:v*k)) for k in (2,3,4,5,10)]

def dsl_inducer(pairs,max_depth=2):
    """All programs (compositions of ≤max_depth primitives) consistent with every training pair, shortest first."""
    found=[]
    for d in range(1,max_depth+1):
        for combo in itertools.product(PRIMS,repeat=d):
            def fn(x,combo=combo):
                for _,f in combo:
                    if x is None:return None
                    x=f(x)
                return x
            if all(fn(i)==o for i,o in pairs):found.append(('∘'.join(n for n,_ in reversed(combo)),fn))
        if found:break
    return found

def words(t):return set(re.findall(r'\w+',str(t).casefold()))
def jaccard(a,b):return len(a&b)/len(a|b) if a|b else 0.

def cluster(episodes,key=lambda e:e.get('tags') or e['input'],threshold=SIM):
    """Greedy single-pass clustering on word sets of a key (tags if given)."""
    cl=[]
    for e in episodes:
        w=words(key(e))
        for c in cl:
            if jaccard(w,c['words'])>=threshold:c['members'].append(e);c['words']|=w;break
        else:cl.append({'words':set(w),'members':[e]})
    return [c['members'] for c in cl]

class Abstraction:
    def __init__(self,store,inducer=dsl_inducer,clock=time.time):
        self.s=store;self.inducer=inducer;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'rules':{},'seq':0})
    def induce(self,episodes,domain='text',transfer=None):
        """episodes: [{'id','input','output','tags'?}]. transfer: optional episodes of another domain to test reach."""
        out=[]
        for members in cluster(episodes):
            if len(members)<MIN_SUPPORT:continue
            k=max(1,int(round(len(members)*HOLDOUT_SHARE)));train,test=members[:-k],members[-k:]
            progs=self.inducer([(m['input'],m['output']) for m in train])
            if not progs:continue
            name,fn=progs[0]
            held=sum(fn(m['input'])==m['output'] for m in test)/len(test)
            reach=None
            if transfer:reach=round(sum(fn(m['input'])==m['output'] for m in transfer)/len(transfer),4)
            status='VALIDATED' if held==1. else 'REFUTED'
            out.append(self._save(name,domain,[m['id'] for m in train],[m['id'] for m in test],held,reach,status,len(progs)))
        return out
    def _save(self,program,domain,train,test,held,reach,status,alternatives):
        def f(st):
            for r in st['rules'].values():
                if r['program']==program and r['domain']==domain:
                    r['support']=sorted(set(r['support'])|set(train));r['tests']=sorted(set(r['tests'])|set(test))
                    r['holdout_accuracy']=held;r['transfer']=reach if reach is not None else r['transfer']
                    if status=='REFUTED':r['status']='REFUTED'
                    return dict(r)
            st['seq']+=1;rid=f'rule_{st["seq"]}'
            st['rules'][rid]={'id':rid,'program':program,'domain':domain,'support':train,'tests':test,'holdout_accuracy':held,'transfer':reach,
                              'status':status,'ambiguity':alternatives,'fact_write_authority':0,'created':self.clock()}
            while len(st['rules'])>MAX_RULES:st['rules'].pop(next(iter(st['rules'])))
            return dict(st['rules'][rid])
        return self.box.mutate(f)
    def promote(self,rid):
        """Human decision only: a validated rule becomes an approved principle (still provenance-bound)."""
        def f(st):
            r=st['rules'][rid]
            if r['status']!='VALIDATED':raise ValueError('Nur VALIDATED-Regeln')
            r['status']='APPROVED';r['approved']=self.clock()
        self.box.mutate(f)
    def report(self):
        rules=list(self.box.load()[0]['rules'].values())
        return {'revision':REVISION,'by_status':{s:sum(r['status']==s for r in rules) for s in ('VALIDATED','REFUTED','APPROVED')},
                'rules':[{k:r[k] for k in ('id','program','domain','holdout_accuracy','transfer','status')} for r in rules[-16:]],
                'claim_limit':'Symbolic DSL induction over string/int pairs; model-based inducers plug in later'}
