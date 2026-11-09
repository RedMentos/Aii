"""Reject structurally inconsistent persisted online predictor state.

These are software-only checkpoint corruption tests, not native model evidence.
"""
import numpy as np
import pytest

from v13.continuous_predictor import OnlinePredictor


def rewrite_checkpoint(path, **changes):
    with np.load(path, allow_pickle=False) as archive:
        payload = {key: archive[key].copy() for key in archive.files}
    payload.update(changes)
    np.savez_compressed(path, **payload)


@pytest.mark.parametrize("counters", [
    np.array([0.5, 2.0]),
    np.array([0, 1], dtype=np.int64),
    np.array([1, 0], dtype=np.int64),
])
def test_corrupted_counters_rejected_before_state_restore(tmp_path, counters):
    p = OnlinePredictor(7, 4, tmp_path)
    p.observe(np.ones(7) * 0.1, 1, np.ones(7) * 0.2)
    p.checkpoint(processed_ids=['action-1'])
    rewrite_checkpoint(p.path, counters=counters)
    with pytest.raises(ValueError, match="checkpoint"):
        OnlinePredictor(7, 4, tmp_path)


def test_cursor_cannot_contain_more_actions_than_learned(tmp_path):
    p = OnlinePredictor(7, 4, tmp_path)
    p.checkpoint(processed_ids=[])
    rewrite_checkpoint(p.path, processed_ids=np.array('["action-without-gradient"]'))
    with pytest.raises(ValueError, match="cursor"):
        OnlinePredictor(7, 4, tmp_path)


@pytest.mark.parametrize("key", ["W", "act"])
def test_wrong_numeric_array_types_rejected(tmp_path, key):
    p = OnlinePredictor(7, 4, tmp_path)
    p.checkpoint()
    with np.load(p.path, allow_pickle=False) as archive:
        bad = archive[key].astype(float if key == "act" else np.int64)
    rewrite_checkpoint(p.path, **{key: bad})
    with pytest.raises(ValueError, match="checkpoint"):
        OnlinePredictor(7, 4, tmp_path)


def test_valid_atomic_cursor_and_replay_resume(tmp_path):
    p = OnlinePredictor(7, 4, tmp_path)
    p.observe(np.ones(7) * 0.1, 1, np.ones(7) * 0.2)
    p.checkpoint(processed_ids=['action-1'])
    restored = OnlinePredictor(7, 4, tmp_path)
    assert restored.checkpoint_ids == ['action-1']
    assert restored.seen == 1
    assert restored.updates >= 1
    np.testing.assert_array_equal(restored.W, p.W)

def test_cursor_cannot_be_published_ahead_of_learned_weights(tmp_path):
    p = OnlinePredictor(7, 4, tmp_path)
    with pytest.raises(ValueError, match="cursor"):
        p.checkpoint(processed_ids=['unlearned-action'])
    assert not p.path.exists()
