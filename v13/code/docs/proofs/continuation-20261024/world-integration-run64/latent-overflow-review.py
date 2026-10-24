import math
from tests.test_world_model_integration_run64 import Store
from v13 import world_model as W
s=Store()
for i in range(24):s.add(i,chars=20+i,duration=.1+i*.01,output=10+i,route=W.ACTIONS[i%4],latent=[1e308,1e308])
print('transitions=',len(W.transitions(s)))
try:
    out=W.fit(s,rng_seed=42)
    print('status=',out['status'])
    print('state_align=',out['metrics']['state_align'])
    assert out['metrics']['state_align']['status']!='MEASURED' or all(math.isfinite(x) for x in out['metrics']['state_align']['r2'].values()), 'RED: persisted nonfinite measured state-align' 
except Exception as exc:
    print('fit_exception=',type(exc).__name__,str(exc))
    raise
