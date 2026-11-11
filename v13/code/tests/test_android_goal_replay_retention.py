"""Integration: committed simulator action outcomes -> replay/no-replay JEPA."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from v13.android_goal_replay_retention import run_goal_replay
from v13.android_control_sim import SimulatedAndroidWorld


def test_goal_then_restart_then_disjoint_replay_ablation(tmp_path):
    result = run_goal_replay(tmp_path, count=18, seed=9, steps=3)
    assert result["status"] == "SHADOW_SYNTHETIC_REPLAY_ONLY"
    assert result["goal"]["tasks_completed_this_run"] == 18
    assert result["goal"]["learning"]["status"] == "OFF"
    assert result["goal"]["restart_state_digest_equal"]
    assert result["replay"]["source_ids_disjoint"]
    assert result["replay"]["both_models_changed_numeric_weights"]
    assert result["replay"]["old_disjoint_holdout_rows"] >= 4
    assert result["replay"]["replayed_prior_rows"] >= 4
    assert all(math.isfinite(result["replay"][key]) for key in (
        "old_holdout_loss_before", "without_replay_loss_after",
        "with_replay_loss_after", "forgetting_delta_without_replay",
        "forgetting_delta_with_replay"))
    assert result["native_android_executed"] is False
    assert result["registered_t8_training_corpus_modified"] is False
    assert result["body_weights_modified"] is False
    assert "SYNTHETIC-NOTE" not in json.dumps(result)
    world = SimulatedAndroidWorld(tmp_path)
    try:
        assert world.receipt_count() == result["goal"]["action_receipt_count"]
    finally:
        world.close()


def test_repeat_from_same_persisted_receipts_has_identical_ablation(tmp_path):
    run_goal_replay(tmp_path, count=18, seed=21, steps=2)
    # No new actions; the measured ablation uses exactly the persisted corpus.
    from v13.android_sim_jepa_probe import replay_ablation
    world = SimulatedAndroidWorld(tmp_path)
    try:
        a = replay_ablation(world, seed=21, steps=2)
        b = replay_ablation(world, seed=21, steps=2)
        assert a["source_sha256"] == b["source_sha256"]
        assert a["with_replay_loss_after"] == pytest.approx(b["with_replay_loss_after"])
        assert a["without_replay_loss_after"] == pytest.approx(b["without_replay_loss_after"])
    finally:
        world.close()


def test_refuse_non_simulation_cli(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])}
    cmd = [sys.executable, "-m", "v13.android_goal_replay_retention",
           "--home", str(tmp_path), "--count", "18", "--steps", "2"]
    rejected = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=20)
    assert rejected.returncode != 0
    assert "--simulation-only" in rejected.stderr
    accepted = subprocess.run(cmd + ["--simulation-only"], env=env,
                              capture_output=True, text=True, timeout=90)
    assert accepted.returncode == 0, accepted.stderr
    result = json.loads(accepted.stdout)
    assert result["replay"]["both_models_changed_numeric_weights"]
    assert result["native_android_executed"] is False


@pytest.mark.parametrize("seed,steps", [(True, 2), (-1, 2), (0, 0), (0, 101)])
def test_invalid_budgets_fail_before_simulator_side_effects(tmp_path, seed, steps):
    with pytest.raises(ValueError):
        run_goal_replay(tmp_path, seed=seed, steps=steps)
    assert not (tmp_path / "android_control_sim" / "state.sqlite").exists()
