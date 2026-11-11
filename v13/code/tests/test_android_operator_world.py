"""Real integration regression: Core operator -> persistent world -> JEPA."""
import pytest
from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_control_sim import SimulatedAndroidWorld
from v13.android_operator_world import (
    PersistentWorldCompanion, synthetic_operator_action,
)
from v13.android_goal_learning_demo import run_demo
from v13.android_companion_registry import CapabilityRegistry, CompanionTransport
from v13.android_operator_loop import AndroidOperatorLoop


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
    result = run_demo(tmp_path, first=0, count=18, seed=17, learn=True)
    assert result["native_android_executed"] is False
    assert result["tasks_completed_this_run"] == 18
    assert result["learning"]["readback"]["inference_reload_exact_loss"] is True
    assert result["action_receipt_count"] > 0


def test_typed_transport_rejects_tampering_before_world_mutation(tmp_path):
    broker = AndroidControlBroker(tmp_path / "typed-audit.db")
    world = SimulatedAndroidWorld(tmp_path)
    try:
        broker.start()
        companion = PersistentWorldCompanion(world)
        transport = CompanionTransport(CapabilityRegistry(), simulator=companion)
        loop = AndroidOperatorLoop(broker, companion=transport)
        pending = loop.run_from_brain("launch_app", {"package": "org.v13.demo.notes"})
        broker.approve(pending.action_id, confirmed_by_local_ui=True)
        envelope = broker.execute(pending.action_id, dry_run=True)
        for changed in (
            dict(envelope, status="LIVE"),
            dict(envelope, args={"package": "org.evil.app"}),
            dict(envelope, digest="0" * 64),
            dict(envelope, extra="untrusted"),
        ):
            with pytest.raises(ControlDenied):
                transport.dispatch(changed)
            assert world.receipt_count() == 0
        result = transport.dispatch(envelope)
        assert result.action_id == pending.action_id
        assert companion.last_receipt["simulation_applied"] is True
        assert world.receipt_count() == 1
    finally:
        world.close()
        broker.close()
