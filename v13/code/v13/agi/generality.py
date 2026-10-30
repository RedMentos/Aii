"""WP-AG12 generality eval: does V13 become more general over time, not just "do mechanisms run".

A fixed, versioned suite of procedurally generated tasks (no model and no network needed to
build or score it) is answered by a pluggable solver. Each run is stored per generation so the
curves show: seen vs unseen task families, transfer, forgetting between runs, planning depth
and calibration. Holdout prompts are registered so that no training/distillation dataset can
contain them (guard_training). Acceptance (does a mechanism run) stays separate.

Solver contract: solver(view) -> {'answer': str, 'confidence': float in [0,1]} where view has
id/family/prompt/level but never the answer. Exceptions count as wrong with confidence 0.
"""
import math
import random
import time
from ..common import digest,dumps,atomic_write,Cancelled,uid
from .base import StateBox,clamp01

KEY='G12_GENERALITY_EVAL';REVISION='g12-generality-v1'
SUITE_VERSION='g12-suite-v1'
HISTORY=120
HOLDOUT_MAX_SUITES=32
HOLDOUT_MAX_DIGESTS=2048
INTERVAL_S=30*86400.  # monthly by default (FORSCHUNG §9 #12)

# family: (split, transfer_source or None, levels). 'seen' families may appear in practice/training,
# 'unseen' families are holdout: never in any dataset. Transfer pairs measure source→target lift.
FAMILIES={
 'arith_add':('seen',None,(1,2,3)),
 'reverse_word':('seen',None,(1,2,3)),
 'seq_next':('seen',None,(1,2,3)),
 'arith_mul':('unseen','arith_add',(1,2,3)),
 'sort_letters':('unseen','reverse_word',(1,2,3)),
 'rule_map':('unseen','seq_next',(1,2,3)),
 'grid_path':('unseen',None,(2,4,6,8)),   # planning depth axis
}
PER_LEVEL=4
# English first (user decision 2026-10-09); German comes later as a learning test with the same task logic.
LANGS=('en','de')
WORDS={'en':('apple','bread','window','garden','dog','island','candle','lamp','moon','fog','oven','rain','sun','table','bird','cloud'),
       'de':('apfel','brot','fenster','garten','hund','insel','kerze','lampe','mond','nebel','ofen','regen','sonne','tisch','vogel','wolke')}
TEXT={'en':{'add':'Compute: {a} + {b} = ?','mul':'Compute: {a} * {b} = ?','rev':'Write backwards: {w}','sort':'Sort the letters alphabetically: {w}',
            'seq':'Continue: {s}, ?','rule':'Examples: {ex}. Apply the same rule: {q}->?','grid':'Shortest path from S to Z (steps up/down/left/right, # is a wall):'},
      'de':{'add':'Rechne: {a} + {b} = ?','mul':'Rechne: {a} * {b} = ?','rev':'Schreibe rückwärts: {w}','sort':'Sortiere die Buchstaben alphabetisch: {w}',
            'seq':'Setze fort: {s}, ?','rule':'Beispiele: {ex}. Wende dieselbe Regel an: {q}->?','grid':'Kürzester Weg von S nach Z (Schritte oben/unten/links/rechts, # ist Wand):'}}

