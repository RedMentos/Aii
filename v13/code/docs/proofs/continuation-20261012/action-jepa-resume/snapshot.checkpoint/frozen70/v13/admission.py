"""WP-T9 / §9.5 learned memory admission: which human memories deserve long-term consolidation (AG6 into weights).

Not everything becomes long-term memory. Every candidate is already a human-authored correction (memory.py never stores
model text as fact); admission only decides *priority and admission into consolidation*, never truth.
Features per active memory, all from stored human signals or usage:
  uses (turns that recalled it), retrieval relevant / irrelevant labels, restatements (same key, same value again),
  explicit `:note` scores of turns that used it, WP-N8 strength, kind, scope, age.
Labels (human only): positive = `:retrieval relevant`, restated by the user, used in a turn rated >= 8;
  negative = `:retrieval irrelevant`, superseded by a different value, deleted with `:forget`, used in a turn rated <= 3.
Model: logistic regression (pure Python, L2) over the features; BOOT prior weights until enough labels.
Authority: SHADOW by default (scores are logged with each AG6 batch, the order does not change). `:admission active` (user
only) needs a passed held-out check (learned AUC >= prior AUC and >= AUC_MIN on >= MIN_LABELS labels) and then orders
AG6 candidates by score and leaves out scores below `admission_floor`.
"""
import json
import math
from .common import now,dumps,digest

KEY='MEMORY_ADMISSION';REVISION='wp-t9-admission-v1'
FEATURES=('bias','uses','relevant','irrelevant','restated','rating','strength','kind_fact','kind_style','scope_global','age')
PRIOR={'bias':0.,'uses':.6,'relevant':1.2,'irrelevant':-1.5,'restated':.8,'rating':.8,'strength':.5,'kind_fact':.2,'kind_style':0.,
       'scope_global':.2,'age':-.1}  # BOOT: used, confirmed, well-rated memories first
MIN_LABELS=20;AUC_MIN=.6;L2=.1;STEPS=400;LR=.3
RATING_GOOD=8;RATING_BAD=3

def _sig(x):return 1/(1+math.exp(-max(-30.,min(30.,x))))
def score(w,f):return _sig(sum(w.get(k,0.)*f.get(k,0.) for k in FEATURES))

def auc(scores,labels):
    pos=[s for s,l in zip(scores,labels) if l];neg=[s for s,l in zip(scores,labels) if not l]
    if not pos or not neg:return None
    return sum((p>n)+.5*(p==n) for p in pos for n in neg)/(len(pos)*len(neg))

def fit(rows,steps=STEPS,lr=LR,l2=L2,init=None):
    """rows: [(features, label 0/1)]. Batch gradient descent from the prior; deterministic."""
    w=dict(init or PRIOR)
    for _ in range(steps):
        g={k:0. for k in FEATURES}
        for f,y in rows:
            e=score(w,f)-y
            for k in FEATURES:g[k]+=e*f.get(k,0.)
        for k in FEATURES:w[k]-=lr*(g[k]/max(1,len(rows))+(l2*w[k] if k!='bias' else 0.))
    return w

