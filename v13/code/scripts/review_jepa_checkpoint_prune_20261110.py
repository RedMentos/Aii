from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import numpy as np
from v13.world_jepa import WorldJEPA
from v13 import world_jepa_runtime_checkpoint as checkpoint
rng=np.random.default_rng(7)
x=rng.normal(size=(16,4));a=np.eye(2)[np.arange(16)%2]
model=WorldJEPA(seed=7,ensemble=1).fit(x,a,x+.1,steps=1,log_every=1)
with TemporaryDirectory(prefix='v13-1661-prune-audit-') as home:
    r=SimpleNamespace(home=home,_world_jepa_online=model,_world_jepa_source_sha='a'*64)
    checkpoint.save(r)
    unowned=Path(home)/'world_jepa_online'/('jepa-'+'f'*32+'.npz')
    unowned.write_bytes(b'synthetic unrelated private file')
    checkpoint.save(r)
    print('untracked_matching_file_preserved',unowned.exists())
