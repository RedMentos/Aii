"""Synthetic regression: T8 sibling actions must never cross the holdout boundary."""
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import numpy as np
from v13.online_world import OnlineWorld


def _row(i):
    event = i // 2
    return {
        'action_id': 'action-%04d' % i,
        'event_id': event,
        's': [0.1 + i * 0.001, 0., 0., 1.],
        'a': 'simple' if i % 2 == 0 else 'detail',
        'y': [0.2 + i * 0.0005, 1., 0.3],
    }


def test_group_split_and_pre_post_retention(tmp_path):
    rows = [_row(i) for i in range(120)]
    runtime = SimpleNamespace(home=tmp_path, store=object())
    with patch('v13.t8_learning_audit.world_model.transitions', return_value=rows):
        world = OnlineWorld(runtime)
        result = world.benchmark(limit=120)
    assert result['split'] == 'SHA256_EVENT_ID_MOD5'
    expected_holdout = sum(
        int.from_bytes(hashlib.sha256(str(event).encode()).digest()[:8], 'big') % 5 == 0
        for event in range(60)
    ) * 2
    assert result['holdout'] == expected_holdout
    assert result['train'] + result['holdout'] == 120
    for measurement in result['results'].values():
        assert np.isfinite(measurement['early_train_anchor_mse_before'])
        assert np.isfinite(measurement['early_train_anchor_mse_after'])
        assert np.isclose(
            measurement['early_train_anchor_mse_delta'],
            measurement['early_train_anchor_mse_after'] - measurement['early_train_anchor_mse_before'],
        )
        assert measurement['restart_exact']
    assert 'action_shift_control' in result['results']\n    assert np.isfinite(result['results']['replay_on']['action_specific_gain_vs_shift_control'])\n    shifted = result['results']['action_shift_control']\n    assert shifted['restart_exact']\n    assert shifted['updates'] == result['results']['replay_on']['updates']\n    assert result['production_unchanged']
    assert not world.model.path.exists()


def test_legacy_ungrouped_rows_are_explicitly_labeled(tmp_path):
    rows = [_row(i) for i in range(120)]
    for row in rows:
        del row['event_id']
    runtime = SimpleNamespace(home=tmp_path, store=object())
    with patch('v13.t8_learning_audit.world_model.transitions', return_value=rows):
        result = OnlineWorld(runtime).benchmark(limit=120)
    assert result['split'] == 'SHA256_ACTION_ID_MOD5_LEGACY_UNGROUPED'


def test_mixed_event_provenance_fails_closed_before_training(tmp_path):
    import pytest
    rows = [_row(i) for i in range(120)]
    del rows[0]['event_id']
    runtime = SimpleNamespace(home=tmp_path, store=object())
    with patch('v13.t8_learning_audit.world_model.transitions', return_value=rows):
        world = OnlineWorld(runtime)
        with pytest.raises(ValueError, match='Mixed event-bound'):
            world.benchmark(limit=120)
    assert not world.model.path.exists()