def _gen(family,level,rng,lang='en'):
    T=TEXT[lang];W=WORDS[lang]
    if family=='arith_add':
        a,b=rng.randrange(10**level),rng.randrange(10**level);return T['add'].format(a=a,b=b),str(a+b)
    if family=='arith_mul':
        a,b=rng.randrange(2,10**level),rng.randrange(2,10);return T['mul'].format(a=a,b=b),str(a*b)
    if family=='reverse_word':
        w=''.join(rng.choice(W) for _ in range(level));return T['rev'].format(w=w),w[::-1]
    if family=='sort_letters':
        w=''.join(rng.choice(W) for _ in range(level));return T['sort'].format(w=w),''.join(sorted(w))
    if family=='seq_next':
        a,d=rng.randrange(1,20),rng.randrange(1,4*level+2);s=[a+d*i for i in range(3+level)]
        return T['seq'].format(s=', '.join(map(str,s))),str(a+d*(3+level))
    if family=='rule_map':
        # few-shot rule induction: hidden letter shift k on short words (ARC-style "infer the rule")
        k=rng.randrange(1,4+level);shift=lambda w:''.join(chr((ord(c)-97+k)%26+97) for c in w)
        ex=[rng.choice(W) for _ in range(2+level)];q=rng.choice(W)
        return T['rule'].format(ex='; '.join(f'{w}->{shift(w)}' for w in ex),q=q),shift(q)
    if family=='grid_path':
        # shortest path length on an open n×n grid with walls; answer is BFS distance (planning depth ≈ level)
        n=level+2
        while True:
            walls={(rng.randrange(n),rng.randrange(n)) for _ in range(n)}
            s,g=(0,0),(n-1,n-1);walls-= {s,g};d=_bfs(n,walls,s,g)
            if d is not None:break
        rows=[''.join('S' if (r,c)==s else 'Z' if (r,c)==g else '#' if (r,c) in walls else '.' for c in range(n)) for r in range(n)]
        return T['grid']+'\n'+'\n'.join(rows),str(d)
    raise ValueError('Unbekannte Aufgabenfamilie: '+family)

def _bfs(n,walls,s,g):
    seen={s:0};frontier=[s]
    while frontier:
        nxt=[]
        for r,c in frontier:
            for p in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                if 0<=p[0]<n and 0<=p[1]<n and p not in walls and p not in seen:seen[p]=seen[(r,c)]+1;nxt.append(p)
        frontier=nxt
    return seen.get(g)

def build_suite(seed=13,families=None,per_level=PER_LEVEL,lang='en'):
    if lang not in LANGS:raise ValueError('lang en|de')
    """Deterministic: same seed/version → identical items and suite hash."""
    fam=families or FAMILIES;items=[]
    for name in sorted(fam):
        split,source,levels=fam[name]
        for level in levels:
            rng=random.Random(f'{SUITE_VERSION}:{seed}:{name}:{level}')  # same task logic in every language
            for i in range(per_level):
                prompt,answer=_gen(name,level,rng,lang)
                items.append({'id':digest(f'{SUITE_VERSION}:{lang}:{name}:{level}:{i}:{prompt}')[:16],'family':name,'lang':lang,'split':split,
                              'transfer_source':source,'level':level,'prompt':prompt,'answer':answer})
    return {'version':SUITE_VERSION,'seed':seed,'lang':lang,'hash':digest(dumps([[i['id'],i['answer']] for i in items])),'items':items}

def normalize(a):return ' '.join(str(a).strip().casefold().split())

def _holdout_digest_ok(value):
    return (type(value) is str and len(value)==64
            and all(ch in '0123456789abcdef' for ch in value))

def _holdout_list_ok(values):
    return (type(values) is list and 0 < len(values) <= HOLDOUT_MAX_DIGESTS
            and values == sorted(set(values))
            and all(_holdout_digest_ok(v) for v in values))

def _validated_holdout_registry(st):
    """Fail closed on damaged or incomplete durable historical exclusion state."""
    reg=st.get('holdout_registry')
    if (type(reg) is not dict or len(reg)>HOLDOUT_MAX_SUITES
            or type(st.get('holdout_history_unknown')) is not bool
            or type(st.get('runs')) is not list):
        raise ValueError('AG12_HOLDOUT_INTEGRITY')
    union=set()
    for suite_hash,values in reg.items():
        if not _holdout_digest_ok(suite_hash) or not _holdout_list_ok(values):
            raise ValueError('AG12_HOLDOUT_INTEGRITY')
        union.update(values)
    if (len(union)>HOLDOUT_MAX_DIGESTS
            or st.get('holdout')!=sorted(union)
            or st.get('suite_hash') not in reg):
        raise ValueError('AG12_HOLDOUT_INTEGRITY')
    if not st['holdout_history_unknown']:
        if any(type(r) is not dict or r.get('suite_hash') not in reg
               for r in st['runs']):
            raise ValueError('AG12_HOLDOUT_INTEGRITY')
    return reg

