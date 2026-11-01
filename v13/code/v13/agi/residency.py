"""WP-AG13 expert residency: MoE experts live in RAM only while useful, and learn only while resident.

Blueprint: L9.3 / OPT.body_residency_policy [TUNE/LEARNED], §24.33 Redmi scheduling/residency, F7
runtime fabric, line 80 ("protect router/shared path first; active-expert/projector/delta experiments
before router/base plasticity"), §12.1 eligibility arises during activity.
User wish (2026-10-09): experts in RAM only when active, learning while they are in RAM.

Model-free policy:
- request(expert) on a routing decision: hit → use; miss → load if it fits the RAM budget, else evict
  the least valuable resident (value = recency-weighted use frequency; pinned experts never leave).
- prefetch() suggests experts the router uses most, within spare budget (no load if resources are tight).
- Learning: can_learn(expert) only while resident and not pinned-shared (router/shared layers stay
  protected); updates for an evicted expert are queued (bounded) and replayed when it is loaded again.
- Memory pressure (YELLOW/RED from the resource guard) shrinks the budget at once.
The actual load/unload is done by the runner (mmap/llama.cpp); this module decides and records.
"""
import time
from .base import StateBox

KEY='AG13_EXPERT_RESIDENCY';REVISION='ag13-residency-v1'
DECAY=.9;MAX_QUEUE=64
PRESSURE_SHARE={'GREEN':1.,'YELLOW':.6,'ORANGE':.45,'RED':.3}  # §97.2 modes; BOOT shares

class ExpertResidency:
    def __init__(self,store,budget_mb=1500,clock=time.time,key=KEY):
        self.clock=clock
        self.box=StateBox(store,key,REVISION,lambda:{'experts':{},'resident':[],'budget_mb':float(budget_mb),'mode':'GREEN',
                                                     'counters':{'hit':0,'miss':0,'evict':0,'refused':0},'queue':{}})
    def register(self,expert,size_mb,body='B1_DETAIL',pinned=False,shared=False):
        """shared=True marks router/shared/pre-router parts: always resident (pinned), never plastic here."""
        def f(st):
            st['experts'][expert]={'size_mb':float(size_mb),'body':body,'pinned':bool(pinned or shared),'shared':bool(shared),'score':0.,'last':0.}
            if pinned or shared:
                if expert not in st['resident']:st['resident'].append(expert)
        self.box.mutate(f)
    def _used(self,st):return sum(st['experts'][e]['size_mb'] for e in st['resident'])
    def _cap(self,st):return st['budget_mb']*PRESSURE_SHARE[st['mode']]
    def _value(self,e):return e['score']
    def request(self,expert):
        """Routing chose this expert. Returns {'status': HIT|LOADED|REFUSED, 'evict': [...]} for the runner."""
        def f(st):
            for e in st['experts'].values():e['score']*=DECAY
            ex=st['experts'][expert];ex['score']+=1.;ex['last']=self.clock()
            if expert in st['resident']:st['counters']['hit']+=1;return {'status':'HIT','evict':[]}
            st['counters']['miss']+=1;evict=[]
            cands=sorted((e for e in st['resident'] if not st['experts'][e]['pinned']),key=lambda e:(self._value(st['experts'][e]),st['experts'][e]['last']))
            while self._used(st)+ex['size_mb']>self._cap(st) and cands:
                v=cands.pop(0);st['resident'].remove(v);evict.append(v);st['counters']['evict']+=1
            if self._used(st)+ex['size_mb']>self._cap(st):
                st['counters']['refused']+=1;return {'status':'REFUSED','evict':evict,'fallback':'dense/shared path'}
            st['resident'].append(expert)
            return {'status':'LOADED','evict':evict,'replay_updates':st['queue'].pop(expert,[])}
        return self.box.mutate(f)
    def set_mode(self,mode):
        """Resource guard state; under pressure non-pinned experts are dropped until the budget fits."""
        if mode not in PRESSURE_SHARE:raise ValueError('GREEN|YELLOW|ORANGE|RED')
        def f(st):
            st['mode']=mode;evict=[]
            for e in sorted((e for e in st['resident'] if not st['experts'][e]['pinned']),key=lambda e:self._value(st['experts'][e])):
                if self._used(st)<=self._cap(st):break
                st['resident'].remove(e);evict.append(e);st['counters']['evict']+=1
            return evict
        return self.box.mutate(f)
    def prefetch(self,n=2):
        st=self.box.load()[0];spare=self._cap(st)-self._used(st)
        if st['mode']!='GREEN':return []
        out=[]
        for name,e in sorted(st['experts'].items(),key=lambda kv:-kv[1]['score']):
            if name in st['resident'] or e['score']<=0 or e['size_mb']>spare:continue
            out.append(name);spare-=e['size_mb']
            if len(out)>=n:break
        return out
    def can_learn(self,expert):
        st=self.box.load()[0];e=st['experts'].get(expert)
        return bool(e) and expert in st['resident'] and not e['shared']
    def defer_update(self,expert,update_ref):
        """Learning signal for a non-resident expert: kept (bounded) and handed back when it loads."""
        def f(st):
            q=st['queue'].setdefault(expert,[]);q.append(update_ref);del q[:-MAX_QUEUE]
        self.box.mutate(f)
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'mode':st['mode'],'budget_mb':st['budget_mb'],'cap_mb':round(self._cap(st),1),'used_mb':round(self._used(st),1),
                'resident':list(st['resident']),'counters':st['counters'],'queued':{k:len(v) for k,v in st['queue'].items()},
                'claim_limit':'Residency decisions only; real expert load/unload needs a MoE body and runner support (MobileMoE gated)'}
