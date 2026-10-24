"""Independent randomized algebraic review, fixed seed; no native/model execution."""
import copy, math, random
from v13.sleep_trace_decay import DAY,plan_trace_decay,apply_trace_decay
rng=random.Random(20261024)
for k in range(2000):
    p=rng.uniform(.05,1.0)
    t=rng.uniform(0,365)*DAY
    n=rng.randint(1,50)
    i={'priority':p,'created':0.,'last':None,'expires':366*DAY,'retired':None}
    j=copy.deepcopy(i)
    for a in range(1,n+1):
        apply_trace_decay(plan_trace_decay([i],t*a/n,.98,.05))
    apply_trace_decay(plan_trace_decay([j],t,.98,.05))
    if not math.isclose(i['priority'],j['priority'],rel_tol=2e-12,abs_tol=2e-12):
        raise AssertionError((k,p,t,n,i,j))
    previous=i['priority']
    apply_trace_decay(plan_trace_decay([i],i['trace_decay_at'],.98,.05))
    if i['priority']!=previous:raise AssertionError(('same time',k))
print('2000/2000 randomized elapsed-time equivalence and idempotence PASS; seed=20261024')
