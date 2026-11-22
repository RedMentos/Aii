"""Execute only in the #1663 hash-checked materialized integration copy."""
import time
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from v13 import inputs, online_world_policy, world_model
from v13.online_world import OnlineWorld
from v13.operator import Operator
from v13.runtime import Runtime


def turn(runtime):
    runtime.submit('Explain a synthetic integration test')
    deadline = time.monotonic() + 10
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(.005)
    assert runtime.idle() and runtime.last_answer()['status'] == 'FINAL'
    return runtime.last_answer()['event_id']


def synthetic_c3(runtime):
    runtime.sleep.cycle.set_policy('enabled', 'off')
    runtime._route = Mock(return_value=('simple', {'source': 'SYNTHETIC_TEST'}))
    runtime.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE', last_metrics={},
                        generate=lambda *a, **kw: iter(['synthetic response'])))
    runtime.learner.output_delta = Mock(return_value=None)


def test_real_operator_turn_update_restart_and_revocation(tmp_path):
    r = Runtime(tmp_path)
    try:
        synthetic_c3(r)
        eid = turn(r)
        assert r.cfg['learning_mode'] == 'RECORD_ONLY'
        assert not hasattr(r, '_online_world') and len(world_model.transitions(r.store)) == 1
        # A direct internal call cannot skip RECORD_ONLY with a permissive callback.
        direct = OnlineWorld(r)
        assert direct.update(should_continue=lambda: True)['status'] == 'SKIPPED_RECORD_ONLY'
        assert direct.model.seen == 0
        op = Operator(r)
        op.run(':learning shadow')
        assert direct.update()['status'] == 'SKIPPED_OFF'
        online_world_policy.set_enabled(r.store, True, online_world_policy.HUMAN)
        result = r.online_world_update(limit=64, authority=online_world_policy.HUMAN)
        assert result['learned'] == 1 and r._online_world.model.seen == 1
        assert np.any(r._online_world.model.U != 0)
        saved = r._online_world.model.W.copy()
        source = r.store.one('SELECT source_id FROM events WHERE id=?', (eid,))['source_id']
        r.close()
        r = Runtime(tmp_path)
        synthetic_c3(r)
        assert r.cfg['learning_mode'] == 'SHADOW_UPDATE'
        assert online_world_policy.enabled(r.store) is True
        result = r.online_world_update(limit=64, authority=online_world_policy.HUMAN)
        assert result['learned'] == 0 and r._online_world.model.seen == 1
        np.testing.assert_array_equal(r._online_world.model.W, saved)
        with r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (source,))
        with pytest.raises(ValueError, match='source'):
            r.online_world_update(limit=64, authority=online_world_policy.HUMAN)
        with pytest.raises(RuntimeError, match='review'):
            r._online_world.predict([0., 0., 0., 1.], 'simple')
    finally:
        r.close()


def test_direct_update_respects_mode_and_training_pause(tmp_path):
    r = Runtime(tmp_path)
    try:
        synthetic_c3(r)
        turn(r)
        direct = OnlineWorld(r)
        assert direct.update(authority=online_world_policy.HUMAN)['status'] == 'SKIPPED_RECORD_ONLY'
        r.cfg['learning_mode'] = 'SHADOW_UPDATE'
        inputs.set_pause(r.store, 'training', True)
        assert direct.update(authority=online_world_policy.HUMAN)['status'] == 'SKIPPED_PAUSED_TRAINING'
        assert direct.model.seen == 0 and not direct.model.path.exists()
    finally:
        r.close()


def test_worker_survives_learning_and_error_log_failures(tmp_path):
    r = Runtime(tmp_path)
    try:
        synthetic_c3(r)
        original_log = r.store.log
        def log(kind, *args, **kwargs):
            if kind == 'online_world_learning_error':
                raise OSError('synthetic log failure')
            return original_log(kind, *args, **kwargs)
        r.store.log = log
        r.online_world_update = Mock(side_effect=ValueError('synthetic learning failure'))
        turn(r)
        assert r.worker.is_alive()
        turn(r)
        assert r.worker.is_alive() and r.online_world_update.call_count == 2
    finally:
        r.close()
