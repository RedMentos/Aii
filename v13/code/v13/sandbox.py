"""WP-DS1 lab sandbox: a tiny 2D object world for embodiment-light and active-inference-style curiosity. Lab only.

Nothing in the runtime imports this module; it never touches the Age-0 core, bodies or the store (STEP8+ stays locked).

WORLD     GRID x GRID cells, one agent, objects named by words (apfel, stein, kiste, glas, fernseher; pilz appears at
          NEW_KIND_AT). The agent only sees the word. To act on an object it must walk next to it (each move = 1 step).
          Actions on an object: push / eat / touch / lift. The outcome is drawn from a hidden table TRUE[word][action]
          over OUTCOMES. fernseher is the noisy TV: every action gives a uniform random outcome (nothing to learn).
          MOVED relocates the object to a free neighbour cell, EATEN/BROKE respawn it elsewhere. Hunger rises per step
          and falls when something is EATEN (HUNGER_RELIEF).
MODEL     per (word, action) Dirichlet counts over OUTCOMES (prior ALPHA0). Grounding = the word now predicts what the
          body will feel when it acts on it, learned only from own interaction.
POLICIES  choose the (object, action) to try next; walking there is planned by BFS. All except random subtract
          MOVE_COST x distance as a tie-break.
  random    uniform over present (object, action)
  surprise  mean recent surprise (-log p / log K) of that (word, action); unvisited = 1 (prediction-error curiosity)
  novelty   1/sqrt(1+visits)
  lp        V13 AG5 Curiosity rule: max(0, learning progress over the surprise window) + NOVELTY/sqrt(1+visits)
  eig       expected information gain of one more try = I(outcome; parameters) under the Dirichlet
            = H[E p] - E[H(p)] (epistemic value of active inference)
  efe       eig + PRAGMATIC x hunger x P(EATEN) x relief (expected free energy with a hunger preference)
METRICS   mean KL(true || predictive) over the (word, action) pairs of present kinds, steps until it is <= KL_GOAL,
          share of interactions spent on fernseher, mean hunger, grounding accuracy (argmax prediction == true mode on
          pairs that have a unique mode).
"""
import math
import random
from collections import deque
from .agi.curiosity import Curiosity,NOVELTY

REVISION='ds1-sandbox-v1';DS2_REVISION='ds2-combined-v1';WORD_NOVELTY_GAIN=.3
COVERAGE_TARGET=8;COVERAGE_BONUS=.75;COVERAGE_HUNGER_MAX=.60  # Run347 preregistered lab-only policy
GRID=7;ACTIONS=('push','eat','touch','lift')
OUTCOMES=('NOTHING','MOVED','EATEN','BLOCKED','BROKE','SOUND','LIGHT')
K=len(OUTCOMES);ALPHA0=.5;NOISE='fernseher';NEW_KIND='pilz';NEW_KIND_AT=600
HUNGER_STEP=.004;HUNGER_RELIEF={'apfel':.5,'pilz':.3};PRAGMATIC=2.;MOVE_COST=1e-3;SURPRISE_WINDOW=8;KL_GOAL=.1

def _d(**kw):
    v=[kw.get(o,0.) for o in OUTCOMES];s=sum(v);return [x/s for x in v]
TRUE={
 'apfel':{'push':_d(MOVED=.9,NOTHING=.1),'eat':_d(EATEN=1),'touch':_d(NOTHING=1),'lift':_d(MOVED=1)},
 'stein':{'push':_d(BLOCKED=.95,MOVED=.05),'eat':_d(NOTHING=1),'touch':_d(NOTHING=.7,SOUND=.3),'lift':_d(BLOCKED=1)},
 'kiste':{'push':_d(MOVED=.8,BLOCKED=.2),'eat':_d(NOTHING=1),'touch':_d(SOUND=.5,NOTHING=.5),'lift':_d(MOVED=.6,BLOCKED=.4)},
 'glas':{'push':_d(MOVED=.6,BROKE=.4),'eat':_d(NOTHING=1),'touch':_d(SOUND=1),'lift':_d(MOVED=.7,BROKE=.3)},
 NOISE:{a:[1/K]*K for a in ACTIONS},
 NEW_KIND:{'push':_d(NOTHING=1),'eat':_d(EATEN=1),'touch':_d(LIGHT=.8,NOTHING=.2),'lift':_d(MOVED=1)}}
