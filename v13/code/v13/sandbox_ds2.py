"""WP-DS2 lab sandbox, part 2: combined curiosity+goal policy and grounding that generalizes. Lab only.

Builds on v13/sandbox.py (WP-DS1, frozen). Nothing in the runtime imports this module; Age-0 core, bodies and store
stay untouched (STEP8+ stays locked).

PART A  combined policy in the DS1 world (same TRUE table, same pilz at NEW_KIND_AT):
  lpgoal          AG5 learning progress + novelty (as 'lp') + the pragmatic hunger term of 'efe'
                  + NEW_BOOST while a word has had fewer than NEW_TRIES interactions (novelty channel: a word never
                  met before raises curiosity for that object, so the hunger goal cannot starve exploration of it)
  lpgoal_noboost  the same without the novelty channel (ablation)
PART B  word combinations + visible features in a second world (World2). Every object is (adjective or None, noun).
  Adjectives override part of the noun's behaviour (ADJ_EFFECT: with prob w the outcome is the adjective's outcome).
  Nouns carry visible features (VIS) such as rund/weich/hart/durchsichtig, as a stand-in for vision-lab features.
  At HOLDOUT_AT unseen items appear: three new adjective+noun combinations, three new nouns that look like known
  ones and behave like them (birne~apfel, ziegel~stein, vase~glas), and one misleading look-alike (wachsapfel looks
  like apfel but is not edible). A model-agnostic driver ('novelty' on item visits) explores; three passive learners
  see the same observations:
    flat     Dirichlet per whole item (DS1 learner); an unseen item starts uniform
    backoff  like flat, but an unseen item starts from its noun's table (no adjective, no features)
    feat     hierarchical: a log-linear model over item features (noun id, adjective id, visible features) gives a
             prior p_feat; the item posterior is Dirichlet(PRIOR_S * p_feat + counts). Generalizes to unseen
             combinations/nouns and is overruled by the item's own evidence (needed for wachsapfel).
METRICS first-encounter KL(true || prediction) of each held-out item (model state when it appears), interactions
  with the item until its KL <= KL_GOAL (None = never), wachsapfel P(EATEN) at first encounter.
"""
import math
import random
from . import sandbox as S
from .agi.curiosity import Curiosity,NOVELTY

REVISION='ds2-sandbox-v1'
NEW_BOOST=.6;NEW_TRIES=12
POLICIES_A=('lp','efe','lpgoal','lpgoal_noboost')

class AgentA(S.Agent):
    """DS1 agent plus the combined policies; the DS1 policies keep their exact DS1 value function."""
    def __init__(self,policy,rng):
        assert policy in POLICIES_A,policy
        if policy in('lp','efe'):super().__init__(policy,rng)
        else:
            self.policy=policy;self.rng=rng;self.alpha={};self.surprise={};self.visits={}
        self.word_visits={}
    def observe(self,word,action,y):
        super().observe(word,action,y);self.word_visits[word]=self.word_visits.get(word,0)+1
    def value(self,word,action,hunger):
        if self.policy in('lp','efe'):return super().value(word,action,hunger)
        key=(word,action);n=self.visits.get(key,0);a=self.counts(word,action)
        v=max(0.,Curiosity._lp(self.surprise.get(key,[])))+NOVELTY/math.sqrt(1+n)
        v+=S.PRAGMATIC*hunger*S.predictive(a)[S.OUTCOMES.index('EATEN')]*S.HUNGER_RELIEF.get(word,0.)
        if self.policy=='lpgoal' and self.word_visits.get(word,0)<NEW_TRIES:v+=NEW_BOOST
        return v

def run_a(policy,seed,steps=1500,every=25,new_kind_at=S.NEW_KIND_AT):
    """S.run with AgentA (same world, same metrics)."""
    orig=S.Agent
    try:
        S.Agent=AgentA;return S.run(policy,seed,steps=steps,every=every,new_kind_at=new_kind_at)
    finally:S.Agent=orig

