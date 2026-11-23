"""WP-T4 A-plane teacher/student (A1-A3, §18.1-18.4, §18.11, G9B, G10).

1. A3 student beyond shadow T1. StudentEvaluation packets (student route vs. teacher route) build an agreement window.
   T2 'fallback' lets the student route only when the teacher path (Needle/C2 control) is unavailable and the student
   is in support. Gate: >= GATE_N comparisons, agreement >= GATE_AGREE, and the newest RECENT comparisons are not worse
   than the earlier ones by more than RETENTION (retention gate). Promotion is a user command; the gate can refuse it.
   It is withdrawn automatically when the gate stops holding.
2. Text distillation (not LoRA): a small ridge head maps prompt features to teacher-answer features (A3 raw byte
   n-gram stem, no model needed). Held-out split by trace id. Solo success = cosine(prediction, teacher answer) above
   the floor and the nearest held-out answer is the right one. The head never writes output (authority 0); it is
   evidence for the internalisation loop (teacher.trial, solo).
3. Teacher removal as a real run: the same held-out set, trained with 100/75/50/25 % of the teacher traces, gives the
   reliance curve. Removing the teacher for a capability stays the user's call (teacher.remove).
"""
import hashlib
import time
from .common import dumps,uid

KEY='aplane-state';MODES=('shadow','fallback')
GATE_N=50;GATE_AGREE=.9;RECENT=25;RETENTION=.05;WINDOW=400
RIDGE=1.;SOLO_FLOOR=.3;MIN_TRACES=16;CURVE=(1.,.75,.5,.25)

def _mutate(store,fn):
    for attempt in (0,1):
        st,v=store.state(KEY);st=st or {'student_mode':'shadow','distill':None,'curves':[]};out=fn(st)
        try:store.set_state(KEY,st,expected=v);return out
        except ValueError:
            if attempt:raise

def state(store):return store.state(KEY)[0] or {'student_mode':'shadow','distill':None,'curves':[]}

# -- 1. A3 student T1 -> T2 -------------------------------------------------------------------------------------
def student_gate(store):
    import json
    rows=store.rows("SELECT payload FROM packets WHERE kind='StudentEvaluation' ORDER BY rowid DESC LIMIT ?",(WINDOW,))
    agree=[bool(json.loads(r['payload'])['agreement']) for r in rows][::-1]
    n=len(agree);rate=sum(agree)/n if n else None
    recent=agree[-RECENT:];early=agree[:-RECENT]
    r_rate=sum(recent)/len(recent) if recent else None;e_rate=sum(early)/len(early) if early else None
    retained=e_rate is None or r_rate is None or r_rate>=e_rate-RETENTION
    curve=[round(sum(agree[i:i+RECENT])/len(agree[i:i+RECENT]),4) for i in range(0,n,RECENT)]
    ok=n>=GATE_N and rate is not None and rate>=GATE_AGREE and retained
    return {'n':n,'agreement':round(rate,4) if rate is not None else None,'recent':r_rate,'earlier':e_rate,'retention_pass':bool(retained),
            'agreement_curve':curve,'pass':bool(ok),'gate':{'min_n':GATE_N,'min_agreement':GATE_AGREE,'retention_max_drop':RETENTION}}

def set_student_mode(store,mode):
    if mode not in MODES:raise ValueError(':aplane student shadow|fallback')
    if mode=='fallback':
        g=student_gate(store)
        if not g['pass']:raise ValueError('A3-Gate nicht bestanden: '+dumps({k:g[k] for k in ('n','agreement','retention_pass')}))
    _mutate(store,lambda st:st.__setitem__('student_mode',mode));return mode

def student_fallback(r,e,info):
    """Teacher path unavailable: the student may route (T2) if promoted, the gate still holds and it is in support."""
    if state(r.store).get('student_mode')!='fallback':return None
    if not student_gate(r.store)['pass']:
        _mutate(r.store,lambda st:st.__setitem__('student_mode','shadow'));r.store.log('aplane_student_demoted',e['event_id'],{});return None
    sr=r.learner.student_route(e)
    if not sr or sr.get('route') is None:return None
    r.store.log('aplane_student_fallback',e['event_id'],{'route':sr['route']})
    return sr['route'],info|{'source':'A3_STUDENT_FALLBACK','student':sr}

# -- 2./3. text distillation head + reliance curve --------------------------------------------------------------
def _features(rows):
    import numpy as np
    from .student_worker import raw_features
    X=np.stack([raw_features(t['prompt'][:4000] or ' ') for t in rows]);Y=np.stack([raw_features(t['target'][:4000] or ' ') for t in rows])
    return np.hstack([X,np.ones((len(X),1))]),Y

