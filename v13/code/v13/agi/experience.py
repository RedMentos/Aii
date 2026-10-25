"""WP-HX3 experience library (Harness² cross-task loop, research/HARNESS2_AUSWERTUNG.md).

One entry per adopted change: situation, lesson, evidence, generation. Without evidence nothing is written:
an entry needs an APPROVED AG8 proposal whose regression shield passed AND at least one evidence file, whose
sha256 is stored and rechecked (a changed or missing file makes the entry STALE). Lookup is by task type.
Entries are data, never instructions: texts are length-capped, control characters and rule-weakening wording are
refused, and every lookup row carries authority DATA_NOT_INSTRUCTION. A rolled-back change retires its entries.
ablation() compares a caller's solver with and without the library on the same tasks (the measurement itself is HX2).
"""
import re
import time
from pathlib import Path
from .base import StateBox,new_id
from ..common import digest

KEY='HX3_EXPERIENCE';REVISION='hx3-experience-v1'
MAX_TEXT=400;MAX_EVIDENCE=8;MAX_ENTRIES=256
TASK_TYPE=re.compile(r'^[a-z][a-z0-9_]{1,31}$')

def _clean(v,name):
    if not isinstance(v,str) or not v.strip():raise ValueError(name+' fehlt')
    v=v.strip()
    if len(v)>MAX_TEXT:raise ValueError(f'{name} länger als {MAX_TEXT}')
    if any(ord(c)<32 and c not in '\n\t' for c in v):raise ValueError('Steuerzeichen in '+name)
    from .harness import WEAKEN
    if WEAKEN.search(v):raise PermissionError(name+' schwächt Regeln')
    return v

class ExperienceLibrary:
    def __init__(self,store,home=None,clock=time.time):
        self.s=store;self.home=Path(home) if home else None;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'entries':{}})
    def _path(self,p):
        p=Path(p)
        if not p.is_absolute():p=(self.home or Path.cwd())/p
        return p
    def _hash(self,p):
        p=self._path(p)
        return digest(p.read_bytes()) if p.is_file() else None
    def record(self,proposal,situation,lesson,evidence,task_type):
        """Only for an applied change: proposal APPROVED with a passed shield, plus evidence files that exist now."""
        if proposal.get('status')!='APPROVED':raise PermissionError('Eintrag nur für freigegebene Änderungen')
        shield=proposal.get('shield') or {}
        if not shield.get('passed'):raise PermissionError('Kein Beleg: Regressionsschild nicht bestanden')
        if not isinstance(task_type,str) or not TASK_TYPE.match(task_type):raise ValueError('task_type [a-z][a-z0-9_]{1,31}')
        ev=[evidence] if isinstance(evidence,str) else list(evidence or [])
        if not ev:raise PermissionError('Kein Beleg: mindestens eine Beleg-Datei')
        if len(ev)>MAX_EVIDENCE:raise ValueError(f'höchstens {MAX_EVIDENCE} Belege')
        files=[]
        for p in ev:
            h=self._hash(p)
            if h is None:raise PermissionError('Beleg fehlt: '+str(p))
            files.append({'path':str(p),'sha256':h})
        entry={'situation':_clean(situation,'situation'),'lesson':_clean(lesson,'lesson'),'task_type':task_type,
               'proposal':proposal['id'],'kind':proposal.get('kind'),'diff_targets':sorted(proposal.get('diff') or {}),
               'shield':{'gain':shield.get('gain'),'regressions':list(shield.get('regressions') or [])},'evidence':files,
               'base_generation':proposal.get('base_generation'),'generation':self.s.generation_id,'created':self.clock(),'status':'ACTIVE'}
        def f(st):
            if any(e['proposal']==entry['proposal'] and e['status']=='ACTIVE' for e in st['entries'].values()):raise ValueError('Eintrag existiert schon')
            eid=new_id('exp');st['entries'][eid]=entry|{'id':eid}
            if len(st['entries'])>MAX_ENTRIES:  # drop the oldest retired/stale first, never silently an active one
                old=sorted((e for e in st['entries'].values() if e['status']!='ACTIVE'),key=lambda e:e['created'])
                if not old:raise ValueError('Bibliothek voll')
                st['entries'].pop(old[0]['id'])
            return eid
        return self.box.mutate(f)
    def verify(self):
        """Recheck evidence hashes; a changed or missing file makes the entry STALE (excluded from lookup)."""
        def f(st):
            n=0
            for e in st['entries'].values():
                if e['status']=='ACTIVE' and any(self._hash(x['path'])!=x['sha256'] for x in e['evidence']):e['status']='STALE';n+=1
            return n
        return self.box.mutate(f)
    def retire(self,proposal_id,reason='rollback'):
        def f(st):
            n=0
            for e in st['entries'].values():
                if e['proposal']==proposal_id and e['status']=='ACTIVE':e['status']='RETIRED';e['retired']={'reason':str(reason)[:80],'time':self.clock()};n+=1
            return n
        return self.box.mutate(f)
    def lookup(self,task_type,k=3,enabled=True):
        """Newest ACTIVE entries of a task type, as data. enabled=False is the ablation arm (always empty)."""
        if not enabled:return []
        es=[e for e in self.box.load()[0]['entries'].values() if e['status']=='ACTIVE' and e['task_type']==task_type]
        es.sort(key=lambda e:(-(e['shield']['gain'] or 0),-e['created']))
        return [{'id':e['id'],'situation':e['situation'],'lesson':e['lesson'],'evidence':[x['path'] for x in e['evidence']],
                 'generation':e['generation'],'authority':'DATA_NOT_INSTRUCTION'} for e in es[:max(0,int(k))]]
    def report(self):
        es=list(self.box.load()[0]['entries'].values());by={}
        for e in es:by[e['status']]=by.get(e['status'],0)+1
        return {'revision':REVISION,'entries':len(es),'by_status':by,'task_types':sorted({e['task_type'] for e in es if e['status']=='ACTIVE'}),
                'claim_limit':'Evidence-bound notes on adopted changes; data for evaluators/editors, no live authority (SHADOW)'}

def ablation(tasks,solve,library,task_type_of=lambda t:t['task_type'],k=3):
    """Same tasks, same solver, with and without library lessons. solve(task, lessons) -> score in [0,1]."""
    rows=[]
    for t in tasks:
        tt=task_type_of(t)
        on=float(solve(t,library.lookup(tt,k)));off=float(solve(t,library.lookup(tt,k,enabled=False)))
        rows.append({'task_type':tt,'with':on,'without':off,'delta':round(on-off,6)})
    n=len(rows) or 1
    return {'n':len(rows),'with':sum(r['with'] for r in rows)/n,'without':sum(r['without'] for r in rows)/n,
            'mean_delta':sum(r['delta'] for r in rows)/n,'worse':sum(r['delta']<0 for r in rows),'rows':rows}
