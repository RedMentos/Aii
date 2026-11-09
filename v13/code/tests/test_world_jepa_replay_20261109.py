import numpy as np
import pytest
from v13.world_jepa_replay import replay_update


def rows(n=12, offset=0):
    x = np.arange(n * 2, dtype=float).reshape(n, 2) / 10 + offset
    a = np.tile([[1., 0.], [0., 1.]], (n + 1) // 2)[:n]
    return x, a, x + a


class MeasuredModel:
    def __init__(self):
        self.calls = []
        self.weight = 0.

    def prediction_loss(self, x, a, x2):
        return float(np.mean((x2 - x - a - self.weight) ** 2))

    def partial_fit(self, x, a, x2, *, steps, log_every):
        self.calls.append((x.copy(), a.copy(), x2.copy(), steps))
        self.weight = .1


def test_replay_update_measures_both_holdouts_and_bounded_rows():
    model = MeasuredModel()
    result = replay_update(model, rows(12, 0), rows(12, 100),
                           rows(8, 200), rows(8, 300),
                           steps=4, replay_fraction=.25, seed=3)
    assert result["new_train_rows"] == 12
    assert result["replay_train_rows"] == 6
    assert len(model.calls) == 1
    assert len(model.calls[0][0]) == 18
    assert result["old_holdout_delta"] > 0
    assert result["new_holdout_delta"] > 0
    assert result["active_model_promoted"] is False


def test_replay_update_is_deterministic():
    a, b = MeasuredModel(), MeasuredModel()
    args = (rows(40), rows(40, 100), rows(8, 200), rows(8, 300))
    replay_update(a, *args, seed=7, replay_fraction=.5)
    replay_update(b, *args, seed=7, replay_fraction=.5)
    for left, right in zip(a.calls[0][:3], b.calls[0][:3]):
        np.testing.assert_array_equal(left, right)


def test_invalid_inputs_cannot_train():
    model = MeasuredModel()
    args = (rows(), rows(), rows(), rows())
    with pytest.raises(ValueError):
        replay_update(model, *args, replay_fraction=float("nan"))
    with pytest.raises(ValueError):
        replay_update(model, rows(), rows(), rows(), rows(8, 2)[:2] + (np.zeros((8, 3)),))
    assert model.calls == []
