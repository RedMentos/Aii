"""WP-FS9 / BP3: scout probes decide which body answers (ScoutRoute, arXiv 2610.23443, 16.10.2026; idea only, own code).

One small scout model runs once over the request; its hidden state (a vector, e.g. the mean of the last layer) feeds one
logistic probe per target (B1_DETAIL, B2_GIST, TEACHER). A probe estimates P(this target answers correctly). The plan
asks the cheapest target whose probability reaches its threshold and falls back to the strongest one otherwise.
Equifinality in MoE (arXiv 2604.14419): router shape hardly matters, so no further router refinements; what matters is whom
to ask and that the estimate is calibrated. ``compare`` therefore reports log-loss and ECE of the probe against the scout's
own confidence as the baseline, and the cost saved at equal accuracy.
NumPy only, no runtime wiring (SHADOW): needs per-request competence labels of the real bodies and scout hidden states,
which do not exist yet (STEP2 labels have no scout features). Evidence on synthetic data only, said in every report.
"""
import numpy as np

TARGETS=('B2_GIST','B1_DETAIL','TEACHER')           # cheapest first
COST={'B2_GIST':1.,'B1_DETAIL':1.5,'TEACHER':8.}     # BOOT relative cost, not measured

def _sigmoid(z):return 1./(1.+np.exp(-np.clip(z,-30,30)))

class Probe:
    """L2-regularised logistic regression by Newton steps (no SciPy)."""
    def __init__(self,l2=1.):self.l2=l2;self.w=None;self.mu=None;self.sd=None;self.prior=.5
    def fit(self,X,y,iters=25):
        X=np.asarray(X,float);y=np.asarray(y,float)
        if len(X)<8 or y.min()==y.max():self.w=None;self.prior=float(y.mean()) if len(y) else .5;return self
        self.mu=X.mean(0);self.sd=X.std(0)+1e-6;Z=np.c_[(X-self.mu)/self.sd,np.ones(len(X))]
        w=np.zeros(Z.shape[1]);R=np.eye(Z.shape[1])*self.l2;R[-1,-1]=0
        for _ in range(iters):
            p=_sigmoid(Z@w);g=Z.T@(p-y)+R@w;H=(Z*(p*(1-p))[:,None]).T@Z+R+1e-9*np.eye(len(w))
            step=np.linalg.solve(H,g);w-=step
            if np.abs(step).max()<1e-7:break
        self.w=w;return self
    def predict(self,X):
        X=np.atleast_2d(np.asarray(X,float))
        if self.w is None:return np.full(len(X),self.prior)
        return _sigmoid(np.c_[(X-self.mu)/self.sd,np.ones(len(X))]@self.w)

def ece(p,y,bins=10):
    p=np.asarray(p,float);y=np.asarray(y,float);e=0.
    for lo in np.linspace(0,1,bins,endpoint=False):
        m=(p>=lo)&(p<lo+1./bins+(1e-12 if lo+1./bins>=1 else 0))
        if m.any():e+=m.mean()*abs(p[m].mean()-y[m].mean())
    return float(e)

def logloss(p,y):
    p=np.clip(np.asarray(p,float),1e-6,1-1e-6);y=np.asarray(y,float);return float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p)))

class ScoutRoute:
    def __init__(self,thresholds=None):
        self.probes={t:Probe() for t in TARGETS};self.th=dict(thresholds or {'B2_GIST':.8,'B1_DETAIL':.8,'TEACHER':0.})
    def fit(self,X,labels):
        """labels: {target: 0/1 per row (did this target answer correctly)}; a target without labels keeps its prior."""
        for t,y in labels.items():
            if t in self.probes:self.probes[t].fit(X,y)
        return self
    def probabilities(self,x):return {t:float(self.probes[t].predict(x)[0]) for t in TARGETS}
    def choose(self,x):
        """Cheapest target above its threshold, else the one with the highest probability (never blind)."""
        p=self.probabilities(x)
        for t in TARGETS:
            if p[t]>=self.th[t]:return {'target':t,'p':p,'reason':'cheapest above threshold'}
        t=max(p,key=p.get);return {'target':t,'p':p,'reason':'none above threshold; best estimate'}

def compare(route,X,labels,confidence):
    """Held-out comparison: probe vs scout confidence (one number per row, same for every target) and an always-ask-teacher
    / always-ask-cheapest baseline. Returns accuracy and cost of the chosen target per policy plus calibration per target."""
    X=np.asarray(X,float);n=len(X);rep={'n':n,'targets':{}}
    for t in TARGETS:
        if t not in labels:continue
        y=np.asarray(labels[t],float);pp=route.probes[t].predict(X);pc=np.clip(np.asarray(confidence,float),0,1)
        rep['targets'][t]={'logloss_probe':logloss(pp,y),'logloss_confidence':logloss(pc,y),'ece_probe':ece(pp,y),'ece_confidence':ece(pc,y)}
    def policy(pick):
        ok=cost=0.
        for i in range(n):
            t=pick(i);ok+=float(labels[t][i]);cost+=COST[t]
        return {'accuracy':ok/n,'cost':cost/n}
    rep['policy']={'scout':policy(lambda i:route.choose(X[i])['target']),'always_teacher':policy(lambda i:'TEACHER'),
                   'always_cheapest':policy(lambda i:'B2_GIST')}
    rep['evidence']='synthetic or supplied data; no runtime wiring'
    return rep
