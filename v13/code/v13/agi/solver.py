"""WP-AG12 step 2: solver adapters that let the real bodies answer the generality suite.

The suite (generality.py) only measures; this module connects it to the native runners so the
curves show what B1/B2/C3 can do per generation. Rules:
- No store writes, no memory, no tools, no history: the holdout prompts must never reach the
  episodic store or any training set (guard_training), and a tool would measure the tool, not V13.
- Answers come as JSON {"answer": ...} under a grammar, so extraction is exact and the runner
  returns token log-probabilities for the answer span (confidence = least probable answer token,
  the best error signal measured in WP-KAL2).
- batch(): one body answers all items before the next body loads (phone: one resident body).
- 'v13' combines the bodies like the JEF combines offers: confidence-weighted vote, agreement
  raises confidence, disagreement lowers it. It is still not the full live turn (no focal loop,
  no recall); that would put holdout prompts into memory.
"""
import json
import math
import re
import threading
import time
from ..common import Cancelled,Unavailable,digest,dumps
from .generality import normalize

SYS='Answer with only the final answer. No explanation, no units, no extra words.'
SCHEMA={'type':'object','properties':{'answer':{'type':'string','maxLength':64}},'required':['answer']}
ROLES={'c3':('C3_LANGUAGE',),'b1':('B1_DETAIL',),'b2':('B2_GIST',),'v13':('B1_DETAIL','B2_GIST','C3_LANGUAGE')}
CONF_KEYS=('field_min_prob','field_mean_prob','mean_prob')
ITEM_SECONDS=90.

def extract(text):
    """JSON answer under grammar; tolerant fallback for runners without grammar support."""
    t=(text or '').strip()
    try:
        v=json.loads(t)
        if isinstance(v,dict):return str(v.get('answer','')).strip()
    except ValueError:pass
    m=re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)',t)
    if m:return m.group(1).strip()
    return t.splitlines()[0].strip() if t else ''

def confidence(metrics):
    tc=(metrics or {}).get('token_confidence') or {}
    for k in CONF_KEYS:
        v=tc.get(k)
        if isinstance(v,(int,float)):return max(0.,min(1.,float(v))),k
    return .5,'none'

def combine(outs):
    """outs: [{'role','answer','confidence'}] -> one answer. Score per distinct answer = sum of member
    confidences; final confidence = score / number of voters (unanimous sure bodies -> high)."""
    outs=[o for o in outs if o.get('answer')]
    if not outs:return {'answer':'','confidence':0.,'votes':{}}
    score={};first={}
    for o in outs:
        k=normalize(o['answer']);score[k]=score.get(k,0.)+o['confidence'];first.setdefault(k,o['answer'])
    best=max(score,key=lambda k:(score[k],-list(first).index(k)))
    return {'answer':first[best],'confidence':round(score[best]/len(outs),4),'votes':{k:round(v,4) for k,v in score.items()},
            'agree':sum(normalize(o['answer'])==best for o in outs),'voters':len(outs)}

