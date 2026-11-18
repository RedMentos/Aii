from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from v13.online_world import OnlineWorld


def row(i):
    return {'action_id': 'committed-t8-%04d' % i,
            's': [.1+i*.001, 0., 0., 1.],
            'a': 'simple' if i % 2 == 0 else 'detail',
            'y': [.2+i*.0005, 1., .3]}


def test_disjoint_benchmark_readonly_replay_and_restart(tmp_path):
    rows = [row(i) for i in range(100)]
    runtime = SimpleNamespace(home=tmp_path, store=object())
    with patch('v13.online_world.world_model.transitions', return_value=rows), \
         patch('v13.t8_learning_audit.world_model.transitions', return_value=rows):
        world = OnlineWorld(runtime)
        before = (world.model.W.copy(), world.model.U.copy(), world.model.seen)
        report = world.benchmark(limit=100)
        assert report['train'] + report['holdout'] == 100
        assert report['status'] == 'SYNTHETIC_OR_LOCAL_T8_AUDIT_NOT_ANDROID_PROOF'
        assert report['production_unchanged']
        for result in report['results'].values():
            assert np.isfinite(result['holdout_mse_before'])
            assert np.isfinite(result['holdout_mse_after'])
            assert result['restart_exact']
        assert report['results']['replay_on']['updates'] > report['results']['replay_off']['updates']
        np.testing.assert_array_equal(world.model.W, before[0])
        np.testing.assert_array_equal(world.model.U, before[1])
        assert world.model.seen == before[2]
        assert not world.model.path.exists()


def test_disjoint_benchmark_refuses_small_or_duplicate_feed(tmp_path):
    runtime = SimpleNamespace(home=tmp_path, store=object())
    with patch('v13.t8_learning_audit.world_model.transitions', return_value=[row(i) for i in range(8)]):
        assert OnlineWorld(runtime).benchmark(limit=8)['status'] == 'INSUFFICIENT_DISJOINT_T8'
    with patch('v13.t8_learning_audit.world_model.transitions', return_value=[row(1)]*20):
        import pytest
        with pytest.raises(ValueError, match='Duplicate'):
            OnlineWorld(runtime).benchmark(limit=20)
