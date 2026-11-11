"""Real integration regression: Core operator -> persistent world -> JEPA."""
import pytest
from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_control_sim import SimulatedAndroidWorld
from v13.android_operator_world import (
    PersistentWorldCompanion, synthetic_operator_action,
)
from v13.android_goal_learning_demo import run_demo


def test_operator_persists_real_synthetic_world_receipt(tmp_path):
    broker = AndroidControlBroker(tmp_path / "audit.db")
    world = SimulatedAndroidWorld(tmp_path)
    try:
        broker.start()
        receipt = synthetic_operator_action(
            broker, world, "launch_app", {"package": "org.v13.demo.notes"})
        assert receipt["simulation_applied"] is True
        assert receipt["native_android_executed"] is False
        assert world.receipt_count() == 1
        events = [e[1] for e in broker.events()]
        assert events.index("proposed") < events.index("approved") < events.index("dry_run")
        broker.stop()
        with pytest.raises(ControlDenied):
            synthetic_operator_action(broker, world, "back", {})
        assert world.receipt_count() == 1
    finally:
        world.close()
        broker.close()


def test_world_companion_rejects_live_envelope_before_side_effect(tmp_path):
    world = SimulatedAndroidWorld(tmp_path)
    try:
        companion = PersistentWorldCompanion(world)
        with pytest.raises(ControlDenied):
            companion.dispatch({"status": "LIVE", "action_id": "fake", "capability": "back"})
        assert world.receipt_count() == 0
    finally:
        world.close()


def test_full_goal_uses_operator_and_preserves_restart_and_learning(tmp_path):
    result = run_demo(tmp_path, first=0, count=4, seed=17, learn=True)
    assert result["native_android_executed"] is False
    assert result["tasks_completed_this_run"] == 4
    assert result["learning"]["readback"]["inference_reload_exact_loss"] is True
    assert result["action_receipt_count"] > 0
