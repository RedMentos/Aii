#!/usr/bin/env python3
"""WP-BP10 / FS1: does ranking candidate futures by their executed outcome beat "closest predicted state to the goal"?
Registered in docs/BP10_WORLD_MODEL_WIRING.md (section FS1) before the first run. Software, real file operations (z12b world).
  PYTHONPATH=. python3 scripts/bp10_fs1_rank.py <out.json> [--seeds 221,222,223] [--train 4000] [--states 900] [--steps 3000] [--probe]
"""
import argparse,importlib.util,json,random,shutil,sys,tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_s=importlib.util.spec_from_file_location('z12b',Path(__file__).with_name('z12b_world_jepa.py'));z12b=importlib.util.module_from_spec(_s);_s.loader.exec_module(z12b)
_c=importlib.util.spec_from_file_location('z12c',Path(__file__).with_name('z12c_slot_world_jepa.py'));z12c=importlib.util.module_from_spec(_c);_c.loader.exec_module(z12c)
SLOTS,OPS,ACTIONS,NOOP=z12b.SLOTS,z12b.OPS,z12b.ACTIONS,z12b.NOOP
CLASSES=('E','D','N','S','L');K=6

def slot_class(f):
    """Task class of one slot from its 10 features: empty / dir / digits / short text / long text."""
    if f[1]>.5:return 'D'
    if f[0]<.5:return 'E'
    if f[4]>.5:return 'N'
    return 'L' if f[2]*8>np.log(80) else 'S'
def classes(x):return [slot_class(x[s*10:(s+1)*10]) for s in range(SLOTS)]
def matches(x,g):return sum(a==b for a,b in zip(classes(x),classes(g)))

def collect(work,seed,n,held,tag):
    """n states; per state K candidate actions executed for real in copies, plus a reachable goal (2 random covered ops)."""
    root=work/('walk-'+tag);root.mkdir();rng=random.Random(seed*13+(1 if tag=='train' else 2));covered=[i for i in range(NOOP) if i not in held];out=[]
    for _ in range(30):o,s=ACTIONS[rng.choice(covered)];z12b.do(root,o,s,rng)
    while len(out)<n:
        for _ in range(3):o,s=ACTIONS[NOOP if rng.random()<1/8 else rng.choice(covered)];z12b.do(root,o,s,rng)
        x=z12b.features(root);cp=work/'goalcopy';shutil.rmtree(cp,ignore_errors=True);shutil.copytree(root,cp)
        for _ in range(2):o,s=ACTIONS[rng.choice(covered)];z12b.do(cp,o,s,rng)
        xg=z12b.features(cp);cands=[]
        for i in rng.sample(range(len(ACTIONS)),K):
            shutil.rmtree(cp,ignore_errors=True);shutil.copytree(root,cp);o,s=ACTIONS[i];z12b.do(cp,o,s,rng)
            x2=z12b.features(cp);cands.append({'a':i,'x2':x2,'score':matches(x2,xg),'held':i in held})
        out.append({'x':x,'goal':xg,'cands':cands})
    shutil.rmtree(work/'goalcopy',ignore_errors=True);return out

def skill(chosen,states):
    """(chosen - random)/(oracle - random) on the mean score; also top-1 hit rate (chosen has the max score)."""
    ch=np.mean([st['cands'][j]['score'] for st,j in zip(states,chosen)]);rnd=np.mean([np.mean([c['score'] for c in st['cands']]) for st in states])
    orc=np.mean([max(c['score'] for c in st['cands']) for st in states]);hit=np.mean([st['cands'][j]['score']==max(c['score'] for c in st['cands']) for st,j in zip(states,chosen)])
    return {'chosen':round(float(ch),4),'random':round(float(rnd),4),'oracle':round(float(orc),4),'skill':round(float((ch-rnd)/max(1e-9,orc-rnd)),4),'top1':round(float(hit),4)}

def predicted(m,st):
    A=np.array([z12c.slot_action(c['a']) for c in st['cands']]);X=np.repeat(st['x'][None],len(A),0);p,_=m.predict(X,A);return p  # (K,S,k)

def choose_distance(m,states):
    out=[]
    for st in states:
        p=predicted(m,st);zg=m.latent(st['goal'][None])[0];out.append(int(np.argmin(((p-zg)**2).sum((1,2)))))
    return out