class Admission:
    def __init__(self,store,cfg=None):self.s=store;self.cfg=cfg or {}
    def state(self):
        st,_=self.s.state(KEY,None)
        return st or {'revision':REVISION,'authority':'SHADOW','weights':None,'check':None,'history':[]}
    def _save(self,st):self.s.set_state(KEY,st)
    # --- signals ---------------------------------------------------------------------------------------------------
    def _usage(self):
        """memory_id -> list of event ids of turns that recalled it (assistant message metadata)."""
        out={}
        for r in self.s.rows("SELECT event_id,metadata FROM messages WHERE role='assistant' AND metadata IS NOT NULL"):
            try:ids=json.loads(r['metadata'] or '{}').get('memory_ids') or []
            except ValueError:continue
            for m in ids:out.setdefault(m,[]).append(r['event_id'])
        return out
    def _retrieval(self):
        out={}
        for p in self.s.rows("SELECT payload FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.kind')='retrieval'"):
            d=json.loads(p['payload']);m=(d.get('selection') or {}).get('memory_id')
            if m:out.setdefault(m,{'relevant':0,'irrelevant':0})[d['value']]+=1
        return out
    def _ratings(self):
        try:
            from .inputs import ratings
            return {r['event_id']:r['score'] for r in ratings(self.s) if r.get('origin')=='EXPLICIT_NOTE'}
        except Exception:return {}
    def _strength(self,mid,t):
        try:
            from .episodes import Episodes
            return Episodes(self.s,self.cfg).strength(mid,t) or 0.
        except Exception:return 0.
    def table(self,clock=None):
        """All human memories with features and (when any) a human-derived label."""
        t=now() if clock is None else clock
        rows=self.s.rows("SELECT id,event_id,kind,scope,key_text,value,active,created,session_id FROM memories WHERE kind IN ('fact','style','preference') ORDER BY created")
        use=self._usage();ret=self._retrieval();rate=self._ratings()
        by_key={}
        for r in rows:by_key.setdefault((r['session_id'] if r['scope']=='session' else '*',r['kind'],r['key_text']),[]).append(r)
        out=[]
        for r in rows:
            peers=by_key[(r['session_id'] if r['scope']=='session' else '*',r['kind'],r['key_text'])]
            later=[p for p in peers if p['created']>r['created'] or (p['created']==r['created'] and p['id']>r['id'])]
            restated=sum(1 for p in peers if p['id']!=r['id'] and p['value']==r['value'] and p['value']!='[GELÖSCHT]')
            ev=use.get(r['id'],[]);scores=[rate[e] for e in ev if e in rate]
            rr=ret.get(r['id'],{'relevant':0,'irrelevant':0})
            f={'bias':1.,'uses':math.log1p(len(ev)),'relevant':float(rr['relevant']),'irrelevant':float(rr['irrelevant']),'restated':float(min(restated,3)),
               'rating':(sum(scores)/len(scores)-5)/5 if scores else 0.,'strength':self._strength(r['id'],t),
               'kind_fact':float(r['kind']=='fact'),'kind_style':float(r['kind']=='style'),'scope_global':float(r['scope']=='global'),
               'age':math.log1p(max(0.,t-r['created'])/86400)}
            deleted=r['value']=='[GELÖSCHT]';superseded=not r['active'] and not deleted and any(p['value']!=r['value'] for p in later)
            pos=rr['relevant']>0 or restated>0 or any(s>=RATING_GOOD for s in scores)
            neg=rr['irrelevant']>0 or deleted or superseded or any(s<=RATING_BAD for s in scores)
            label=None if pos==neg else int(pos)  # conflicting or no signal: unlabeled
            out.append({'memory_id':r['id'],'active':bool(r['active']),'features':f,'label':label,
                        'reasons':[k for k,v in (('relevant',rr['relevant']),('restated',restated),('rated_good',any(s>=RATING_GOOD for s in scores)),
                                                 ('irrelevant',rr['irrelevant']),('deleted',deleted),('superseded',superseded),('rated_bad',any(s<=RATING_BAD for s in scores))) if v]})
        return out
    # --- learning --------------------------------------------------------------------------------------------------
    def train(self,clock=None):
        """Fit on labeled memories; held-out check (every 4th labeled row, deterministic by id hash) against the prior."""
        tab=self.table(clock);lab=[x for x in tab if x['label'] is not None]
        st=self.state()
        if len(lab)<MIN_LABELS:
            st['check']={'status':'TOO_FEW_LABELS','labels':len(lab),'need':MIN_LABELS,'at':now()};self._save(st);return st['check']
        hold=[x for x in lab if int(digest(x['memory_id'])[:8],16)%4==0];train=[x for x in lab if x not in hold]
        if not hold or len({x['label'] for x in hold})<2 or len({x['label'] for x in train})<2:
            st['check']={'status':'ONE_CLASS','labels':len(lab),'at':now()};self._save(st);return st['check']
        w=fit([(x['features'],x['label']) for x in train])
        learned=auc([score(w,x['features']) for x in hold],[x['label'] for x in hold])
        prior=auc([score(PRIOR,x['features']) for x in hold],[x['label'] for x in hold])
        passed=learned is not None and learned>=AUC_MIN and (prior is None or learned>=prior)
        full=fit([(x['features'],x['label']) for x in lab])  # deployable weights use every label once the check passed
        st['weights']=full if passed else st.get('weights');st['check']={'status':'PASS' if passed else 'FAIL','labels':len(lab),'heldout':len(hold),
            'auc_learned':learned,'auc_prior':prior,'auc_min':AUC_MIN,'at':now(),'weights_sha256':digest(dumps(full))}
        st['history']=(st['history']+[dict(st['check'],kind='TRAIN')])[-32:]
        if not passed and st['authority']=='ACTIVE':st['authority']='SHADOW';st['history'].append({'kind':'DEMOTE','at':now(),'reason':'check failed'})
        self._save(st);return st['check']
    def set_authority(self,mode,origin='USER'):
        st=self.state()
        if mode not in {'SHADOW','ACTIVE'}:raise ValueError('admission: shadow|active')
        if mode=='ACTIVE':
            if origin!='USER':raise ValueError('ACTIVE nur durch den Nutzer')
            if not st.get('check') or st['check'].get('status')!='PASS' or not st.get('weights'):raise ValueError('Zuerst :admission train mit bestandenem Held-out-Check')
        st['authority']=mode;st['history']=(st['history']+[{'kind':mode,'origin':origin,'at':now()}])[-32:];self._save(st);return st
    def weights(self):
        st=self.state();return st['weights'] if st.get('weights') else PRIOR
    def scores(self,memory_ids=None,clock=None):
        w=self.weights();return {x['memory_id']:round(score(w,x['features']),4) for x in self.table(clock) if memory_ids is None or x['memory_id'] in memory_ids}
    # --- use in AG6 ------------------------------------------------------------------------------------------------
    def order(self,items):
        """AG6 candidates: ACTIVE sorts by score and drops scores below the floor; SHADOW keeps the order. Both attach the
        score to each memory item and return the decision record (items that are not memories, e.g. ratings, pass)."""
        st=self.state();ids={i['memory_id'] for i in items if str(i['memory_id']).startswith('mem_')}
        sc=self.scores(ids) if ids else {};floor=float(self.cfg.get('admission_floor',.3))
        for i in items:
            if i['memory_id'] in sc:i['admission']=sc[i['memory_id']]
        would=[i['memory_id'] for i in items if sc.get(i['memory_id'],1.)<floor]
        rec={'authority':st['authority'],'floor':floor,'scores':sc,'would_drop':would,'weights':'learned' if st.get('weights') else 'prior'}
        if st['authority']!='ACTIVE':return items,rec
        kept=sorted((i for i in items if i['memory_id'] in sc and i['memory_id'] not in would),key=lambda i:-sc[i['memory_id']])
        kept+=[i for i in items if i['memory_id'] not in sc];rec['dropped']=would  # non-memory items keep their place after
        return kept,rec
    def report(self):
        st=self.state();tab=self.table()
        return {'authority':st['authority'],'check':st.get('check'),'weights':'learned' if st.get('weights') else 'prior',
                'memories':len(tab),'labeled':sum(x['label'] is not None for x in tab),'positive':sum(x['label']==1 for x in tab),
                'top':sorted(({'memory_id':k,'score':v} for k,v in self.scores([x['memory_id'] for x in tab if x['active']]).items()),key=lambda x:-x['score'])[:5]}

def operator_command(runtime,args):
    a=Admission(runtime.store,runtime.cfg)
    if not args or args==['status']:return a.report()
    if args==['train']:return a.train()
    if args==['active']:return a.set_authority('ACTIVE','USER')
    if args==['shadow']:return a.set_authority('SHADOW','USER')
    if args[0]=='table':return [{k:x[k] for k in ('memory_id','label','reasons','active')} for x in a.table()][-20:]
    raise ValueError(':admission [status|train|active|shadow|table]')
