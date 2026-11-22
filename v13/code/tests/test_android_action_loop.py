"""Synthetic broker-to-C5 outcome contract regression tests."""
import pytest
from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_action_loop import AndroidActionLoop


def test_local_confirmation_and_one_shot_simulation(tmp_path):
    broker = AndroidControlBroker(tmp_path / "audit.sqlite")
    events = []
    loop = AndroidActionLoop(broker, events.append, clock=lambda: 123.)
    broker.start()
    p = loop.propose("back", {})
    with pytest.raises(ControlDenied):
        loop.approve_local(p.action_id)
    assert not events
    p = loop.propose("back", {})
    loop.approve_local(p.action_id, local_confirmation=True)
    with pytest.raises(ControlDenied):
        loop.dispatch_live(p.action_id)
    result = loop.dry_run(p.action_id)
    assert result.status == "SIMULATED_NOT_EXECUTED"
    assert events[0]["source"] == "LOCAL_DRY_RUN"
    assert events[0]["request_digest"] == p.digest
    with pytest.raises(ControlDenied):
        loop.dry_run(p.action_id)
    broker.close()


def test_stop_revokes_approved_action(tmp_path):
    broker = AndroidControlBroker(tmp_path / "audit.sqlite")
    events = []
    loop = AndroidActionLoop(broker, events.append)
    broker.start()
    p = loop.propose("launch_app", {"package": "org.example.app"})
    loop.approve_local(p.action_id, local_confirmation=True)
    broker.stop()
    with pytest.raises(ControlDenied):
        loop.dry_run(p.action_id)
    assert not events
    broker.close()