class Ranker:
    """score(candidate) = sum over slots of w[goal class of the slot] . predicted slot latent (+ bias per goal class); trained pairwise
    (logistic loss) on executed outcomes: the candidate whose real outcome matched the goal in more slots should score higher."""
    def __init__(self,k,lr=.05,l2=1e-3,epochs=60,seed=0):self.k=k;self.lr=lr;self.l2=l2;self.epochs=epochs;self.rng=np.random.default_rng(seed)
    def feats(self,p,goal_cls):
        f=np.zeros((p.shape[0],len(CLASSES),self.k+1))
        for s,gc in enumerate(goal_cls):f[:,CLASSES.index(gc),:self.k]+=p[:,s,:];f[:,CLASSES.index(gc),self.k]+=1.
        return f.reshape(p.shape[0],-1)
    def fit(self,m,states,shuffle=False):
        F=[];Y=[]
        for st in states:
            F.append(self.feats(predicted(m,st),classes(st['goal'])));Y.append(np.array([c['score'] for c in st['cands']],float))
        if shuffle:
            for y in Y:self.rng.shuffle(y)  # control: outcomes detached from candidates
        self.w=np.zeros(F[0].shape[1])
        pairs=[(i,a,b) for i,y in enumerate(Y) for a in range(len(y)) for b in range(len(y)) if y[a]>y[b]]
        for _ in range(self.epochs):
            self.rng.shuffle(pairs)
            for i,a,b in pairs:
                d=F[i][a]-F[i][b];sg=1/(1+np.exp(np.clip(self.w@d,-30,30)));self.w+=self.lr*(sg*d-self.l2*self.w)
        return self
    def choose(self,m,states):return [int(np.argmax(self.feats(predicted(m,st),classes(st['goal']))@self.w)) for st in states]

def run_seed(seed,a):
    from v13.world_jepa_slots import SlotWorldJEPA
    work=Path(tempfile.mkdtemp(prefix='bp10-%d-'%seed));rng=random.Random(seed);held=set(rng.sample(range(NOOP),4))
    train=z12b.collect_train(work,seed,a.train,held);nv=len(train)//10;fit,val=train[:-nv],train[-nv:];val=[r for r in val if not r['world']]
    X=np.array([r['x'] for r in fit]);A=np.array([z12c.slot_action(r['a']) for r in fit]);X2=np.array([r['x2'] for r in fit])
    Xv=np.array([r['x'] for r in val]);Av=np.array([z12c.slot_action(r['a']) for r in val]);X2v=np.array([r['x2'] for r in val])
    m=SlotWorldJEPA(SLOTS,seed=seed).fit(X,A,X2,steps=a.steps).calibrate(Xv,Av,X2v)
    rank_train=collect(work,seed,a.states,held,'train');test=collect(work,seed,a.states//3,held,'test')
    heldtest=[{'x':st['x'],'goal':st['goal'],'cands':[c for c in st['cands'] if c['held'] or True]} for st in test]
    res={'seed':seed,'distance':skill(choose_distance(m,test),test),'random_ref':skill([0]*len(test),test)}
    if not a.probe:
        r=Ranker(m.k,seed=seed).fit(m,rank_train);res['ranker']=skill(r.choose(m,test),test)
        r0=Ranker(m.k,seed=seed).fit(m,rank_train,shuffle=True);res['ranker_shuffled_labels']=skill(r0.choose(m,test),test)
    shutil.rmtree(work,ignore_errors=True);return res

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--seeds',default='221,222,223');ap.add_argument('--train',type=int,default=4000)
    ap.add_argument('--states',type=int,default=900);ap.add_argument('--steps',type=int,default=3000);ap.add_argument('--probe',action='store_true');a=ap.parse_args()
    runs=[run_seed(int(s),a) for s in a.seeds.split(',')];mean=lambda k,f:float(np.mean([r[k][f] for r in runs]))
    out={'runs':runs,'mean_skill':{k:round(mean(k,'skill'),4) for k in runs[0] if isinstance(runs[0][k],dict)}}
    if a.probe:out['room']='ROOM' if out['mean_skill']['distance']<.8 else 'NO_ROOM'
    else:
        s=out['mean_skill'];crit={'1_rank_beats_distance_by_0.10':s['ranker']>=s['distance']+.10,'2_rank_skill_ge_0.6':s['ranker']>=.6,'3_shuffled_control_le_0.15':s['ranker_shuffled_labels']<=.15}
        out['criteria']=crit;out['verdict']='BP10_FS1_PASS' if all(crit.values()) else 'BP10_FS1_FAIL'
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(out,indent=1,sort_keys=True));print(json.dumps({k:v for k,v in out.items() if k!='runs'},indent=1))
if __name__=='__main__':main()
