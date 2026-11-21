"""Selective WorldJEPA plasticity and checkpoint-resume regression.

The predictor-only phase is a temporary adaptation mode, not a permanent
frozen-teacher architecture: an earlier full update trains the encoder/EMA,
a later dynamics update changes only the predictor, and a subsequent full
update can resume encoder/inverse plasticity with correct per-parameter Adam
bias-correction clocks.
"""
import numpy as np
import pytest

from v13 import world_jepa, world_jepa_shadow_checkpoint, world_jepa_training_state


def _cohort(seed, offset=0.0):
    rng = np.random.default_rng(seed)
    n, d, actions = 64, 7, 3
    x = rng.normal(size=(n, d)) + offset
    a = np.eye(actions, dtype=np.float64)[np.arange(n) % actions]
    transition = np.zeros((actions, d), dtype=np.float64)
    transition[0, :3] = (0.3, -0.2, 0.1)
    transition[1, 3:5] = (-0.4, 0.2)
    transition[2, 5:] = (0.15, -0.25)
    x2 = x + a @ transition + rng.normal(scale=0.03, size=(n, d))
    return x, a, x2


def test_prediction_loss_uses_fixed_preupdate_ema_target_snapshot():
    x, actions, x2 = _cohort(61)
    model = world_jepa.WorldJEPA(seed=61, ensemble=1)
    model.fit(x, actions, x2, steps=16, log_every=4)
    anchor = {key: value.copy() for key, value in model.tgt.items()}
    baseline = model.prediction_loss(x, actions, x2, target_snapshot=anchor)

    for value in model.tgt.values():
        value[...] += 0.1

    anchored = model.prediction_loss(x, actions, x2, target_snapshot=anchor)
    moving = model.prediction_loss(x, actions, x2)
    assert anchored == baseline
    assert not np.isclose(moving, baseline, rtol=1e-9, atol=1e-12)
    with pytest.raises(ValueError, match="target snapshot"):
        model.prediction_loss(x, actions, x2, target_snapshot={})


def _group_steps(state, prefix):
    return {key: value for key, value in state["main"]["steps"].items()
            if key.startswith(prefix)}


def test_predictor_only_adaptation_preserves_encoder_ema_and_resumes_clocks(tmp_path):
    x, actions, x2 = _cohort(41)
    shifted = _cohort(42, offset=0.25)
    model = world_jepa.WorldJEPA(seed=41, ensemble=2)
    model.fit(x, actions, x2, steps=32, log_every=8)

    before_enc = {key: value.copy() for key, value in model.enc.items()}
    before_tgt = {key: value.copy() for key, value in model.tgt.items()}
    before_pred = [{key: value.copy() for key, value in part.items()}
                   for part in model.preds]
    before_training = world_jepa_training_state.from_model(model)
    assert set(_group_steps(before_training, "e").values()) == {32}
    assert set(_group_steps(before_training, "p").values()) == {32}
    assert set(_group_steps(before_training, "i").values()) == {32}

    model.partial_fit(*shifted, steps=16, log_every=4, train_encoder=False)

    assert all(np.array_equal(before_enc[key], model.enc[key]) for key in before_enc)
    assert all(np.array_equal(before_tgt[key], model.tgt[key]) for key in before_tgt)
    assert any(not np.array_equal(before_pred[0][key], model.preds[0][key])
               for key in before_pred[0])
    assert any(not np.array_equal(before_pred[1][key], model.preds[1][key])
               for key in before_pred[1])

    after_training = world_jepa_training_state.from_model(model)
    before_steps = before_training["main"]["steps"]
    after_steps = after_training["main"]["steps"]
    assert all(after_steps[key] == before_steps[key] for key in before_steps if key.startswith("e"))
    assert all(after_steps[key] == before_steps[key] for key in before_steps if key.startswith("i"))
    assert all(after_steps[key] == before_steps[key] + 16
               for key in before_steps if key.startswith("p"))
    assert after_training["main"]["t"] == before_training["main"]["t"] + 16
    assert all(np.array_equal(before_training["inverse"][key], after_training["inverse"][key])
               for key in before_training["inverse"])

    checkpoint = tmp_path / "predictor-only-jepa.npz"
    source_sha = "a" * 64
    saved = world_jepa_shadow_checkpoint.save(model, checkpoint, source_sha)
    restored = world_jepa_shadow_checkpoint.load(
        checkpoint, source_sha, saved["sha256"]
    )
    restored_training = world_jepa_training_state.from_model(restored)
    assert restored_training["main"]["steps"] == after_training["main"]["steps"]
    assert restored_training["main"]["t"] == after_training["main"]["t"]
    assert all(np.array_equal(restored.enc[key], model.enc[key]) for key in model.enc)
    assert all(np.array_equal(restored.tgt[key], model.tgt[key]) for key in model.tgt)

    # Re-open encoder/inverse plasticity. Their Adam clocks must resume from
    # their own prior update counts, not the predictor's later global clock.
    restored.partial_fit(*shifted, steps=8, log_every=4, train_encoder=True)
    resumed_training = world_jepa_training_state.from_model(restored)
    resumed_steps = resumed_training["main"]["steps"]
    assert all(resumed_steps[key] == after_steps[key] + 8
               for key in after_steps if key.startswith(("e", "i", "p")))
    assert resumed_training["main"]["t"] == after_training["main"]["t"] + 8
    assert any(not np.array_equal(restored.tgt[key], before_tgt[key])
               for key in before_tgt)


def test_predictor_only_requires_an_existing_encoder_checkpoint():
    x, actions, x2 = _cohort(9)
    model = world_jepa.WorldJEPA(seed=9, ensemble=1)
    with pytest.raises(ValueError, match="requires an existing encoder"):
        model.fit(x, actions, x2, steps=4, train_encoder=False)
    with pytest.raises(ValueError, match="Invalid WorldJEPA fit configuration"):
        model.fit(x, actions, x2, steps=4, train_encoder=1)

    
def test_optimizer_update_scale_damps_real_weight_delta_without_changing_step_count():
    x, actions, x2 = _cohort(51)
    full = world_jepa.WorldJEPA(seed=51, ensemble=1)
    damped = world_jepa.WorldJEPA(seed=51, ensemble=1)
    full.fit(x, actions, x2, steps=0, log_every=1)
    damped.fit(x, actions, x2, steps=0, log_every=1)

    full_before = full.preds[0]["P1"].copy()
    damped_before = damped.preds[0]["P1"].copy()
    assert np.array_equal(full_before, damped_before)

    full.partial_fit(x, actions, x2, steps=1, log_every=1, update_scale=1.0)
    damped.partial_fit(x, actions, x2, steps=1, log_every=1, update_scale=0.25)
    full_delta = full.preds[0]["P1"] - full_before
    damped_delta = damped.preds[0]["P1"] - damped_before

    assert np.linalg.norm(full_delta) > 0.0
    assert np.allclose(damped_delta, full_delta * 0.25, rtol=1e-9, atol=1e-12)
    assert full._fit_steps == damped._fit_steps == 1
    assert full._training_state["main"]["t"] == damped._training_state["main"]["t"] == 1

    with pytest.raises(ValueError, match="update scale"):
        damped.partial_fit(x, actions, x2, steps=1, log_every=1, update_scale=0.0)