START_KINDS=('apfel','stein','kiste','glas',NOISE)
POLICIES=('random','surprise','novelty','lp','eig','efe','lp_goal','lp_goal_novelty','lp_goal_coverage')

def digamma(x):
    r=0.
    while x<6:r-=1/x;x+=1
    f=1/(x*x)
    return r+math.log(x)-.5/x-f*(1/12-f*(1/120-f*(1/252-f*(1/240-f/132))))

def predictive(alpha):
    s=sum(alpha);return [a/s for a in alpha]
def entropy(p):return -sum(x*math.log(x) for x in p if x>0)
def eig(alpha):
    """I(y; theta) for y ~ Cat(theta), theta ~ Dir(alpha): H[E p] - E[H(p)]."""
    a0=sum(alpha);eh=digamma(a0+1)-sum(a/a0*digamma(a+1) for a in alpha)
    return max(0.,entropy(predictive(alpha))-eh)
def kl(p,q):return sum(x*math.log(x/y) for x,y in zip(p,q) if x>0)
def mode(p):
    m=max(p);idx=[i for i,x in enumerate(p) if x>=m-1e-12];return idx[0] if len(idx)==1 else None

class World:
    def __init__(self,rng):
        self.rng=rng;self.objs={};self.n=0;self.hunger=.3;self.steps=0
        cells=[(x,y) for x in range(GRID) for y in range(GRID)];rng.shuffle(cells)
        self.agent=cells.pop()
        for w in START_KINDS+('apfel',):self._add(w,cells.pop())
    def _add(self,word,cell):self.n+=1;self.objs[self.n]={'word':word,'cell':cell}
    def free(self,c):
        return 0<=c[0]<GRID and 0<=c[1]<GRID and c!=self.agent and all(o['cell']!=c for o in self.objs.values())
    def _respawn(self,oid):
        free=[(x,y) for x in range(GRID) for y in range(GRID) if self.free((x,y))]
        if free:self.objs[oid]['cell']=self.rng.choice(free)
    def add_kind(self,word):
        free=[(x,y) for x in range(GRID) for y in range(GRID) if self.free((x,y))];self._add(word,self.rng.choice(free))
    def path(self,goal):
        """BFS from the agent to any free cell 4-adjacent to goal; returns the list of cells (excluding start)."""
        targets={(goal[0]+dx,goal[1]+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))}
        if self.agent in targets:return []
        prev={self.agent:None};q=deque([self.agent])
        while q:
            c=q.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                n=(c[0]+dx,c[1]+dy)
                if n in prev or not self.free(n):continue
                prev[n]=c
                if n in targets:
                    out=[]
                    while n!=self.agent:out.append(n);n=prev[n]
                    return out[::-1]
                q.append(n)
        return None
    def tick(self):self.steps+=1;self.hunger=min(1.,self.hunger+HUNGER_STEP)
    def move(self,cell):self.agent=cell;self.tick()
    def act(self,oid,action):
        o=self.objs[oid];p=TRUE[o['word']][action]
        y=self.rng.choices(range(K),weights=p)[0];out=OUTCOMES[y]
        if out=='MOVED':
            nb=[(o['cell'][0]+dx,o['cell'][1]+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))]
            nb=[c for c in nb if self.free(c)]
            if nb:o['cell']=self.rng.choice(nb)
        elif out in('EATEN','BROKE'):
            if out=='EATEN':self.hunger=max(0.,self.hunger-HUNGER_RELIEF.get(o['word'],0.))
            self._respawn(oid)
        self.tick();return y