# ---------------------------------------------------------------- PART B world
O=S.OUTCOMES;_d=S._d;ACTIONS=S.ACTIONS;K=S.K
BASE={w:S.TRUE[w] for w in('apfel','stein','kiste','glas',S.NOISE)}
BASE['birne']=BASE['apfel'];BASE['ziegel']=BASE['stein'];BASE['vase']=BASE['glas']
BASE['wachsapfel']={'push':_d(MOVED=.9,NOTHING=.1),'eat':_d(NOTHING=1),'touch':_d(NOTHING=1),'lift':_d(MOVED=1)}
VIS={'apfel':('rund','weich','rot'),'birne':('rund','weich','gruen'),'wachsapfel':('rund','weich','rot','glaenzend'),
     'stein':('rund','hart','schwer','grau'),'ziegel':('eckig','hart','schwer','rot'),
     'kiste':('eckig','holz','braun'),'glas':('durchsichtig','hart','glaenzend'),'vase':('durchsichtig','hart','rund'),
     S.NOISE:('eckig','schwer','bildschirm')}
ADJ_EFFECT={'zerbrechlich':{'push':(.5,'BROKE'),'lift':(.5,'BROKE')},
            'klebrig':{'push':(.7,'BLOCKED'),'lift':(.7,'BLOCKED')},
            'leuchtend':{'touch':(.8,'LIGHT')}}
TRAIN_ITEMS=((None,'apfel'),(None,'apfel'),(None,'stein'),(None,'kiste'),(None,'glas'),(None,S.NOISE),
             ('zerbrechlich','kiste'),('klebrig','apfel'),('leuchtend','stein'),('zerbrechlich','glas'))
HOLDOUT_COMBOS=(('zerbrechlich','apfel'),('klebrig','kiste'),('leuchtend','glas'))
HOLDOUT_LOOKALIKE=((None,'birne'),(None,'ziegel'),(None,'vase'))
HOLDOUT_MISLEAD=((None,'wachsapfel'),)
HOLDOUT=HOLDOUT_COMBOS+HOLDOUT_LOOKALIKE+HOLDOUT_MISLEAD
HOLDOUT_AT=900;PRIOR_S=4.;L2=.02;FIT_EVERY=20;FIT_ITERS=80;LR=.5
LEARNERS=('flat','backoff','feat')

def item_name(item):return item[1] if item[0] is None else f'{item[0]} {item[1]}'
def true2(item,action):
    adj,noun=item;p=list(BASE[noun][action])
    if adj and action in ADJ_EFFECT[adj]:
        w,out=ADJ_EFFECT[adj][action];p=[(1-w)*x for x in p];p[O.index(out)]+=w
    return p
def features(item):
    adj,noun=item;f=['noun:'+noun]+['vis:'+v for v in VIS[noun]]
    if adj:f.append('adj:'+adj)
    return f

class World2(S.World):
    def __init__(self,rng):
        self.rng=rng;self.objs={};self.n=0;self.hunger=.3;self.steps=0
        cells=[(x,y) for x in range(S.GRID) for y in range(S.GRID)];rng.shuffle(cells)
        self.agent=cells.pop()
        for it in TRAIN_ITEMS:self._add(it,cells.pop())
    def _add(self,item,cell):self.n+=1;self.objs[self.n]={'word':item_name(item),'item':item,'cell':cell}
    def add_item(self,item):
        free=[(x,y) for x in range(S.GRID) for y in range(S.GRID) if self.free((x,y))];self._add(item,self.rng.choice(free))
    def act(self,oid,action):
        o=self.objs[oid];p=true2(o['item'],action)
        y=self.rng.choices(range(K),weights=p)[0];out=O[y]
        if out=='MOVED':
            nb=[(o['cell'][0]+dx,o['cell'][1]+dy) for dx,dy in((1,0),(-1,0),(0,1),(0,-1))];nb=[c for c in nb if self.free(c)]
            if nb:o['cell']=self.rng.choice(nb)
        elif out in('EATEN','BROKE'):
            if out=='EATEN':self.hunger=max(0.,self.hunger-.5)
            self._respawn(oid)
        self.tick();return y

def softmax(z):
    m=max(z);e=[math.exp(x-m) for x in z];s=sum(e);return [x/s for x in e]

