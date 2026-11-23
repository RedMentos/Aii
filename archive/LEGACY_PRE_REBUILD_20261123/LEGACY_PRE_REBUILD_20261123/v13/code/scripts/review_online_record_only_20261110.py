from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13 import world_model
with TemporaryDirectory(prefix='v13-1661-audit-') as home:
    r=Runtime(Path(home))
    try:
        r.sleep.cycle.set_policy('enabled','off')
        r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                       generate=lambda *args,**kwargs:iter(['synthetic answer'])))
        r.learner.output_delta=Mock(return_value=None)
        eid=r.submit('Synthetic audit request')
        end=monotonic()+10
        while not r.idle() and monotonic()<end:sleep(.005)
        if not r.idle():raise RuntimeError('timeout')
        print('learning_mode',r.cfg['learning_mode'],'final',r.last_answer()['status'],
              'transitions',len(world_model.transitions(r.store)),
              'automatic_model',hasattr(r,'_online_world'),
              'seen',getattr(getattr(getattr(r,'_online_world',None),'model',None),'seen',None),
              'checkpoint_exists',(Path(home)/'online_world'/'online_predictor.npz').exists())
    finally:r.close()
