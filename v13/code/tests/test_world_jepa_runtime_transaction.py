"""Runtime JEPA update publication must survive failed post-training evaluation."""
import threading

import pytest

from v13.runtime import Runtime
from v13 import world_jepa_online_experiment


class Model:
    def __init__(self):
        self.weights = [1.0]


def _runtime():
    runtime = object.__new__(Runtime)
    runtime.lock = threading.RLock()
    runtime.store = object()
    runtime._world_jepa_online = Model()
    runtime._world_jepa_source_sha = "a" * 64
    return runtime


def test_failed_experimental_update_preserves_previous_model_and_source(monkeypatch):
    runtime = _runtime()
    original = runtime._world_jepa_online

    def broken(candidate, store, *, steps, limit):
        assert candidate is not original
        candidate.weights[0] = 999.0
        raise ValueError("holdout evaluation failed")

    monkeypatch.setattr(world_jepa_online_experiment, "update_from_store", broken)
    with pytest.raises(ValueError, match="holdout"):
        runtime.world_jepa_update(steps=2, limit=16)
    assert runtime._world_jepa_online is original
    assert original.weights == [1.0]
    assert runtime._world_jepa_source_sha == "a" * 64


def test_successful_experimental_update_publishes_new_copy(monkeypatch):
    runtime = _runtime()
    original = runtime._world_jepa_online

    def updated(candidate, store, *, steps, limit):
        candidate.weights[0] = 2.0
        return {"source_sha256": "b" * 64, "holdout_loss_after": 0.1}

    monkeypatch.setattr(world_jepa_online_experiment, "update_from_store", updated)
    receipt = runtime.world_jepa_update(steps=2, limit=16)
    assert runtime._world_jepa_online is not original
    assert original.weights == [1.0]
    assert runtime._world_jepa_online.weights == [2.0]
    assert runtime._world_jepa_source_sha == "b" * 64
    assert receipt["active_model_promoted"] is False
    assert receipt["persisted"] is False


def test_real_jepa_gradient_failure_does_not_publish_weights(monkeypatch):
    import numpy as np
    from v13.world_jepa import WorldJEPA

    rng = np.random.default_rng(7)
    x = rng.normal(size=(16, 4))
    a = np.eye(2)[np.arange(16) % 2]
    x2 = x + 0.2 * np.where(a[:, :1] == 1, 1, -1)
    fitted = WorldJEPA(seed=7, ensemble=1)
    fitted.fit(x, a, x2, steps=3, log_every=1)

    runtime = _runtime()
    runtime._world_jepa_online = fitted
    old_weights = {key: value.copy() for key, value in fitted.enc.items()}
    old_loss = fitted.prediction_loss(x, a, x2)

    def update_then_fail(candidate, store, *, steps, limit):
        candidate.partial_fit(x, a, x2, steps=3, log_every=1)
        assert candidate._fit_steps > fitted._fit_steps
        raise RuntimeError("post-gradient validation failed")

    monkeypatch.setattr(world_jepa_online_experiment, "update_from_store", update_then_fail)
    with pytest.raises(RuntimeError, match="post-gradient"):
        runtime.world_jepa_update(steps=3, limit=16)

    assert runtime._world_jepa_online is fitted
    assert all(np.array_equal(fitted.enc[k], v) for k, v in old_weights.items())
    assert fitted.prediction_loss(x, a, x2) == old_loss
    assert runtime._world_jepa_source_sha == "a" * 64