def registered_holdout_digests(store):
    """Read-only union of registered EN/DE unseen prompts for training consumers.

    Evaluation suites remain language-local. Missing state is not a reason to
    create a new suite; an existing invalid or unknown-history state vetoes
    candidate reuse in *either* language.
    """
    hold=set()
    for key in (KEY,KEY+'_DE'):
        st,version=store.state(key,None)
        if st is None and version==0:
            continue
        if type(st) is not dict or st.get('revision')!=REVISION:
            raise ValueError('AG12_HOLDOUT_INTEGRITY')
        _validated_holdout_registry(st)
        if st['holdout_history_unknown']:
            raise ValueError('AG12_HOLDOUT_HISTORY_UNKNOWN')
        hold.update(st['holdout'])
    return hold

def _solver_confidence(value):
    """Reject malformed solver confidence before the unchanged AG12 scorer."""
    if type(value) is bool:
        raise ValueError('AG12_INVALID_CONFIDENCE')
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('AG12_INVALID_CONFIDENCE') from exc
    if not math.isfinite(number):
        raise ValueError('AG12_INVALID_CONFIDENCE')
    return clamp01(number)

def calibration(pairs,bins=10):
    """pairs: [(confidence, correct)]. Returns ECE, Brier and reliability bins."""
    if not pairs:return {'ece':None,'brier':None,'bins':[]}
    out=[];ece=0.;n=len(pairs)
    for b in range(bins):
        lo,hi=b/bins,(b+1)/bins
        sel=[(c,k) for c,k in pairs if lo<=c<hi or (b==bins-1 and c==1.)]
        if not sel:continue
        conf=sum(c for c,_ in sel)/len(sel);acc=sum(k for _,k in sel)/len(sel);ece+=len(sel)/n*abs(conf-acc)
        out.append({'lo':lo,'hi':hi,'n':len(sel),'confidence':round(conf,4),'accuracy':round(acc,4)})
    return {'ece':round(ece,4),'brier':round(sum((c-k)**2 for c,k in pairs)/n,4),'bins':out}

def _mean(xs):return round(sum(xs)/len(xs),4) if xs else None

def summarize(suite,results,previous=None):
    by={i['id']:i for i in suite['items']};fam={};lvl={}
    for r in results:
        it=by[r['id']];fam.setdefault(it['family'],[]).append(r['correct']);lvl.setdefault((it['family'],it['level']),[]).append(r['correct'])
    split=lambda s:[r['correct'] for r in results if by[r['id']]['split']==s]
    transfer={}
    for name,(sp,src,_) in FAMILIES.items():
        if src and name in fam and src in fam:transfer[f'{src}->{name}']={'source':_mean(fam[src]),'target':_mean(fam[name]),
                                                                        'ratio':round(_mean(fam[name])/_mean(fam[src]),4) if _mean(fam[src]) else None}
    # planning depth: deepest grid level solved at ≥50 %
    depth=max([lv for (f,lv),v in lvl.items() if f=='grid_path' and _mean(v)>=.5],default=0)
    forgetting=None
    if previous:
        before=[i for i,ok in previous.items() if ok and i in by]
        now={r['id']:r['correct'] for r in results}
        lost=[i for i in before if now.get(i)==0]
        forgetting={'previously_correct':len(before),'now_wrong':len(lost),'rate':round(len(lost)/len(before),4) if before else None}
    return {'overall':_mean([r['correct'] for r in results]),'seen':_mean(split('seen')),'unseen':_mean(split('unseen')),
            'generalization_gap':(round(_mean(split('seen'))-_mean(split('unseen')),4) if split('seen') and split('unseen') else None),
            'families':{k:_mean(v) for k,v in sorted(fam.items())},'transfer':transfer,'planning_depth':depth,'forgetting':forgetting,
            'calibration':calibration([(r['confidence'],r['correct']) for r in results])}

