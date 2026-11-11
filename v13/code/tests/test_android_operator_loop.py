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


def test_outcome_audit_survives_restart(tmp_path):
    db = tmp_path / "audit.db"
    broker = AndroidControlBroker(db)
    broker.start()
    loop = AndroidOperatorLoop(broker)
    request = loop.run_from_brain("back", {})
    loop.approved_simulation(request.action_id, local_confirmation=True)
    broker.close()
    reopened = AndroidControlBroker(db)
    events = [row[1] for row in reopened.events() if row[0] == request.action_id]
    assert events == ["proposed", "approved", "dry_run", "simulated_outcome"]
    reopened.close()


def test_forged_companion_result_is_rejected(tmp_path):
    from v13.android_operator_loop import ActionOutcome

    class ForgedCompanion:
        def dispatch(self, envelope):
            return ActionOutcome(envelope["action_id"], "tap", "SIMULATED", 0, "SIMULATED_COMPANION")

    broker = AndroidControlBroker(tmp_path / "audit.db")
    broker.start()
    loop = AndroidOperatorLoop(broker, companion=ForgedCompanion())
    request = loop.run_from_brain("back", {})
    with pytest.raises(ControlDenied, match="outcome mismatch"):
        loop.approved_simulation(request.action_id, local_confirmation=True)
    assert "outcome_rejected" in [row[1] for row in broker.events()]
    broker.close()


def test_companion_dispatch_failure_is_audited(tmp_path):
    class BrokenCompanion:
        def dispatch(self, envelope):
            raise RuntimeError("companion unavailable")

    broker = AndroidControlBroker(tmp_path / "audit.db")
    broker.start()
    loop = AndroidOperatorLoop(broker, companion=BrokenCompanion())
    request = loop.run_from_brain("back", {})
    with pytest.raises(RuntimeError):
        loop.approved_simulation(request.action_id, local_confirmation=True)
    assert "simulation_dispatch_failed" in [row[1] for row in broker.events()]
    broker.close()


def test_duplicate_and_unissued_outcomes_cannot_be_logged(tmp_path):
    from v13.android_operator_loop import ActionOutcome
    broker = AndroidControlBroker(tmp_path / "audit.db")
    broker.start()
    p = broker.propose("back", {})
    broker.approve(p.action_id, confirmed_by_local_ui=True)
    envelope = broker.execute(p.action_id)
    outcome = ActionOutcome(p.action_id, "back", "SIMULATED", 0, "SIMULATED_COMPANION")
    broker.record_simulated_outcome(envelope, outcome)
    with pytest.raises(ControlDenied, match="duplicate"):
        broker.record_simulated_outcome(envelope, outcome)
    with pytest.raises(ControlDenied, match="unissued"):
        broker.record_simulated_outcome(dict(envelope, action_id="f" * 32), outcome)
    assert [row[1] for row in broker.events() if row[0] == p.action_id].count("simulated_outcome") == 1
    broker.close()


@pytest.mark.parametrize("alter", [
    lambda e: dict(e, capability="tap"),
    lambda e: dict(e, args={"x": 1, "y": 2}),
    lambda e: dict(e, digest="0" * 64),
    lambda e: dict(e, status="LIVE"),
])
def test_simulation_audit_rejects_mutated_issued_envelope(tmp_path, alter):
    from v13.android_operator_loop import ActionOutcome
    broker = AndroidControlBroker(tmp_path / "audit.db")
    broker.start()
    p = broker.propose("back", {})
    broker.approve(p.action_id, confirmed_by_local_ui=True)
    envelope = broker.execute(p.action_id)
    outcome = ActionOutcome(p.action_id, "back", "SIMULATED", 0, "SIMULATED_COMPANION")
    with pytest.raises(ControlDenied):
        broker.record_simulated_outcome(alter(envelope), outcome)
    with pytest.raises(ControlDenied):
        broker.record_simulated_failure(alter(envelope))
    assert not any(row[1] == "simulated_outcome" for row in broker.events())
    broker.record_simulated_outcome(envelope, outcome)
    broker.close()


def test_stop_switch_rejects_late_simulation_receipts(tmp_path):
    from v13.android_operator_loop import ActionOutcome
    broker = AndroidControlBroker(tmp_path / "audit.db")
    broker.start()
    p = broker.propose("back", {})
    broker.approve(p.action_id, confirmed_by_local_ui=True)
    envelope = broker.execute(p.action_id)
    broker.stop()
    outcome = ActionOutcome(p.action_id, "back", "SIMULATED", 0, "SIMULATED_COMPANION")
    with pytest.raises(ControlDenied, match="stopped"):
        broker.record_simulated_outcome(envelope, outcome)
    with pytest.raises(ControlDenied, match="stopped"):
        broker.record_simulated_failure(envelope)
    assert not any(row[1] == "simulated_outcome" for row in broker.events())
    broker.close()


def test_stop_restart_revokes_issued_receipt(tmp_path):
    from v13.android_operator_loop import ActionOutcome
    db = tmp_path / "audit.db"
    broker = AndroidControlBroker(db)
    broker.start()
    proposal = broker.propose("back", {})
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    envelope = broker.execute(proposal.action_id)
    broker.close()
    reopened = AndroidControlBroker(db)
    reopened.start()
    outcome = ActionOutcome(proposal.action_id, "back", "SIMULATED", 0, "SIMULATED_COMPANION")
    with pytest.raises(ControlDenied, match="revoked"):
        reopened.record_simulated_outcome(envelope, outcome)
    with pytest.raises(ControlDenied, match="revoked"):
        reopened.record_simulated_failure(envelope)
    reopened.close()


def test_dispatch_failure_is_terminal_and_cannot_become_success(tmp_path):
    from v13.android_operator_loop import ActionOutcome
    broker = AndroidControlBroker(tmp_path / "audit.db")
    broker.start()
    proposal = broker.propose("back", {})
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    envelope = broker.execute(proposal.action_id)
    broker.record_simulated_failure(envelope)
    outcome = ActionOutcome(proposal.action_id, "back", "SIMULATED", 0, "SIMULATED_COMPANION")
    with pytest.raises(ControlDenied, match="finalized"):
        broker.record_simulated_outcome(envelope, outcome)
    with pytest.raises(ControlDenied, match="finalized"):
        broker.record_simulated_failure(envelope)
    assert [e[1] for e in broker.events() if e[0] == proposal.action_id].count("simulation_dispatch_failed") == 1
    broker.close()