class BodySolver:
    """solver(view) and solver.batch(views) for one or more body roles of a runtime's RunnerPool."""
    def __init__(self,pool,roles,cfg=None,name=None,item_seconds=ITEM_SECONDS,seed=13):
        self.pool=pool;self.roles=tuple(roles);self.cfg=cfg or {};self.name=name or '+'.join(self.roles)
        self.item_seconds=item_seconds;self.seed=seed;self.stopped=None;self.stats={}
    def available(self,models):
        out=[]
        for r in self.roles:
            try:models.path_for(r);out.append(r)
            except Exception:pass
        return out
    def ask(self,role,view,cancel=None,deadline=None):
        dl=time.monotonic()+self.item_seconds
        if deadline is not None:dl=min(dl,deadline)
        runner=self.pool.get(role);text=''
        ev=cancel if cancel is not None else threading.Event()
        for tok in runner.generate([{'role':'system','content':SYS},{'role':'user','content':view['prompt']}],ev,dl,max_tokens=40,
                                   schema=SCHEMA,seed=self.seed,confidence_field='answer'):text+=tok
        conf,src=confidence(getattr(runner,'last_metrics',{}))
        return {'role':role,'answer':extract(text),'confidence':conf,'confidence_source':src}
    def _answers(self,role,views,cancel,deadline):
        out={};st=self.stats.setdefault(role,{'items':0,'errors':0,'seconds':0.})
        for v in views:
            if cancel is not None and cancel.is_set():self.stopped='INTERRUPTED';raise Cancelled()
            if deadline is not None and time.monotonic()>=deadline:self.stopped='DEADLINE';break
            t=time.monotonic()
            try:out[v['id']]=self.ask(role,v,cancel,deadline)
            except Cancelled:self.stopped='INTERRUPTED';raise
            except Exception as exc:out[v['id']]={'role':role,'answer':'','confidence':0.,'error':type(exc).__name__};st['errors']+=1
            st['items']+=1;st['seconds']=round(st['seconds']+time.monotonic()-t,3)
        return out
    def batch(self,views,cancel=None,deadline=None):
        self.stopped=None;per={}
        try:
            for role in self.roles:
                per[role]=self._answers(role,views,cancel,deadline)
                errs=[o for o in per[role].values() if o.get('error')]
                if per[role] and len(errs)==len(per[role]):
                    # every item failed: a broken runner, not a 0 % body. No curve point.
                    self.stopped='ERROR';raise Unavailable(f"{role}: alle {len(errs)} Aufgaben fehlgeschlagen ({errs[0]['error']})")
        except Cancelled:return {}
        done=set.intersection(*[set(p) for p in per.values()]) if per else set()
        if len(self.roles)==1:return {i:per[self.roles[0]][i] for i in done}
        return {i:combine([per[r][i] for r in self.roles]) for i in done}
    def __call__(self,view):
        outs=[self.ask(r,view) for r in self.roles]
        return outs[0] if len(outs)==1 else combine(outs)
    def report(self):return {'name':self.name,'roles':list(self.roles),'stats':self.stats}

def make_solver(runtime,name='v13'):
    """Solver for :growth eval run <name>; only roles with an installed model take part."""
    if name not in ROLES:raise ValueError('Solver: '+'|'.join(ROLES))
    s=BodySolver(runtime.pool,ROLES[name],runtime.cfg,name)
    roles=s.available(runtime.models)
    if not roles:return None
    s.roles=tuple(roles);return s

def run(growth,runtime,name='v13',label='manual',cancel=None,deadline=None):
    solver=make_solver(runtime,name)
    if solver is None:return {'status':'NO_SOLVER','solver':name}
    out=growth.eval.run(solver,label=label,cancel=cancel,deadline=deadline,solver_name=name,include_results=True)
    _feed_metacog(growth,name,out)
    return {'status':out['status'],'solver':name,'roles':list(solver.roles),'overall':out['summary']['overall'],
            'unseen':out['summary']['unseen'],'ece':out['summary']['calibration']['ece'],'stats':solver.stats}

def _feed_metacog(growth,name,run_):
    """AG9 receives only validated rows from the exact completed AG12 run in memory.

    No export-file reread: that file may be stale, overwritten, or tampered.
    German diagnostics use a distinct calibration component; English stays unchanged.
    """
    if run_.get('status')!='DONE' or growth.home is None:return
    try:
        suite=growth.eval.suite
        rows=run_.get('_results')
        items=suite['items']
        if (run_.get('suite_hash')!=suite['hash'] or run_.get('items')!=len(items)
                or not isinstance(rows,list) or len(rows)!=len(items)):
            return
        for item,row in zip(items,rows):
            if (type(row) is not dict or row.get('id')!=item['id']
                    or type(row.get('correct')) is not int or row['correct'] not in (0,1)
                    or type(row.get('confidence')) not in (int,float)
                    or not math.isfinite(row['confidence'])
                    or not 0.<=row['confidence']<=1.):
                return
        nonce=run_.get('_feedback_nonce')
        if type(nonce) is not str or re.fullmatch(r'g12fb_[0-9a-f]{32}',nonce) is None:
            return
        component='ag12:'+name+(':de' if suite['lang']=='de' else '')
        receipt=digest(dumps([nonce,suite['hash'],name,
                              [[row['id'],row['confidence'],row['correct']] for row in rows]]))
        growth.metacog.record_batch(component,
                                    [(row['confidence'],row['correct']) for row in rows],
                                    receipt=receipt)
    except Exception:
        # A failed feedback diagnostic must not grant model or Age authority.
        return
