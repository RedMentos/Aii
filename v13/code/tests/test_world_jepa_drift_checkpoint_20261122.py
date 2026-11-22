"""Regression: the optional STABLE-style drift controller survives JEPA resume.

This tests only the numeric WorldJEPA predictor/EMA checkpoint, not GGUF or
cross-organ receiver learning.
"""
import numpy as np

from v13 import world_jepa_drift as drift
from v13 import world_jepa_training_state as training_state
from v13.world_jepa import WorldJEPA
from v13.world_jepa_shadow_checkpoint import load, save


def batch(seed, n=48):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 4))
    actions = np.eye(2)[np.arange(n) % 2]
    y = x + np.column_stack((
        actions[:, 0] * 0.2,
        actions[:, 1] * 0.3,
        np.zeros(n),
        np.zeros(n),
    ))
    return x, actions, y


def controller():
    return {
        "enabled": True,
        "budget_sq": {
            "encoder": 0.05,
            "predictor": 0.05,
            "inverse": 0.05,
        },
    }


def test_drift_state_roundtrips_and_controls_resumed_numeric_update(tmp_path):
    model = WorldJEPA(seed=22, ensemble=2)
    model.fit(*batch(3), steps=3, log_every=1, drift_control=controller())
    before_state = model._training_state["drift"]
    assert all(item["task_count"] == 1 for item in before_state["groups"].values())
    assert all(item["budget_method"] == "EXPLICIT" for item in before_state["groups"].values())

    source_sha = "a" * 64
    checkpoint = tmp_path / "world-jepa.npz"
    receipt = save(model, checkpoint, source_sha)
    restored = load(checkpoint, source_sha, receipt["sha256"])
    assert restored._training_state["drift"] == before_state

    encoder_before = {key: value.copy() for key, value in restored.enc.items()}
    target_before = {key: value.copy() for key, value in restored.tgt.items()}
    restored.partial_fit(*batch(9), steps=2, log_every=1, drift_control=controller())

    assert any(not np.array_equal(encoder_before[k], restored.enc[k]) for k in encoder_before)
    assert any(not np.array_equal(target_before[k], restored.tgt[k]) for k in target_before)
    after = restored._training_state["drift"]
    assert all(item["task_count"] == 2 for item in after["groups"].values())
    assert all(item["controlled_steps"] == 2 for item in after["groups"].values())


def test_legacy_training_state_without_drift_defaults_safely():
    model = WorldJEPA(seed=23, ensemble=2)
    model.fit(*batch(4), steps=2, log_every=1)
    legacy = dict(model._training_state)
    legacy.pop("drift")
    restored = training_state.validate(
        legacy, len(model.mu), len(model._action_counts),
        model.seed, model.ensemble, model._fit_steps,
    )
    assert restored["drift"] == drift.default_state()


def test_malformed_persisted_drift_state_is_rejected():
    model = WorldJEPA(seed=24, ensemble=2)
    model.fit(*batch(5), steps=2, log_every=1)
    invalid = dict(model._training_state)
    invalid["drift"] = {"schema": drift.SCHEMA, "groups": {}}
    try:
        training_state.validate(
            invalid, len(model.mu), len(model._action_counts),
            model.seed, model.ensemble, model._fit_steps,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("malformed persisted drift state was accepted")
