"""Synthetic Android action receipts -> actual NumPy JEPA weight updates.

This is intentionally NOT evidence of real Android control, live perception,
pretrained B1/B2/C3 updates, or AGI. Simulation data is kept outside T8 Store.
"""
import json
import sqlite3

import numpy as np
import pytest

from v13.android_control import AndroidControlBroker
from v13.android_control_sim import SimulatedAndroidWorld, DEMO_PACKAGE
from v13.android_sim_jepa_probe import trial, replay_ablation, _groups


def _do(broker, world, cap, args):
    p = broker.propose(cap, args)
    broker.approve(p.action_id, confirmed_by_local_ui=True)
    return world.apply(broker.execute(p.action_id))


def _environment(tmp_path, n=18):
    broker = AndroidControlBroker(tmp_path / "broker.sqlite")
    broker.start()
    world = SimulatedAndroidWorld(tmp_path)
    _do(broker, world, "launch_app", {"package": DEMO_PACKAGE})
    for i in range(n):
        _do(broker, world, "tap", {"x": 200, "y": 150})
        _do(broker, world, "type_text", {"text": f"SYNTHETIC-NOTE-{i}"})
        _do(broker, world, "tap", {"x": 200, "y": 350})
        _do(broker, world, "observe_ui", {})
    return broker, world


def test_simulated_to_jepa_actual_numeric_weights_and_checkpoint(tmp_path):
    broker, world = _environment(tmp_path, n=18)
    try:
        assert len(world.transitions()) == 73
        result = trial(world, seed=9, steps=3, checkpoint=tmp_path / "synthetic-jepa.npz")
        assert result["kind"] == "SYNTHETIC_UI_JEPA_PROBE"
        assert result["scope"] == "SYNTHETIC_UI_ONLY_NO_T8_SOURCE"
        assert result["train_rows"] >= 8
        assert result["holdout_rows"] >= 4
        assert result["verified_input_disjointness"] is True
        assert result["encoder_weights_changed"] is True
        assert result["fit_steps"] == 6
        assert np.isfinite(result["heldout_loss_before"])
        assert np.isfinite(result["heldout_loss_after"])
        assert result["active_model_promoted"] is False
        assert result["native_android_executed"] is False
        assert result["b1_b2_c3_gguf_weights_modified"] is False
        assert result["registered_t8_training_corpus_modified"] is False
        assert result["readback"]["inference_reload_exact_loss"] is True
        assert result["readback"]["optimizer_trajectory_reproduced"] is False
        assert "SYNTHETIC-NOTE" not in json.dumps(result)
        # Actual checkpoint bytes may be loaded only under the exact pinned
        # synthetic receipt SHA and archive digest, never from the live Store.
        assert (tmp_path / "synthetic-jepa.npz").is_file()
    finally:
        world.close()
        broker.close()


def test_repeated_trials_are_deterministic_and_unseen_cohorts_disjoint(tmp_path):
    broker, world = _environment(tmp_path, n=15)
    try:
        records = world.transitions()
        train, test = _groups(records)
        train_keys = {key for key, _ in train}
        test_keys = {key for key, _ in test}
        assert train_keys.isdisjoint(test_keys)
        a = trial(world, seed=21, steps=4)
        b = trial(world, seed=21, steps=4)
        assert a["source_sha256"] == b["source_sha256"]
        assert a["heldout_loss_before"] == pytest.approx(b["heldout_loss_before"])
        assert a["heldout_loss_after"] == pytest.approx(b["heldout_loss_after"])
        assert a["fit_steps"] == b["fit_steps"] == 7
    finally:
        world.close()
        broker.close()


def test_synthetic_transition_export_never_contains_notes_text(tmp_path):
    broker, world = _environment(tmp_path, n=5)
    try:
        rows = world.transitions()
        assert len(rows) == 21
        assert all(row["scope"] == "SYNTHETIC_UI_ONLY" for row in rows)
        assert all(len(row["x"]) == len(row["x2"]) == 4 for row in rows)
        assert all(0 <= row["a"] < 6 for row in rows)
        assert "SYNTHETIC-NOTE" not in json.dumps(rows)
        # The export is numeric only. It must not echo even synthetic
        # user text back into general training/holdout metadata.
        assert all("SYNTHETIC-NOTE" not in str(v) for row in rows for v in row.values())
    finally:
        world.close()
        broker.close()


def test_corrupt_or_relabelled_synthetic_evidence_rejected(tmp_path):
    broker, world = _environment(tmp_path, n=14)
    try:
        with world.db:
            world.db.execute(
                "UPDATE sim_transitions SET scope='REAL_ANDROID' "
                "WHERE action_id=(SELECT action_id FROM sim_transitions LIMIT 1)"
            )
        with pytest.raises(ValueError, match="corrupt simulator transition"):
            world.transitions()
        with world.db:
            world.db.execute("UPDATE sim_transitions SET scope='SYNTHETIC_UI_ONLY'")
            world.db.execute(
                "UPDATE sim_transitions SET before_features=? "
                "WHERE action_id=(SELECT action_id FROM sim_transitions LIMIT 1)",
                ('[0.0,0.0,NaN,0.0]',)
            )
        with pytest.raises(ValueError, match="invalid numeric"):
            world.transitions()
    finally:
        world.close()
        broker.close()


