"""End-to-end typed C5 shadow + simulated Android + durable JEPA weights."""
import pytest
from v13.android_c5_goal_replay import run_integrated_goal


def test_typed_shadow_goal_persists_replay_weights_and_never_executes_native(tmp_path):
    result = run_integrated_goal(tmp_path, first=0, count=18, seed=17, steps=5)
    assert result["c5_typed_status"] == "SHADOW"
    assert result["native_android_executed"] is False
    assert result["b1_b2_c3_weights_modified"] is False
    assert result["replay_weight_checkpoint_reloaded"] is True
    record = result["t8_redacted_action_outcome"]
    assert record["status"] == "SHADOW"
    assert "args" not in record
    assert "package" not in str(record)
    assert result["synthetic_goal"]["replay"]["readback"]["replay_trained_model_reloaded"]
    assert result["synthetic_goal"]["goal"]["tasks_completed_this_run"] == 18
    assert (tmp_path / "android_control_sim" / "android_replay_trained_shadow_jepa.npz").exists()


def test_invalid_budget_rejected_before_simulator(tmp_path):
    with pytest.raises(ValueError):
        run_integrated_goal(tmp_path, count=0)
