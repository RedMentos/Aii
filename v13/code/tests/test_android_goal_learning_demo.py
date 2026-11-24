"""Cross-organ executable synthetic goal → broker → world → JEPA contract.

This tests the real broker, persistent SQLite simulation, numeric JEPA weights
and checkpoint, rather than mocking all organs. Never a native Android proof.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_goal_learning_demo import _next_action, run_demo


def test_goal_to_persisted_outcome_to_actual_jepa_weights(tmp_path):
    result = run_demo(tmp_path, first=0, count=18, seed=9)
    assert result["status"] == "SOFTWARE_SYNTHETIC_ONLY"
    assert result["controller"].endswith("NOT_JEF")
    assert result["tasks_completed_this_run"] == 18
    assert result["total_persisted_notes"] == 18
    assert result["action_receipt_count"] == 73
    assert result["restart_state_digest_equal"] is True
    assert result["native_android_executed"] is False
    assert result["registered_t8_training_corpus_modified"] is False
    learn = result["learning"]
    assert learn["scope"] == "SYNTHETIC_UI_ONLY_NO_T8_SOURCE"
    assert learn["encoder_weights_changed"] is True
    assert learn["fit_steps"] == 6
    assert learn["train_rows"] >= 8 and learn["holdout_rows"] >= 4
    assert math.isfinite(learn["heldout_loss_before"])
    assert math.isfinite(learn["heldout_loss_after"])
    assert learn["readback"]["inference_reload_exact_loss"] is True
    assert (tmp_path / "android_control_sim" / "android_goal_shadow_jepa.npz").is_file()
    assert "SYNTHETIC-NOTE" not in json.dumps(result)


def test_restart_then_continue_task_and_learn(tmp_path):
    first = run_demo(tmp_path, first=0, count=7, learn=False)
    assert first["learning"]["status"] == "OFF"
    assert first["total_persisted_notes"] == 7
    second = run_demo(tmp_path, first=7, count=11, seed=12, learn=True)
    assert second["total_persisted_notes"] == 18
    assert second["tasks_completed_this_run"] == 11
    assert second["action_receipt_count"] == first["action_receipt_count"] + 44
    assert second["learning"]["encoder_weights_changed"]
    assert second["learning"]["active_model_promoted"] is False


def test_non_synthetic_input_and_native_dispatch_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="non-synthetic"):
        _next_action({"kind": "ANDROID_NATIVE_SCREEN"}, "x")
    with pytest.raises(ValueError, match="native Android"):
        _next_action({"kind": "SIMULATED_UI_ONLY", "native_android_control": True}, "x")
    broker = AndroidControlBroker(tmp_path / "broker.sqlite")
    try:
        broker.start()
        p = broker.propose("back", {})
        broker.approve(p.action_id, confirmed_by_local_ui=True)
        with pytest.raises(ControlDenied, match="Android companion not connected"):
            broker.execute(p.action_id, dry_run=False)
    finally:
        broker.close()


@pytest.mark.parametrize("first,count,seed,learn", [
    (-1, 1, 17, True), (0, 0, 17, True), (0, 49, 17, True),
    (63, 2, 17, True), (0, True, 17, True), (0, 1, -1, True),
    (0, 1, 17, "true")
])
def test_bounded_execution_arguments_reject_invalid_values(tmp_path, first, count, seed, learn):
    with pytest.raises(ValueError):
        run_demo(tmp_path, first=first, count=count, seed=seed, learn=learn)


def test_real_command_line_entrypoint_reports_no_native_permission(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "v13.android_goal_learning_demo", "--home", str(tmp_path),
         "--count", "3", "--no-learn", "--simulation-only"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
        capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    assert data["tasks_completed_this_run"] == 3
    assert data["learning"]["status"] == "OFF"
    assert data["native_android_executed"] is False
    denied = subprocess.run(
        [sys.executable, "-m", "v13.android_goal_learning_demo",
         "--home", str(tmp_path), "--count", "1"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
        capture_output=True, text=True, timeout=30)
    assert denied.returncode != 0
    assert "--simulation-only" in denied.stderr
