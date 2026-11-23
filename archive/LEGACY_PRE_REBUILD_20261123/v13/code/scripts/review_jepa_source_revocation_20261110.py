import itertools,json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic,sleep
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import world_model,inputs
from v13.world_jepa_action_outcome_adapter import _partition
with TemporaryDirectory(prefix='v13-1661-jepa-audit-') as home:
    root=Path(home);r=Runtime(root)
    try:
        r.sleep.cycle.set_policy('enabled','off')
        routes=itertools.cycle(('simple','detail'))
        r._route=Mock(side_effect=lambda *a,**k:(next(routes),{'source':'TEST_ROUTE_SEAM'}))
        r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                       generate=lambda *args,**kwargs:iter(['synthetic answer'])))
        r.learner.output_delta=Mock(return_value=None)
        event_ids=[]
        for i in range(48):
            event_ids.append(r.submit('Synthetic sample '+str(i)+' x'*i))
            end=monotonic()+15
            while not r.idle() and monotonic()<end:sleep(.005)
            if not r.idle() or r.last_answer()['status']!='FINAL':raise RuntimeError('turn failed')
        rows=world_model.transitions(r.store,limit=128)
        print('real_turns',len(event_ids),'committed_rows',len(rows),'learning_mode',r.cfg['learning_mode'],flush=True)
        first=json.loads(Operator(r).run(':growth jepa 1 128'))
        w_before=r._world_jepa_online.enc['W1'].copy();fit_before=r._world_jepa_online._fit_steps
        inputs.set_pause(r.store,'training',True)
        second=json.loads(Operator(r).run(':growth jepa 1 128'))
        w_after=r._world_jepa_online.enc['W1'].copy()
        print('record_only_result',first['status'],'fit_steps_before_pause',fit_before,
              'training_paused',inputs.paused(r.store,'training'),
              'weights_changed_while_paused',bool(np.any(w_before!=w_after)),
              'fit_steps_after_pause',r._world_jepa_online._fit_steps,flush=True)
        saved=json.loads(Operator(r).run(':growth jepa save'))
        chosen=next((eid, row['id']) for eid in event_ids
                    if (row:=r.store.one('SELECT id FROM actions WHERE event_id=? AND outcome IS NOT NULL',(eid,)))
                    and _partition(row['id'])=='train')
        source=r.store.one('SELECT source_id FROM events WHERE id=?',(chosen[0],))['source_id']
        action=chosen[1]
        with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(source,))
        stale=any(x['action_id']==action for x in world_model.transitions(r.store,limit=128))
        before_revoked=r._world_jepa_online.enc['W1'].copy()
        revoked_result=json.loads(Operator(r).run(':growth jepa 1 128'))
        print('revoked_row_partition',_partition(action),'present_after_revoke',stale,
              'source_verified_claim',revoked_result['source_verified'],
              'weights_changed_after_revoke',bool(np.any(before_revoked!=r._world_jepa_online.enc['W1'])),flush=True)
        r.close();r=Runtime(root);r.sleep.cycle.set_policy('enabled','off')
        automatic=hasattr(r,'_world_jepa_online')
        restored=json.loads(Operator(r).run(':growth jepa restore'))
        print('revoked_source_still_in_feed',stale,'saved_private',saved['persisted'],
              'automatically_restored',automatic,'explicit_restore',restored['restored'],
              'mode_after_restart',r.cfg['learning_mode'],
              'pause_after_restart',inputs.paused(r.store,'training'),flush=True)
    finally:r.close()