def test_no_data_no_fit_no_checkpoint_and_budget_limits(tmp_path):
    world = SimulatedAndroidWorld(tmp_path)
    try:
        with pytest.raises(ValueError, match="at least 12"):
            trial(world, checkpoint=tmp_path / "no-fit.npz")
        assert not (tmp_path / "no-fit.npz").exists()
        for kwargs in ({"seed": -1}, {"seed": True}, {"steps": 0},
                       {"steps": 101}, {"limit": 2}, {"limit": 2049}):
            with pytest.raises(ValueError):
                trial(world, **kwargs)
    finally:
        world.close()


def test_duplicate_observation_action_pairs_cannot_fake_holdout(tmp_path):
    broker, world = _environment(tmp_path, n=1)
    try:
        for _ in range(24):
            _do(broker, world, "observe_ui", {})
        assert len(world.transitions()) >= 12
        with pytest.raises(ValueError, match="not enough disjoint"):
            trial(world, steps=2)
    finally:
        world.close()
        broker.close()



def test_replay_ablation_compares_actual_weight_updates_without_false_promotion(tmp_path):
    broker, world = _environment(tmp_path, n=20)
    try:
        metrics = replay_ablation(world, seed=5, steps=3)
        assert metrics["kind"] == "SYNTHETIC_UI_REPLAY_ABLATION"
        assert metrics["scope"] == "SYNTHETIC_UI_ONLY_NO_T8_SOURCE"
        assert metrics["initial_train_rows"] >= 8
        assert metrics["old_disjoint_holdout_rows"] >= 4
        assert metrics["new_train_rows"] >= 8
        assert metrics["source_ids_disjoint"] is True
        assert metrics["both_models_changed_numeric_weights"] is True
        assert metrics["guaranteed_replay_superiority"] is False
        assert metrics["native_android_executed"] is False
        assert metrics["active_model_promoted"] is False
        assert metrics["b1_b2_c3_gguf_weights_modified"] is False
        for name in ("old_holdout_loss_before", "without_replay_loss_after",
                     "with_replay_loss_after", "forgetting_delta_without_replay",
                     "forgetting_delta_with_replay"):
            assert np.isfinite(metrics[name])
        assert "SYNTHETIC-NOTE" not in json.dumps(metrics)
        # V13 real T8 corpus remains absent; the simulator writes its own
        # private database with only numeric synthetic observations.
        assert not (tmp_path / "data" / "db").exists()
        repeat = replay_ablation(world, seed=5, steps=3)
        assert metrics == repeat
    finally:
        world.close()
        broker.close()


@pytest.mark.parametrize("kwargs", [
    {"seed": -1}, {"seed": True}, {"steps": 0}, {"steps": 101},
    {"limit": 1}, {"limit": 2049},
])
def test_replay_ablation_rejects_invalid_step_and_source_budgets(tmp_path, kwargs):
    world = SimulatedAndroidWorld(tmp_path)
    try:
        with pytest.raises(ValueError):
            replay_ablation(world, **kwargs)
    finally:
        world.close()


def test_old_new_cohort_split_rejects_duplicate_fake_training_volume(tmp_path):
    broker, world = _environment(tmp_path, n=1)
    try:
        for _ in range(28):
            _do(broker, world, "observe_ui", {})
        with pytest.raises(ValueError, match="not enough disjoint"):
            replay_ablation(world, steps=2)
    finally:
        world.close()
        broker.close()



def test_numeric_target_edits_change_synthetic_dataset_pin(tmp_path):
    broker, world = _environment(tmp_path, n=18)
    try:
        original = trial(world, seed=6, steps=2)
        with world.db:
            world.db.execute(
                "UPDATE sim_transitions SET after_features='[0.0,0.0,0.5,0.0]' "
                "WHERE action_id=(SELECT action_id FROM sim_transitions ORDER BY rowid DESC LIMIT 1)"
            )
        changed = trial(world, seed=6, steps=2)
        assert changed["source_sha256"] != original["source_sha256"]
        first = replay_ablation(world, seed=6, steps=2)
        with world.db:
            world.db.execute(
                "UPDATE sim_transitions SET after_features='[0.0,0.0,0.75,0.0]' "
                "WHERE action_id=(SELECT action_id FROM sim_transitions ORDER BY rowid DESC LIMIT 1)"
            )
        second = replay_ablation(world, seed=6, steps=2)
        assert first["source_sha256"] != second["source_sha256"]
        assert not (tmp_path / "data" / "db").exists()
    finally:
        world.close()
        broker.close()


def test_nonhex_provenance_hash_rejected_before_training(tmp_path):
    broker, world = _environment(tmp_path, n=12)
    try:
        with world.db:
            world.db.execute(
                "UPDATE actions SET after_sha256=? WHERE action_id="
                "(SELECT action_id FROM actions LIMIT 1)",
                ("q" * 64,)
            )
        with pytest.raises(ValueError, match="corrupt simulator transition"):
            world.transitions()
        with pytest.raises(ValueError, match="corrupt simulator transition"):
            trial(world, seed=4, steps=2)
    finally:
        world.close()
        broker.close()
