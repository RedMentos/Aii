#!/usr/bin/env python3
"""Train the learned second-opinion reader S1 (v13/userrules_second.py) on KNOWN sentences only and choose its threshold by
leave-one-set-out cross-validation (PREREG v8): the threshold that catches the most rule sentences the fixed reader v8 misses
(no restriction found), while S1 adds a question to at most 10 % of all no-rule sentences. Deterministic (fixed seed, full batch).
Writes v13/userrules_second.json and cv_second.json here. Refuses sealed sets (holdout_de5, round 8).
Usage: train_second.py"""
import glob,hashlib,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];B=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from v13 import userrules as U, userrules_second as S

def known_files():
    f=[B/'continuation-20261021/user-rules'/n for n in ('dev.json','holdout_author.json','model_cohort.json','model_cohort_round2.json')]
    f+=[Path(p) for p in sorted(glob.glob(str(B/'continuation-20261022/user-rules-v[3-7]/cohort_round*.json')))]
    f+=[Path(p) for p in sorted(glob.glob(str(B/'continuation-20261022/user-rules-v[5-7]/holdout_de*.json')))]
    f+=[B/'continuation-20261022/user-rules-v7/dev_v7.json',HERE/'dev_v8.json']
    for p in f:
        if 'holdout_de5' in p.name or 'round8' in p.name:raise SystemExit('sealed set in training data: '+str(p))
    return f

RULE=('FORBID','ASK_FIRST','UNCLEAR')

def matrix(texts):
    X=np.zeros((len(texts),S.DIM),np.float32)
    for i,t in enumerate(texts):
        f=S.features(t);X[i,f]=1/max(len(f),1)**0.5
    return X

def fit(X,y,l2=1e-3,epochs=400,lr=0.5):
    w=np.zeros(X.shape[1],np.float32);b=0.0;pos=y.mean();cw=np.where(y==1,0.5/pos,0.5/(1-pos)).astype(np.float32)
    m=np.zeros_like(w);v=np.zeros_like(w);mb=vb=0.0
    for e in range(1,epochs+1):  # full-batch Adam, deterministic
        p=1/(1+np.exp(-(X@w+b)));g=cw*(p-y)/len(y);gw=X.T@g+l2*w;gb=float(g.sum())
        m=0.9*m+0.1*gw;v=0.999*v+0.001*gw*gw;mb=0.9*mb+0.1*gb;vb=0.999*vb+0.001*gb*gb
        w-=lr*(m/(1-0.9**e))/(np.sqrt(v/(1-0.999**e))+1e-8)*0.02;b-=lr*(mb/(1-0.9**e))/((vb/(1-0.999**e))**0.5+1e-8)*0.02
    return w,b

def base_restricts(text):
    return any(c['kind'] in RULE for c in U.parse(text,second='off'))

def main():
    files=known_files();rows=[]
    for g,p in enumerate(files):
        for it in json.loads(p.read_text())['items']:rows.append((g,it['text'],it['kind']))
    texts=[r[1] for r in rows];y=np.array([r[2] in RULE for r in rows],np.float32);grp=np.array([r[0] for r in rows])
    X=matrix(texts);base=np.array([base_restricts(t) for t in texts]);cv=np.zeros(len(rows))
    for g in range(len(files)):
        te=grp==g;w,b=fit(X[~te],y[~te]);cv[te]=1/(1+np.exp(-(X[te]@w+b)))
    kinds=np.array([r[2] for r in rows]);miss=(y==1)&~base;none=kinds=='NONE';free=none&~base
    grid=[];best=None
    for t in np.round(np.arange(0.05,0.96,0.01),2):
        caught=int((miss&(cv>=t)).sum());added=int((free&(cv>=t)).sum());ok=added<=0.10*none.sum()
        grid.append({'t':float(t),'caught':caught,'added_none':added,'ok':bool(ok)})
        if ok and (best is None or caught>best['caught'] or (caught==best['caught'] and t>best['t'])):best=grid[-1]
    w,b=fit(X,y);thr=best['t']
    model={'schema':'USER_RULES_SECOND_V1','dim':S.DIM,'bias':round(float(b),5),'threshold':thr,
           'weights':{str(i):round(float(x),5) for i,x in enumerate(w) if abs(x)>=1e-5},
           'trained_on':{str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
           'note':'caution only: asked only when the fixed reader finds no restriction; a yes adds an open question about everything'}
    (ROOT/'v13/userrules_second.json').write_text(json.dumps(model,separators=(',',':'))+'\n')
    full=1/(1+np.exp(-(X@w+b)))
    out={'files':[str(p.relative_to(B)) for p in files],'sentences':len(rows),'rule_sentences':int(y.sum()),'none_sentences':int(none.sum()),
         'base_misses':int(miss.sum()),'base_free_none':int(free.sum()),'chosen':best,'grid':grid,
         'per_set_cv':[{'set':str(files[g].relative_to(B)),'misses':int((miss&(grp==g)).sum()),'caught':int((miss&(grp==g)&(cv>=thr)).sum()),
                        'none':int((none&(grp==g)).sum()),'added':int((free&(grp==g)&(cv>=thr)).sum())} for g in range(len(files))],
         'train_fit':{'misses_caught':int((miss&(full>=thr)).sum()),'added_none':int((free&(full>=thr)).sum())},
         'cv_missed_texts':[texts[i] for i in np.where(miss&(cv<thr))[0]]}
    (HERE/'cv_second.json').write_text(json.dumps(out,ensure_ascii=False,indent=1)+'\n')
    print(json.dumps({k:out[k] for k in ('sentences','rule_sentences','none_sentences','base_misses','base_free_none','chosen','train_fit')}))

if __name__=='__main__':main()