class Agent:
    def __init__(self,policy,rng):
        assert policy in POLICIES,policy
        self.policy=policy;self.rng=rng;self.alpha={};self.surprise={};self.visits={};self.word_visits={}
    def counts(self,word,action):return self.alpha.setdefault((word,action),[ALPHA0]*K)
    def observe(self,word,action,y):
        a=self.counts(word,action);s=-math.log(predictive(a)[y])/math.log(K)
        a[y]+=1;key=(word,action)
        self.surprise[key]=(self.surprise.get(key,[])+[min(1.,s)])[-2*SURPRISE_WINDOW:]
        self.visits[key]=self.visits.get(key,0)+1
        self.word_visits[word]=self.word_visits.get(word,0)+1
    def value(self,word,action,hunger):
        key=(word,action);n=self.visits.get(key,0);a=self.counts(word,action)
        if self.policy=='surprise':
            s=self.surprise.get(key,[]);return 1. if not s else sum(s[-SURPRISE_WINDOW:])/len(s[-SURPRISE_WINDOW:])
        if self.policy=='novelty':return 1/math.sqrt(1+n)
        if self.policy in ('lp','lp_goal','lp_goal_novelty','lp_goal_coverage'):
            intrinsic=max(0.,Curiosity._lp(self.surprise.get(key,[])))+NOVELTY/math.sqrt(1+n)
            if self.policy=='lp':return intrinsic
            pragmatic=PRAGMATIC*hunger*predictive(a)[OUTCOMES.index('EATEN')]*HUNGER_RELIEF.get(word,0.)
            word_novelty=(WORD_NOVELTY_GAIN/math.sqrt(1+self.word_visits.get(word,0))) if self.policy=='lp_goal_novelty' else 0.
            coverage=(COVERAGE_BONUS*max(0.,1-n/COVERAGE_TARGET)
                      if self.policy=='lp_goal_coverage' and hunger<COVERAGE_HUNGER_MAX else 0.)
            return intrinsic+pragmatic+word_novelty+coverage
        v=eig(a)
        if self.policy=='efe':v+=PRAGMATIC*hunger*predictive(a)[OUTCOMES.index('EATEN')]*HUNGER_RELIEF.get(word,0.)
        return v
    def choose(self,world):
        opts=[]
        for oid,o in world.objs.items():
            p=world.path(o['cell'])
            if p is None:continue
            for act in ACTIONS:opts.append((oid,act,p))
        if not opts:return None
        if self.policy=='random':return self.rng.choice(opts)
        return max(opts,key=lambda t:(self.value(world.objs[t[0]]['word'],t[1],world.hunger)-MOVE_COST*len(t[2]),self.rng.random()))

def model_kl(agent,kinds):
    vals=[kl(TRUE[w][a],predictive(agent.counts(w,a))) for w in kinds for a in ACTIONS];return sum(vals)/len(vals)
def grounding(agent,kinds):
    pairs=[(w,a) for w in kinds for a in ACTIONS if mode(TRUE[w][a]) is not None]
    return sum(mode(predictive(agent.counts(w,a)))==mode(TRUE[w][a]) for w,a in pairs)/len(pairs)

def run(policy,seed,steps=1500,every=25,new_kind_at=NEW_KIND_AT):
    """One episode. Returns the KL curve, steps to KL_GOAL (phase 1 and after the new kind), noise share, hunger, grounding."""
    rng=random.Random(seed);world=World(random.Random(seed*7919+1));agent=Agent(policy,rng)
    kinds=list(START_KINDS);curve=[];acts=0;noise=0;hunger=0.;first=None;new_first=None;mark=every
    while world.steps<steps:
        if new_kind_at is not None and world.steps>=new_kind_at and NEW_KIND not in kinds:world.add_kind(NEW_KIND);kinds.append(NEW_KIND)
        pick=agent.choose(world)
        if pick is None:world.tick();continue
        oid,act,path=pick
        for c in path:
            if world.steps>=steps:break
            world.move(c);hunger+=world.hunger
        if world.steps>=steps:break
        word=world.objs[oid]['word'];y=world.act(oid,act);hunger+=world.hunger
        agent.observe(word,act,y);acts+=1;noise+=word==NOISE;k=model_kl(agent,kinds)
        if world.steps>=mark:curve.append((world.steps,round(k,5)));mark+=every
        if first is None and k<=KL_GOAL and NEW_KIND not in kinds:first=world.steps
        if NEW_KIND in kinds and new_first is None and kl_kind(agent,NEW_KIND)<=KL_GOAL:new_first=world.steps-new_kind_at
    return {'policy':policy,'seed':seed,'steps':world.steps,'curve':curve,'steps_to_goal':first,
            'new_kind_steps_to_goal':new_first,
            'new_kind_interactions':sum(agent.visits.get((NEW_KIND,a),0) for a in ACTIONS),
            'new_kind_final_kl':round(kl_kind(agent,NEW_KIND),5) if NEW_KIND in kinds else None,
            'interactions':acts,'noise_share':round(noise/max(1,acts),4),
            'mean_hunger':round(hunger/max(1,world.steps),4),'final_kl':round(model_kl(agent,kinds),5),
            'final_kl_learnable':round(model_kl(agent,[k for k in kinds if k!=NOISE]),5),'grounding':round(grounding(agent,kinds),4)}
def kl_kind(agent,word):return sum(kl(TRUE[word][a],predictive(agent.counts(word,a))) for a in ACTIONS)/len(ACTIONS)
