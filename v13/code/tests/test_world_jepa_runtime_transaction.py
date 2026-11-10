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