class GeneralityEval:
    def __init__(self,store,home=None,seed=13,clock=time.time,interval_s=INTERVAL_S,lang='en'):
        self.s=store;self.home=home;self.clock=clock;self.interval_s=interval_s
        self.suite=build_suite(seed,lang=lang)
        self.box=StateBox(store,KEY if lang=='en' else KEY+'_DE',REVISION,
                          lambda:{'runs':[],'last_items':{},'holdout':[],'suite_hash':None})
        self.box.mutate(self._register)
    def _active_state(self):
        """Reject a stale instance after a same-language suite rotation."""
        st = self.box.load()[0]
        if st.get('suite_hash') != self.suite['hash']:
            raise ValueError('AG12_STALE_SUITE')
        return st
    def _current_runs(self):
        """Keep historical runs for audit but never mix suite identities in curves."""
        return [r for r in self._active_state()['runs'] if r.get('suite_hash') == self.suite['hash']]
    def _register(self,st):
        """Never evict historical unseen digests silently when rotating suites."""
        current=self.suite['hash']
        unseen=sorted({digest(normalize(i['prompt'])) for i in self.suite['items']
                       if i['split']=='unseen'})
        if not _holdout_list_ok(unseen):
            raise ValueError('AG12_HOLDOUT_INTEGRITY')
        if 'holdout_registry' in st:
            reg=dict(_validated_holdout_registry(st))
            unknown=st['holdout_history_unknown']
        else:
            # Migrate a single legacy active suite without inventing older seeds.
            reg={}
            prior=st.get('suite_hash')
            old=st.get('holdout',[])
            if type(st.get('runs')) is not list:
                raise ValueError('AG12_HOLDOUT_INTEGRITY')
            if prior is not None:
                if not _holdout_digest_ok(prior) or not _holdout_list_ok(old):
                    raise ValueError('AG12_HOLDOUT_INTEGRITY')
                reg[prior]=list(old)
            elif old:
                raise ValueError('AG12_HOLDOUT_INTEGRITY')
            legacy_unknown=st.get('holdout_history_unknown',False)
            if type(legacy_unknown) is not bool:
                raise ValueError('AG12_HOLDOUT_INTEGRITY')
            unknown=(legacy_unknown or any(
                type(r) is not dict or r.get('suite_hash') not in reg
                for r in st['runs']))
        if current in reg:
            if reg[current]!=unseen:
                raise ValueError('AG12_HOLDOUT_INTEGRITY')
        else:
            if len(reg)>=HOLDOUT_MAX_SUITES:
                raise ValueError('AG12_HOLDOUT_CAP')
            reg[current]=unseen
        union=sorted({h for values in reg.values() for h in values})
        if len(union)>HOLDOUT_MAX_DIGESTS:
            raise ValueError('AG12_HOLDOUT_CAP')
        if st.get('suite_hash') not in (None,current):
            st['last_items']={};st['last_by']={}
        st['suite_hash']=current
        st['holdout_registry']=reg
        st['holdout']=union
        st['holdout_history_unknown']=unknown
        _validated_holdout_registry(st)
    def guard_training(self,texts):
        """Exclude registered EN/DE historical unseen prompts; fail closed."""
        self._active_state()  # still reject stale same-language evaluators
        hold=registered_holdout_digests(self.s)
        bad=[t for t in texts if digest(normalize(t)) in hold]
        if bad:raise ValueError(f'AG12-Holdout im Trainingssatz ({len(bad)} Einträge)')
        return True
    def practice_items(self):
        """Only 'seen' tasks may enter practice, after historical exclusion checks."""
        items=[{k:i[k] for k in ('id','family','level','prompt','answer')}
               for i in self.suite['items'] if i['split']=='seen']
        self.guard_training([i['prompt'] for i in items])
        return items
    def due(self):
        runs=self._current_runs()
        return not runs or self.clock()-runs[-1]['finished']>=self.interval_s
    def run(self,solver,label='manual',cancel=None,deadline=None,generation=None,solver_name=None,include_results=False):
        """solver_name keeps one curve and one forgetting baseline per solver (C3, B1, B2, ensemble, ...).
        A solver may offer batch(views, cancel, deadline) -> {id: out}: lets a body adapter answer all items with
        one model before switching to the next (one resident body on the phone)."""
        self._active_state()
        started=self.clock();results=[];status='DONE';key=str(solver_name or 'default')[:32]
        views=[{k:it[k] for k in ('id','family','level','prompt')} for it in self.suite['items']]
        pre=None
        if callable(getattr(solver,'batch',None)):
            try:pre=solver.batch(views,cancel,deadline) or {}
            except Cancelled:pre={};status='INTERRUPTED'
            except Exception as exc:pre={};status='ERROR';self.s.log('generality_solver_error',None,{'error':type(exc).__name__+': '+str(exc)[:200]})
        for it,view in zip(self.suite['items'],views):
            if status!='DONE':break
            if cancel is not None and cancel.is_set():status='INTERRUPTED';break
            if deadline is not None and time.monotonic()>=deadline:status='DEADLINE';break
            try:
                if pre is not None:
                    if view['id'] not in pre:status=getattr(solver,'stopped',None) or 'INTERRUPTED';break
                    out=pre[view['id']] or {}
                else:out=solver(view) or {}
                ans=out.get('answer','');conf=_solver_confidence(out.get('confidence',0.))
            except Cancelled:status='INTERRUPTED';break
            except Exception as exc:ans,conf='',0.;out={'error':type(exc).__name__}
            results.append({'id':it['id'],'correct':int(normalize(ans)==normalize(it['answer'])),'confidence':conf})
        st=self._active_state()
        prev=st.get('last_by',{}).get(key) if key!='default' else st['last_items']
        summary=summarize(self.suite,results,prev or None)
        run={'label':str(label)[:64],'solver':key,'status':status,'started':started,'finished':self.clock(),'items':len(results),
             'generation':generation if generation is not None else self.s.generation_id,'suite_hash':self.suite['hash'],'summary':summary}
        def save(st):
            if st.get('suite_hash') != self.suite['hash']:
                raise ValueError('AG12_STALE_SUITE')
            st['runs']=(st['runs']+[run])[-HISTORY:]
            if status=='DONE':
                items={r['id']:r['correct'] for r in results}
                if key=='default':st['last_items']=items
                else:st.setdefault('last_by',{})[key]=items
        self.box.mutate(save)
        self._active_state()
        if self.home is not None:
            export = 'generality-last.json' if self.suite['lang']=='en' else 'generality-last-de.json'
            atomic_write(self.home/'exports'/export,dumps(run|{'results':results}))
        self.s.log('generality_eval',None,{'status':status,'solver':key,'overall':summary['overall'],'unseen':summary['unseen'],'items':len(results)})
        return (run | {'_results':results,'_feedback_nonce':uid('g12fb')}) if include_results else run
    def curve(self,axis='overall',solver=None):
        """Time series for one axis: overall|seen|unseen|generalization_gap|planning_depth|forgetting|ece; optionally one solver."""
        out=[]
        for r in self._current_runs():
            if solver is not None and r.get('solver','default')!=solver:continue
            s=r['summary'];v=(s['forgetting'] or {}).get('rate') if axis=='forgetting' else s['calibration']['ece'] if axis=='ece' else s.get(axis)
            out.append({'finished':r['finished'],'generation':r['generation'],'label':r['label'],'solver':r.get('solver','default'),'value':v})
        return out
    def report(self):
        st=self._active_state()
        runs=[r for r in st['runs'] if r.get('suite_hash') == self.suite['hash']]
        return {'revision':REVISION,'suite':{'version':SUITE_VERSION,'hash':self.suite['hash'],'lang':self.suite['lang'],'items':len(self.suite['items']),
                'families':{k:v[0] for k,v in FAMILIES.items()}},'runs':len(runs),'due':self.due(),
                'last':runs[-1] if runs else None,
                'solvers':sorted({r.get('solver','default') for r in runs}),
                'claim_limit':'Procedural text tasks only; body solvers answer without memory or tools (agi/solver.py)'}

# Reference solvers (tests, baselines). They are not V13 intelligence.
def oracle_solver(suite):
    ans={i['id']:i['answer'] for i in suite['items']}
    return lambda v:{'answer':ans[v['id']],'confidence':1.}
def null_solver(v):return {'answer':'','confidence':0.}
