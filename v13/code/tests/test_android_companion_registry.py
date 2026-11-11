import hashlib
import json
import pytest

from v13.android_companion_registry import CapabilityRegistry, Capability, CompanionTransport
from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_operator_loop import AndroidOperatorLoop


def test_brain_to_approved_companion_simulation(tmp_path):
    broker = AndroidControlBroker(tmp_path / "control.sqlite")
    registry = CapabilityRegistry()
    transport = CompanionTransport(registry)
    broker.start()
    proposal = broker.propose("launch_app", {"package": "org.example.notes"})
    with pytest.raises(ControlDenied):
        broker.approve(proposal.action_id, confirmed_by_local_ui=False)
    proposal = broker.propose("launch_app", {"package": "org.example.notes"})
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    envelope = broker.execute(proposal.action_id, dry_run=True)
    result = transport.dispatch_simulated(envelope)
    assert result.action_id == proposal.action_id
    assert result.status == "SIMULATED"
    assert result.source == "SIMULATED_COMPANION"
    with pytest.raises(ControlDenied):
        broker.execute(proposal.action_id)
    broker.close()


def test_tampering_and_live_execution_fail_closed(tmp_path):
    broker = AndroidControlBroker(tmp_path / "control.sqlite")
    broker.start()
    p = broker.propose("tap", {"x": 12, "y": 23})
    broker.approve(p.action_id, confirmed_by_local_ui=True)
    envelope = broker.execute(p.action_id)
    transport = CompanionTransport(CapabilityRegistry())
    for changed in (
        dict(envelope, args={"x": 13, "y": 23}),
        dict(envelope, status="APPROVED"),
        dict(envelope, action_id="bad"),
        dict(envelope, extra=True),
    ):
        with pytest.raises(ControlDenied):
            transport.dispatch_simulated(changed)
    with pytest.raises(ControlDenied):
        transport.dispatch_live(envelope)
    broker.close()


def test_registry_defaults_off_and_rejects_unsupported():
    registry = CapabilityRegistry()
    assert len(registry.report()) == 6
    assert all(not c["enabled"] for c in registry.report())
    with pytest.raises(ValueError):
        CapabilityRegistry([Capability("shell", "TERMUX", "ANY")])
    with pytest.raises(ValueError):
        CapabilityRegistry([Capability("back", "ACCESSIBILITY", "A")] * 2)
    with pytest.raises(ControlDenied):
        registry.get("shell")


def test_existing_operator_loop_uses_registry_transport_end_to_end(tmp_path):
    """Real SQLite broker -> trusted simulated approval -> typed registry transport."""
    broker = AndroidControlBroker(tmp_path / "operator.sqlite")
    transport = CompanionTransport(CapabilityRegistry())
    loop = AndroidOperatorLoop(broker, companion=transport)
    broker.start()
    pending = loop.run_from_brain("launch_app", {"package": "org.example.notes"})
    assert pending.status == "AWAITING_LOCAL_APPROVAL"
    assert pending.source == "BRAIN_PROPOSAL"
    outcome = loop.approved_simulation(pending.action_id, local_confirmation=True)
    assert outcome.status == "SIMULATED"
    assert outcome.action_id == pending.action_id
    assert outcome.capability == "launch_app"
    with pytest.raises(ControlDenied):
        loop.approved_simulation(pending.action_id, local_confirmation=True)
    assert [row[1] for row in broker.events()].count("dry_run") == 1
    broker.stop()
    pending = loop.run_from_brain("back", {})
    with pytest.raises(ControlDenied):
        loop.approved_simulation(pending.action_id, local_confirmation=True)
    broker.close()


def test_declared_enabled_capability_cannot_claim_native_permission():
    with pytest.raises(ValueError, match="activation unavailable"):
        CapabilityRegistry([Capability("launch_app", "ANDROID_INTENT", "LOCAL_OPERATOR", enabled=True)])
