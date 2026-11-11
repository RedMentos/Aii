import pytest
from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_operator_loop import AndroidOperatorLoop, SimulatedCompanion


def test_brain_to_operator_to_simulated_outcome(tmp_path):
    broker = AndroidControlBroker(tmp_path / "audit.db")
    loop = AndroidOperatorLoop(broker)
    broker.start()  # represents trusted local UI, not the model
    request = loop.run_from_brain("launch_app", {"package": "org.example.app"})
    assert request.status == "AWAITING_LOCAL_APPROVAL"
    with pytest.raises(ControlDenied):
        loop.approved_simulation(request.action_id)
    request = loop.run_from_brain("back", {})
    outcome = loop.approved_simulation(request.action_id, local_confirmation=True)
    assert outcome.status == "SIMULATED"
    assert outcome.source == "SIMULATED_COMPANION"
    assert outcome.action_id == request.action_id
    with pytest.raises(ControlDenied):
        loop.approved_simulation(request.action_id, local_confirmation=True)
    assert any(row[1] == "dry_run" for row in broker.events())
    broker.close()


def test_stop_blocks_pending_and_simulation_rejects_live_envelope(tmp_path):
    broker = AndroidControlBroker(tmp_path / "audit.db")
    broker.start()
    loop = AndroidOperatorLoop(broker)
    request = loop.run_from_brain("observe_ui", {})
    broker.stop()
    with pytest.raises(ControlDenied):
        loop.approved_simulation(request.action_id, local_confirmation=True)
    with pytest.raises(ControlDenied):
        SimulatedCompanion().dispatch({"status": "LIVE", "action_id": "a", "capability": "back"})
    broker.close()
