"""WP-DS2 compositional word/action grounding lab; NOT a V13 runtime or STEP8 component.

The environment alone knows hidden object/support outcome tables. The learner
sees (object word, relation word, support word, action, sampled outcome), never
the hidden probabilities. Entire object-support phrases are held out at train.
"""
import hashlib
import math
import random

REVISION='ds2-composition-lab-v1'
OBJECTS=('glas','kiste','apfel','stein')
SUPPORTS=('stein','kiste','glas')
RELATION='auf'
ACTIONS=('push','touch','lift')
OUTCOMES=('MOVED','BLOCKED','SOUND')
K=len(OUTCOMES)
ALPHA0=.5
WEIGHT_OBJECT=.55
WEIGHT_SUPPORT=.45
HOLDOUT=(('glas','stein'),('kiste','glas'),('apfel','kiste'))
PAIRS=tuple((obj,sup) for obj in OBJECTS for sup in SUPPORTS)
TRAIN_PAIRS=tuple(pair for pair in PAIRS if pair not in HOLDOUT)

# Environment-only generative factors. No learner method reads either table.
TRUE_OBJECT={
    'glas':{'push':(.20,.10,.70),'touch':(.05,.05,.90),'lift':(.55,.10,.35)},
    'kiste':{'push':(.80,.15,.05),'touch':(.10,.25,.65),'lift':(.70,.20,.10)},
    'apfel':{'push':(.70,.20,.10),'touch':(.15,.15,.70),'lift':(.80,.15,.05)},
    'stein':{'push':(.05,.90,.05),'touch':(.10,.65,.25),'lift':(.10,.85,.05)},
}
TRUE_SUPPORT={
    'stein':{'push':(.05,.90,.05),'touch':(.10,.70,.20),'lift':(.15,.80,.05)},
    'kiste':{'push':(.85,.10,.05),'touch':(.10,.30,.60),'lift':(.75,.15,.10)},
    'glas':{'push':(.15,.10,.75),'touch':(.05,.05,.90),'lift':(.40,.15,.45)},
}


def true_dist(obj,support,action):
    """Only the lab environment/heldout evaluator may call this oracle."""
    if (obj,support) not in PAIRS or action not in ACTIONS:
        raise ValueError('unknown object/support/action')
    p=TRUE_OBJECT[obj][action];q=TRUE_SUPPORT[support][action]
    return [WEIGHT_OBJECT*x+WEIGHT_SUPPORT*y for x,y in zip(p,q)]


def predictive(counts):
    total=sum(counts)
    return [x/total for x in counts]


def kl(true,pred):
    return sum(x*math.log(x/y) for x,y in zip(true,pred) if x>0)


class DirichletModels:
    """Three model views over the same observed action outcomes, no truth oracle."""

    def __init__(self):
        self.pair_counts={}
        self.object_counts={}
        self.support_counts={}

    @staticmethod
    def _counts(table,key):
        return table.setdefault(key,[ALPHA0]*K)

    def observe(self,pair,action,outcome_index):
        if pair not in PAIRS or action not in ACTIONS or type(outcome_index) is not int or not 0<=outcome_index<K:
            raise ValueError('invalid compositional observation')
        obj,support=pair
        for table,key in ((self.pair_counts,(pair,action)),
                          (self.object_counts,(obj,action)),
                          (self.support_counts,(support,action))):
            self._counts(table,key)[outcome_index]+=1

    def predict(self,policy,pair,action):
        if pair not in PAIRS or action not in ACTIONS:
            raise ValueError('unknown compositional query')
        obj,support=pair
        if policy=='pair':
            return predictive(self._counts(self.pair_counts,(pair,action)))
        if policy=='object':
            return predictive(self._counts(self.object_counts,(obj,action)))
        if policy=='factor':
            p=predictive(self._counts(self.object_counts,(obj,action)))
            q=predictive(self._counts(self.support_counts,(support,action)))
            return [WEIGHT_OBJECT*x+WEIGHT_SUPPORT*y for x,y in zip(p,q)]
        raise ValueError('pair|object|factor')


def run(seed,steps=600):
    """Paired seeded interaction stream, training phrases only; heldout scored offline."""
    if type(seed) is not int or type(steps) is not int or steps<1:
        raise ValueError('seed/steps')
    rng=random.Random(seed)
    model=DirichletModels()
    training_pairs={}
    stream=hashlib.sha256()
    for step in range(steps):
        pair=TRAIN_PAIRS[step%len(TRAIN_PAIRS)]
        action=ACTIONS[(step//len(TRAIN_PAIRS))%len(ACTIONS)]
        outcome=rng.choices(range(K),weights=true_dist(*pair,action))[0]
        model.observe(pair,action,outcome)
        label='|'.join(pair)
        training_pairs[label]=training_pairs.get(label,0)+1
        stream.update(f'{pair[0]}|{RELATION}|{pair[1]}|{action}|{outcome}\n'.encode())

    def average_kl(pairs,policy):
        values=[kl(true_dist(*pair,action),model.predict(policy,pair,action))
                for pair in pairs for action in ACTIONS]
        return round(sum(values)/len(values),6)

    policies=('pair','object','factor')
    return {
        'revision':REVISION,'seed':seed,'steps':steps,
        'training_pairs':training_pairs,
        'covered_words':{
            'objects':sorted({pair[0] for pair in TRAIN_PAIRS}),
            'supports':sorted({pair[1] for pair in TRAIN_PAIRS})},
        'stream_sha256':stream.hexdigest(),
        'heldout_kl':{policy:average_kl(HOLDOUT,policy) for policy in policies},
        'train_kl':{policy:average_kl(TRAIN_PAIRS,policy) for policy in policies},
    }
