import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from v13.world_jepa import WorldJEPA
from v13 import world_jepa_runtime_checkpoint as checkpoint
rng=np.random.default_rng(7)
x=rng.normal(size=(16,4));a=np.eye(2)[np.arange(16)%2];x2=x+.1
model=WorldJEPA(seed=7,ensemble=1).fit(x,a,x2,steps=1,log_every=1)
with TemporaryDirectory(prefix='v13-1661-checkpoint-audit-') as home:
    r=SimpleNamespace(home=home,_world_jepa_online=model,_world_jepa_source_sha='a'*64)
    checkpoint.save(r)
    model.enc['W1'][0,0]+=.01
    checkpoint.save(r)
    d=Path(home)/'world_jepa_online'
    before_active=json.loads((d/'active.json').read_text())
    before_previous=json.loads((d/'previous.json').read_text())
    original=checkpoint._write_manifest
    def fail_active(home,name,manifest):
        if name=='active.json':raise OSError('injected active publish failure')
        return original(home,name,manifest)
    with patch.object(checkpoint,'_write_manifest',side_effect=fail_active):
        try:checkpoint.save(r)
        except OSError:pass
        else:raise AssertionError('expected injected failure')
    after_active=json.loads((d/'active.json').read_text())
    after_previous=json.loads((d/'previous.json').read_text())
    print('active_unchanged',before_active==after_active,
          'previous_unchanged',before_previous==after_previous,
          'previous_now_equals_active',after_previous==after_active,
          'old_previous_file_exists',(d/before_previous['filename']).exists())
