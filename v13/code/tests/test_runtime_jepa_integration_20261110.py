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
        update.return_value={'mode':'INITIAL_WEIGHTS','source_verified':True}
        first=runtime.world_jepa_update(steps=2,limit=128)
        second=runtime.world_jepa_update(steps=3,limit=256)
    assert first['active_model_promoted'] is False
    assert second['persisted'] is False
    assert second['status']=='EXPERIMENTAL_JEPA_NO_RUNTIME_AUTHORITY'
    assert update.call_count==2
    assert update.call_args_list[0].args[0] is update.call_args_list[1].args[0]
    assert update.call_args_list[0].kwargs=={'steps':2,'limit':128}
    assert update.call_args_list[1].kwargs=={'steps':3,'limit':256}


def test_failed_initial_update_does_not_register_model():
    runtime=_runtime()
    with patch('v13.world_jepa_online_experiment.update_from_store',side_effect=ValueError('not enough data')):
        with pytest.raises(ValueError,match='not enough data'):
            runtime.world_jepa_update()
    assert not hasattr(runtime,'_world_jepa_online')
