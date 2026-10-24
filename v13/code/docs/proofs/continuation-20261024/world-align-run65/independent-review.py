"""Fixed-seed synthetic World-Model numerical review; no native models."""
import math, random
from tests.test_world_model_integration_run64 import Store
from v13 import world_model as W
rng=random.Random(20261024)
for trial in range(200):
    dim=rng.randint(1,12)
    scale=rng.choice([1e-4,1.,1e2,1e100,1e200,1e308])
    s=Store()
    for i in range(24):
        latent=[rng.uniform(-1,1)*scale for _ in range(dim)]
        s.add(i,chars=20+i,duration=.1+i*.01,output=10+i,route=W.ACTIONS[i%4],latent=latent)
    st=W.fit(s,rng_seed=trial)
    a=st['metrics']['state_align']
    if a['status']=='MEASURED':
        assert all(math.isfinite(v) for v in a['r2'].values()),(trial,a)
    else:assert a['status']=='UNAVAILABLE',(trial,a)
    s.db.close()
print('200/200 randomized latent magnitude/dimension fits: no nonfinite measured R2; seed=20261024')
