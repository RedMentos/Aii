"""The moral adviser is actually called by the synthetic Android action path."""
from dataclasses import replace
import pytest
from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_control_sim import SimulatedAndroidWorld
from v13.android_goal_learning_demo import run_demo, _synthetic_action
from v13.behavior_governor import review_behavior, neutral_signals


def test_simulated_goal_actions_go_through_behavior_adviser(tmp_path):
    result = run_demo(tmp_path, first=0, count=4, learn=False)
    assert result["tasks_completed_this_run"] == 4
    assert result["behavior_review"] == "CONTEXTUAL_ADVISORY_ON_EACH_SYNTHETIC_ACTION"
    assert result["native_android_executed"] is False


def test_advisory_deny_stops_synthetic_broker_before_any_action(tmp_path, monkeypatch):
    import v13.android_goal_learning_demo as demo
    broker = AndroidControlBroker(tmp_path / "audit.sqlite")
    world = SimulatedAndroidWorld(tmp_path)
    broker.start()
    try:
        denied = replace(review_behavior(neutral_signals()),
                         guidance="REJECT_UNAUTHORIZED_ACTION")
        monkeypatch.setattr(demo, "review_behavior", lambda *a, **k: denied)
        with pytest.raises(ControlDenied, match="independent review"):
            _synthetic_action(broker, world, "launch_app",
                              {"package": "org.v13.demo.notes"})
        assert world.receipt_count() == 0
        assert not any(row[1] == "proposed" for row in broker.events())
    finally:
        world.close()
        broker.close()
