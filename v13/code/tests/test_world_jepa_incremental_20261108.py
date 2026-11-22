import numpy as np
import pytest
from v13.world_jepa import WorldJEPA


def batch(seed=3,n=40):
    rng=np.random.default_rng(seed)
    x=rng.normal(size=(n,4))
    a=np.eye(2)[np.arange(n)%2]
    y=x+np.column_stack((a[:,0]*.2,a[:,1]*.3,np.zeros(n),np.zeros(n)))
    return x,a,y


def test_partial_fit_reuses_and_updates_existing_encoder_and_ema():
    m=WorldJEPA(seed=2,ensemble=2)
    x,a,y=batch()
    m.fit(x,a,y,steps=2,log_every=1)
    old=m.enc['W1'].copy();old_target=m.tgt['W1'].copy();old_ensemble=m.preds[1]['P1'].copy()
    m.partial_fit(*batch(4),steps=3,log_every=1)
    assert not np.array_equal(old,m.enc['W1'])
    assert not np.array_equal(old_target,m.tgt['W1'])
    assert not np.array_equal(old_ensemble,m.preds[1]['P1'])
    assert m._fit_steps==5
    assert np.isfinite(m.predict(x[:2],a[:2])[0]).all()


def test_partial_fit_requires_existing_compatible_model():
    m=WorldJEPA(seed=2,ensemble=2)
    with pytest.raises(ValueError):m.partial_fit(*batch(),steps=1)
    m.fit(*batch(),steps=1)
    with pytest.raises(ValueError):m.partial_fit(batch()[0][:,:3],batch()[1],batch()[2][:,:3],steps=1)


def test_zero_step_partial_fit_preserves_existing_weight_values():
    m=WorldJEPA(seed=1,ensemble=2)
    x,a,y=batch()
    m.fit(x,a,y,steps=1)
    old=m.enc['W1'].copy()
    m.partial_fit(x,a,y,steps=0)
    np.testing.assert_array_equal(m.enc['W1'],old)


def test_prediction_loss_can_measure_retention_without_training():
    m=WorldJEPA(seed=4,ensemble=2)
    x,a,y=batch()
    m.fit(x,a,y,steps=2)
    before=m.prediction_loss(x,a,y)
    m.partial_fit(*batch(9),steps=2)
    after=m.prediction_loss(x,a,y)
    assert np.isfinite(before) and np.isfinite(after)
    assert before>=0 and after>=0
    with pytest.raises(ValueError):m.prediction_loss(x,a,np.full_like(y,np.nan))


def test_pinned_jepa_checkpoint_can_resume_real_weight_learning(tmp_path):
    from v13.world_jepa_shadow_checkpoint import save,load
    m=WorldJEPA(seed=3,ensemble=2)
    x,a,y=batch()
    m.fit(x,a,y,steps=2)
    source_sha='a'*64
    path=tmp_path/'jepa.npz'
    saved=save(m,path,source_sha)
    resumed=load(path,source_sha,saved['sha256'])
    before=resumed.enc['W1'].copy()
    ensemble_before=resumed.preds[1]['P1'].copy()
    resumed.partial_fit(*batch(10),steps=2)
    assert not np.array_equal(before,resumed.enc['W1'])
    assert resumed._fit_steps==4
    assert not np.array_equal(ensemble_before,resumed.preds[1]['P1'])


# The STABLE-style drift controller is part of resumable JEPA state, not
# ephemeral per-process telemetry.
def _drift_controller():
    return {
        "enabled": True,
        "budget_sq": {"encoder": 0.05, "predictor": 0.05, "inverse": 0.05},
    }


def test_drift_state_roundtrips_and_controls_resumed_numeric_update(tmp_path):
    from v13 import world_jepa_drift as drift
    from v13.world_jepa_shadow_checkpoint import save, load

    m = WorldJEPA(seed=22, ensemble=2)
    m.fit(*batch(3), steps=3, log_every=1, drift_control=_drift_controller())
    before_state = m._training_state["drift"]
    assert all(item["task_count"] == 1 for item in before_state["groups"].values())
    assert all(item["budget_method"] == "EXPLICIT" for item in before_state["groups"].values())

    source_sha = "a" * 64
    path = tmp_path / "world-jepa.npz"
    receipt = save(m, path, source_sha)
    restored = load(path, source_sha, receipt["sha256"])
    assert restored._training_state["drift"] == before_state

    encoder_before = {key: value.copy() for key, value in restored.enc.items()}
    target_before = {key: value.copy() for key, value in restored.tgt.items()}
    restored.partial_fit(*batch(9), steps=2, log_every=1, drift_control=_drift_controller())
    assert any(not np.array_equal(encoder_before[k], restored.enc[k]) for k in encoder_before)
    assert any(not np.array_equal(target_before[k], restored.tgt[k]) for k in target_before)
    after = restored._training_state["drift"]
    assert all(item["task_count"] == 2 for item in after["groups"].values())
    assert all(item["controlled_steps"] == 2 for item in after["groups"].values())


def test_legacy_training_state_without_drift_defaults_safely():
    from v13 import world_jepa_drift as drift
    from v13 import world_jepa_training_state as training_state

    m = WorldJEPA(seed=23, ensemble=2)
    m.fit(*batch(4), steps=2, log_every=1)
    legacy = dict(m._training_state)
    legacy.pop("drift")
    restored = training_state.validate(
        legacy, len(m.mu), len(m._action_counts), m.seed, m.ensemble, m._fit_steps,
    )
    assert restored["drift"] == drift.default_state()


def test_malformed_persisted_drift_state_is_rejected():
    from v13 import world_jepa_drift as drift
    from v13 import world_jepa_training_state as training_state

    m = WorldJEPA(seed=24, ensemble=2)
    m.fit(*batch(5), steps=2, log_every=1)
    invalid = dict(m._training_state)
    invalid["drift"] = {"schema": drift.SCHEMA, "groups": {}}
    with pytest.raises(ValueError):
        training_state.validate(
            invalid, len(m.mu), len(m._action_counts), m.seed, m.ensemble, m._fit_steps,
        )
