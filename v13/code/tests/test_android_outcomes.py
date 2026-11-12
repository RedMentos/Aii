"""Software-only Android outcome contract regression."""
import pytest

from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_outcomes import execute_approved_dry_run, trusted_transition_eligible


def test_approved_action_is_audited_but_not_observed(tmp_path):
    broker = AndroidControlBroker(tmp_path / "control.db")
    broker.start()
    proposal = broker.propose("launch_app", {"package": "org.example.app"})
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    events = []
    result = execute_approved_dry_run(
        broker, proposal.action_id, on_outcome=events.append, clock=lambda: 123.0
    )
    assert result.status == "DRY_RUN_ONLY"
    assert result.observed is False
    assert result.evidence_level == "SOFTWARE_SIMULATION"
    assert result.to_event()["timestamp"] == 123.0
    assert events == [result]
    assert not trusted_transition_eligible(result)
    assert any(row[1] == "dry_run" for row in broker.events())
    with pytest.raises(ControlDenied):
        execute_approved_dry_run(broker, proposal.action_id)
    broker.close()


def test_no_unapproved_or_stopped_action(tmp_path):
    broker = AndroidControlBroker(tmp_path / "control.db")
    proposal = broker.propose("back", {})
    with pytest.raises(ControlDenied):
        execute_approved_dry_run(broker, proposal.action_id)
    broker.start()
    proposal = broker.propose("back", {})
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    broker.stop()
    with pytest.raises(ControlDenied):
        execute_approved_dry_run(broker, proposal.action_id)
    broker.close()


def test_sink_failure_does_not_replay_approved_action(tmp_path):
    broker = AndroidControlBroker(tmp_path / "control.db")
    broker.start()
    p = broker.propose("observe_ui", {})
    broker.approve(p.action_id, confirmed_by_local_ui=True)

    def failed_receiver(outcome):
        assert outcome.status == "DRY_RUN_ONLY"
        raise RuntimeError("sink unavailable")

    with pytest.raises(RuntimeError, match="sink unavailable"):
        execute_approved_dry_run(broker, p.action_id, on_outcome=failed_receiver)
    with pytest.raises(ControlDenied):
        execute_approved_dry_run(broker, p.action_id)
    assert sum(1 for _, event, *_ in broker.events() if event == "dry_run") == 1
    broker.close()