class FeatModel:
    """Log-linear p(y | item, action) = softmax(b[action] + sum_f W[f][action]); fit by full-batch gradient descent
    on the aggregated outcome counts with L2 on W (not on b)."""
    def __init__(self):self.b={a:[0.]*K for a in ACTIONS};self.W={}
    def logits(self,item,action):
        z=list(self.b[action])
        for f in features(item):
            w=self.W.get(f)
            if w:z=[x+y for x,y in zip(z,w[action])]
        return z
    def predict(self,item,action):return softmax(self.logits(item,action))
    def fit(self,data):
        """data: {(item, action): counts[K]}"""
        for f in{f for it,_ in data for f in features(it)}:self.W.setdefault(f,{a:[0.]*K for a in ACTIONS})
        n=sum(sum(c) for c in data.values()) or 1
        for _ in range(FIT_ITERS):
            gb={a:[0.]*K for a in ACTIONS};gW={f:{a:[0.]*K for a in ACTIONS} for f in self.W}
            for(it,a),c in data.items():
                tot=sum(c)
                if not tot:continue
                p=self.predict(it,a);g=[(tot*pi-ci)/n for pi,ci in zip(p,c)]
                gb[a]=[x+y for x,y in zip(gb[a],g)]
                for f in features(it):gW[f][a]=[x+y for x,y in zip(gW[f][a],g)]
            for a in ACTIONS:self.b[a]=[x-LR*y for x,y in zip(self.b[a],gb[a])]
            for f,ws in self.W.items():
                for a in ACTIONS:ws[a]=[x-LR*(y+L2*x) for x,y in zip(ws[a],gW[f][a])]

class Learners:
    def __init__(self):self.counts={};self.feat=FeatModel();self.since=0
    def c(self,item,action):return self.counts.get((item,action),[0]*K)
    def observe(self,item,action,y):
        c=self.counts.setdefault((item,action),[0]*K);c[y]+=1;self.since+=1
        if self.since>=FIT_EVERY:self.refit()
    def refit(self):self.feat.fit(self.counts);self.since=0
    def predict(self,learner,item,action):
        c=self.c(item,action)
        if learner=='flat':prior=[S.ALPHA0]*K
        elif learner=='backoff':
            nc=self.c((None,item[1]),action)  # the plain noun's own table
            if item[0] is None or not sum(nc):prior=[S.ALPHA0]*K
            else:prior=[PRIOR_S*p for p in S.predictive([S.ALPHA0+x for x in nc])]
        else:prior=[PRIOR_S*p for p in self.feat.predict(item,action)]
        return S.predictive([p+x for p,x in zip(prior,c)])
    def item_kl(self,learner,item):
        return sum(S.kl(true2(item,a),self.predict(learner,item,a)) for a in ACTIONS)/len(ACTIONS)

def run_b(seed,steps=2700,holdout_at=HOLDOUT_AT):
    """Novelty driver over item+action visits explores World2; flat/backoff/feat learn passively from the same data."""
    rng=random.Random(seed);world=World2(random.Random(seed*7919+3));drv=S.Agent('novelty',rng);L=Learners()
    first={};goal={};inter={};p_eat=None;added=False
    while world.steps<steps:
        if not added and world.steps>=holdout_at:
            L.refit()
            for it in HOLDOUT:world.add_item(it);inter[it]=0
            first={it:{l:round(L.item_kl(l,it),5) for l in LEARNERS} for it in HOLDOUT}
            p_eat=round(L.predict('feat',HOLDOUT_MISLEAD[0],'eat')[O.index('EATEN')],4)
            goal={it:{l:(0 if first[it][l]<=S.KL_GOAL else None) for l in LEARNERS} for it in HOLDOUT};added=True
        pick=drv.choose(world)
        if pick is None:world.tick();continue
        oid,act,path=pick
        for c in path:
            if world.steps>=steps:break
            world.move(c)
        if world.steps>=steps:break
        it=world.objs[oid]['item'];y=world.act(oid,act);drv.observe(item_name(it),act,y);L.observe(it,act,y)
        if added and it in inter:
            inter[it]+=1
            for l in LEARNERS:
                if goal[it][l] is None and L.item_kl(l,it)<=S.KL_GOAL:goal[it][l]=inter[it]
    seen=sorted({i for i,_ in L.counts},key=item_name)
    final={l:round(sum(L.item_kl(l,i) for i in seen)/len(seen),5) for l in LEARNERS}
    return {'seed':seed,'steps':world.steps,'first_kl':{item_name(i):v for i,v in first.items()},
            'to_goal':{item_name(i):v for i,v in goal.items()},'holdout_interactions':{item_name(i):v for i,v in inter.items()},
            'wachsapfel_feat_p_eaten_first':p_eat,'final_mean_item_kl':final,
            'wachsapfel_p_eaten_final':{l:round(L.predict(l,HOLDOUT_MISLEAD[0],'eat')[O.index('EATEN')],4) for l in LEARNERS}}
