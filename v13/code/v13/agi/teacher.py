"""WP-AG1 stronger base via teacher distillation (FORSCHUNG §9 #1, blueprint L4.5, L5.5, 0Q.1, STEP4).

1. Requests: a prompt that a teacher should answer (user ask, or V13's own when unsure: AG9).
   V13's own requests need Age right request_teacher (Age 3). A cloud teacher additionally needs
   the user's explicit cloud permission (privacy: the prompt leaves the phone); default off.
2. Traces: teacher answer + optional reasoning, stored as REFERENCE (not fact, not truth),
   together with V13's own earlier answer when one exists (self-distillation / preference pairs).
3. Dataset: nightly distillation set for AG6, provenance kept, AG12 holdout excluded.
4. Internalisation loop (L5.5): per capability, paired and student-only trials give a reliance
   estimate; teacher dropout rises only when the student holds up; removing the teacher is a user decision.
Teacher backends are pluggable: backend(prompt) -> {'answer','reasoning'?,'model'}.
"""
import time
from ..common import digest
from .base import StateBox,age_allows,clamp01

KEY='G1_TEACHER';REVISION='g1-teacher-v1'
MAX_REQ=512;MAX_TRACES=2048;WINDOW=64
KINDS=('local','cloud')

class TeacherDistillation:
    def __init__(self,store,age=None,generality=None,clock=time.time):
        self.s=store;self.age=age;self.g=generality;self.clock=clock;self.backends={}
        self.box=StateBox(store,KEY,REVISION,lambda:{'requests':{},'traces':[],'cloud_allowed':False,'reliance':{},'removed':[],'seq':0})
    def register(self,name,backend,kind='local'):
        if kind not in KINDS:raise ValueError('local|cloud')
        self.backends[name]=(backend,kind)
    def allow_cloud(self,on):
        """User decision only."""
        def f(st):st['cloud_allowed']=bool(on)
        self.box.mutate(f)
    def request(self,prompt,capability='language',origin='USER',reason='',own_answer=None):
        if origin!='USER' and not age_allows(self.age,'request_teacher',origin):return None
        def f(st):
            if capability in st['removed']:return None
            open_=[r for r in st['requests'].values() if r['status']=='OPEN']
            if len(open_)>=MAX_REQ:raise ValueError('Lehrer-Warteschlange voll')
            st['seq']+=1;rid=f'treq_{st["seq"]}'
            st['requests'][rid]={'id':rid,'prompt':str(prompt)[:4000],'capability':capability,'origin':origin,'reason':str(reason)[:200],
                                 'own_answer':own_answer,'status':'OPEN','created':self.clock()}
            return rid
        return self.box.mutate(f)
    def fulfil(self,rid,backend_name,cancel=None):
        backend,kind=self.backends[backend_name]
        st=self.box.load()[0];r=st['requests'].get(rid)
        if not r or r['status']!='OPEN':raise ValueError('Keine offene Lehrer-Anfrage')
        if kind=='cloud' and not st['cloud_allowed']:
            def deny(st):
                current=st['requests'].get(rid)
                if current and current.get('status')=='OPEN':current['status']='DENIED_CLOUD'
                return None
            return self.box.mutate(deny)
        if cancel is not None and cancel.is_set():return None
        out=backend(r['prompt']) or {}
        # Cancellation may arrive while a slow backend is executing. Its output
        # must not become a stored reference after the operator has stopped it.
        if cancel is not None and cancel.is_set():return None
        trace={'request':rid,'capability':r['capability'],'prompt':r['prompt'],'teacher_answer':str(out.get('answer',''))[:8000],
               'reasoning':str(out.get('reasoning',''))[:16000] or None,'own_answer':r['own_answer'],'backend':backend_name,'kind':kind,
               'model':out.get('model'),'authority':'REFERENCE_NOT_FACT','created':self.clock()}
        trace['id']='trace_'+digest(trace['prompt']+trace['teacher_answer'])[:16]
        def f(st):
            current=st['requests'].get(rid)
            # Re-read ownership at the actual commit boundary: a concurrent
            # worker may already have completed/denied this request.
            if not current or current.get('status')!='OPEN':return None
            if cancel is not None and cancel.is_set():return None
            if kind=='cloud' and not st['cloud_allowed']:
                current['status']='DENIED_CLOUD'
                return None
            current['status']='DONE';st['traces']=(st['traces']+[trace])[-MAX_TRACES:];return trace
        return self.box.mutate(f)
    def dataset(self,capability=None,since=0.,limit=256):
        """Distillation examples for AG6/WP-S6. Holdout-guarded; traces are references, so a gate must still test them."""
        rows=[t for t in self.box.load()[0]['traces'] if t['created']>=since and (capability is None or t['capability']==capability) and t['teacher_answer']][-limit:]
        if self.g is not None and rows:
            # AG6 consumes targets, reasoning and rejected responses too.
            # A safe request prompt does not make those returned fields safe.
            training_texts=[]
            for t in rows:
                training_texts.extend(t[k] for k in ('prompt','teacher_answer','reasoning','own_answer') if t.get(k))
            self.g.guard_training(training_texts)
        return [{'prompt':t['prompt'],'target':t['teacher_answer'],'reasoning':t['reasoning'],'rejected':t['own_answer'],
                 'trace_id':t['id'],'authority':t['authority']} for t in rows]
    def trial(self,capability,student_ok,teacher_present):
        """Record one outcome for the internalisation loop. teacher_present=False = student-only shadow trial."""
        def f(st):
            r=st['reliance'].setdefault(capability,{'paired':[],'solo':[]})
            key='paired' if teacher_present else 'solo';r[key]=(r[key]+[int(bool(student_ok))])[-WINDOW:]
        self.box.mutate(f);return self.reliance(capability)
    def reliance(self,capability):
        r=self.box.load()[0]['reliance'].get(capability,{'paired':[],'solo':[]})
        mean=lambda xs:sum(xs)/len(xs) if xs else None
        p,s=mean(r['paired']),mean(r['solo'])
        rel=1. if s is None or p is None or p==0 else clamp01(1-s/p)
        dropout=0. if len(r['solo'])<8 else clamp01(1-rel)*.9  # BOOT: never fully drops itself
        return {'capability':capability,'paired_success':p,'solo_success':s,'reliance':round(rel,4),'dropout':round(dropout,4),
                'removal_ready':len(r['solo'])>=32 and rel<=.05}
    def remove(self,capability):
        """User decision: stop asking the teacher for this capability (reversible with restore)."""
        if not self.reliance(capability)['removal_ready']:raise ValueError('Schüler hält ohne Lehrer noch nicht')
        def f(st):st['removed']=sorted(set(st['removed'])|{capability})
        self.box.mutate(f)
    def restore(self,capability):
        def f(st):st['removed']=[c for c in st['removed'] if c!=capability]
        self.box.mutate(f)
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'backends':{n:k for n,(_,k) in self.backends.items()},'cloud_allowed':st['cloud_allowed'],
                'open_requests':sum(r['status']=='OPEN' for r in st['requests'].values()),'traces':len(st['traces']),
                'reliance':{c:self.reliance(c) for c in st['reliance']},'removed':st['removed'],
                'claim_limit':'Request/trace/dataset/reliance plumbing; no teacher model is called from here without a registered backend'}
