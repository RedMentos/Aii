"""Runtime integration of the existing Store-grounded JEPA learner."""
from threading import RLock
from unittest.mock import patch

import pytest
from v13.runtime import Runtime


def _runtime():
    runtime=object.__new__(Runtime)
    runtime.lock=RLock()
    runtime.store=object()
    return runtime


def test_world_jepa_runtime_reuses_model_and_never_promotes():
    runtime=_runtime()
    with patch('v13.world_jepa_online_experiment.update_from_store') as update:
        update.return_value={'mode':'INITIAL_WEIGHTS','source_verified':True,'source_sha256':'a'*64}
        first=runtime.world_jepa_update(steps=2,limit=128)
        second=runtime.world_jepa_update(steps=3,limit=256)
    assert first['active_model_promoted'] is False
    assert second['persisted'] is False
    assert second['status']=='EXPERIMENTAL_JEPA_NO_RUNTIME_AUTHORITY'
    assert update.call_count==2
    assert update.call_args_list[0].args[0] is not update.call_args_list[1].args[0]
    assert runtime._world_jepa_online is update.call_args_list[1].args[0]
    assert update.call_args_list[0].kwargs=={'steps':2,'limit':128}
    assert update.call_args_list[1].kwargs=={'steps':3,'limit':256}


def test_failed_initial_update_does_not_register_model():
    runtime=_runtime()
    with patch('v13.world_jepa_online_experiment.update_from_store',side_effect=ValueError('not enough data')):
        with pytest.raises(ValueError,match='not enough data'):
            runtime.world_jepa_update()
    assert not hasattr(runtime,'_world_jepa_online')


def test_runtime_jepa_real_weights_update_from_committed_feed():
    import numpy as np
    from v13.world_jepa_online_experiment import update_from_store
    rows=[{'action_id':f'grounded-{i:03d}',
           's':[i/90.,(i%7)/7.,float(np.sin(i/11.)),float(np.cos(i/11.))],
           'a':('simple','detail','gist','both')[i%4],
           'y':[i/180.,float(i%3==0),i/200.]} for i in range(96)]
    runtime=_runtime()
    with patch('v13.world_model.transitions',return_value=rows) as feed:
        first=runtime.world_jepa_update(steps=2,limit=128)
        model=runtime._world_jepa_online
        previous=model.enc['W1'].copy()
        second=runtime.world_jepa_update(steps=3,limit=128)
    assert feed.call_count==2
    assert first['source_verified'] is True
    assert second['mode']=='CONTINUED_WEIGHTS'
    assert second['holdout_loss_after']>=0
    assert np.array_equal(previous,model.enc['W1'])  # prior published snapshot stays intact
    assert runtime._world_jepa_online is not model
    assert not np.array_equal(previous,runtime._world_jepa_online.enc['W1'])
    assert runtime._world_jepa_online._fit_steps==5
    assert second['active_model_promoted'] is False


def test_growth_jepa_operator_is_explicit_and_bounded():
    import json
    from v13.agi import operator_command
    runtime=_runtime()
    with patch.object(runtime,'world_jepa_update',return_value={'mode':'CONTINUED_WEIGHTS'}) as update:
        assert json.loads(operator_command(runtime,['jepa','2','128']))['mode']=='CONTINUED_WEIGHTS'
        update.assert_called_once_with(steps=2,limit=128)
        for args in (['jepa','51'],['jepa','2','15'],['jepa','2','4096'],['jepa','1','256','extra']):
            with pytest.raises(ValueError):
                operator_command(runtime,args)
        assert update.call_count==1


def test_jepa_private_checkpoint_survives_restart_and_continues(tmp_path):
    import numpy as np
    rows=[{'action_id':f'checkpoint-{i:03d}',
           's':[i/90.,(i%7)/7.,float(np.sin(i/11.)),float(np.cos(i/11.))],
           'a':('simple','detail','gist','both')[i%4],
           'y':[i/180.,float(i%3==0),i/200.]} for i in range(96)]
    first=_runtime();first.home=str(tmp_path)
    with patch('v13.world_model.transitions',return_value=rows):
        first.world_jepa_update(steps=2,limit=128)
        receipt=first.world_jepa_save()
        assert receipt['persisted'] is True
        before=first._world_jepa_online.enc['W1'].copy()
        second=_runtime();second.home=str(tmp_path)
        restored=second.world_jepa_restore()
        assert restored['restored'] is True
        assert np.array_equal(before,second._world_jepa_online.enc['W1'])
        result=second.world_jepa_update(steps=2,limit=128)
    assert result['mode']=='CONTINUED_WEIGHTS'
    assert not np.array_equal(before,second._world_jepa_online.enc['W1'])
    assert result['active_model_promoted'] is False


def test_jepa_checkpoint_tamper_fails_closed(tmp_path):
    import numpy as np
    rows=[{'action_id':f'tamper-{i:03d}',
           's':[i/90.,(i%7)/7.,float(np.sin(i/11.)),float(np.cos(i/11.))],
           'a':('simple','detail','gist','both')[i%4],
           'y':[i/180.,float(i%3==0),i/200.]} for i in range(96)]
    first=_runtime();first.home=str(tmp_path)
    with patch('v13.world_model.transitions',return_value=rows):
        first.world_jepa_update(steps=2,limit=128)
    first.world_jepa_save()
    import json
    meta=json.loads((tmp_path/'world_jepa_online'/'active.json').read_text())
    target=tmp_path/'world_jepa_online'/meta['filename']
    target.write_bytes(target.read_bytes()+b'tamper')
    second=_runtime();second.home=str(tmp_path)
    with pytest.raises(ValueError):
        second.world_jepa_restore()
    assert not hasattr(second,'_world_jepa_online')