def _held_out(tid):return int(hashlib.sha256(tid.encode()).hexdigest()[:8],16)%4==0

def fit(rows,ridge=RIDGE):
    """Ridge head on centred targets: the shared answer template is the mean, the head must predict what differs."""
    import numpy as np
    X,Y=_features(rows);mu=Y.mean(0);d=X.shape[1]
    return {'W':np.linalg.solve(X.T@X+ridge*np.eye(d),X.T@(Y-mu)),'mu':mu}

def _unit(A):
    import numpy as np
    return A/np.maximum(np.linalg.norm(A,axis=1,keepdims=True),1e-12)

def evaluate(head,rows):
    """Held-out: centred cosine (the mean-answer baseline scores 0 here), nearest-answer retrieval, solo success."""
    import numpy as np
    X,Y=_features(rows);P=_unit(X@head['W']);T=_unit(Y-head['mu'])
    cos=(P*T).sum(1);hit=(P@T.T).argmax(1)==np.arange(len(rows));solo=(cos>=SOLO_FLOOR)&hit
    return {'n':len(rows),'mean_cosine':round(float(cos.mean()),4),'retrieval_at_1':round(float(hit.mean()),4),'chance':round(1/len(rows),4),
            'solo_success':round(float(solo.mean()),4),'baseline_cosine':0.,'solo':solo.tolist()}

def distill(r,capability=None,record_trials=True):
    """Train the small head on the teacher dataset, evaluate held-out, run the teacher-dropout curve."""
    if r.cfg['learning_mode']=='RECORD_ONLY':raise ValueError('RECORD_ONLY: keine Optimizer-Schritte. :learning shadow')
    from .agi import hub
    t=hub(r).teacher;rows=t.dataset(capability,limit=2048)
    rows=[x for x in rows if x['prompt'].strip() and x['target'].strip()]
    train=[x for x in rows if not _held_out(x['trace_id'])];test=[x for x in rows if _held_out(x['trace_id'])]
    if len(train)<MIN_TRACES or len(test)<4:raise ValueError(f'Zu wenig Lehrer-Spuren: {len(train)} Training / {len(test)} Holdout (mind. {MIN_TRACES}/4)')
    import numpy as np
    started=time.monotonic();W=fit(train);ev=evaluate(W,test)
    curve=[]
    for share in CURVE:  # teacher removal as a run: fewer teacher traces, same held-out prompts
        k=max(2,int(round(len(train)*share)));sub=sorted(train,key=lambda x:x['trace_id'])[:k]
        e=evaluate(fit(sub),test);curve.append({'teacher_share':share,'train':k,'solo_success':e['solo_success'],'mean_cosine':e['mean_cosine']})
    full=curve[0]['solo_success'] or 0.
    for c in curve:c['reliance']=round(1-c['solo_success']/full,4) if full else 1.
    eligible=ev['mean_cosine']>ev['baseline_cosine']+.1 and ev['retrieval_at_1']>2*ev['chance']
    did=uid('distill');path=r.home/'checkpoints'/(did+'.npz');path.parent.mkdir(parents=True,exist_ok=True);np.savez(path,weights=W['W'],target_mean=W['mu'])
    cap=capability or 'language'
    if record_trials:
        for ok in ev['solo']:t.trial(cap,bool(ok),teacher_present=False)
        for _ in ev['solo']:t.trial(cap,True,teacher_present=True)  # the reference answer itself is the paired outcome
    run={'id':did,'capability':cap,'train':len(train),'held_out':len(test),'stem':'utf8-signed-byte-ngrams-1-3-v1','ridge':RIDGE,
         'held_out_metrics':{k:v for k,v in ev.items() if k!='solo'},'curve':curve,'eligible':bool(eligible),'artifact':str(path.relative_to(r.home)),
         'duration_s':round(time.monotonic()-started,3),'authority':'EVIDENCE_ONLY_NO_OUTPUT','reliance':t.reliance(cap)}
    def f(st):st['distill']=run;st['curves']=(st.get('curves',[])+[{'id':did,'capability':cap,'curve':curve}])[-20:]
    _mutate(r.store,f);r.store.log('aplane_distill',None,{'id':did,'eligible':bool(eligible)})
    return run

def report(r):
    st=state(r.store)
    return {'student':{'mode':st.get('student_mode','shadow'),'gate':student_gate(r.store)},'distill':st.get('distill'),'curves':st.get('curves',[])[-5:],
            'claim_limit':'A3 fallback routes only when the teacher path is down; the distillation head is evidence for the internalisation loop, never output. Raw byte stem: lexical, not semantic.'}
