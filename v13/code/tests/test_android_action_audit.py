import sqlite3
import pytest

from v13.android_action_audit import DurableCompanionTransport, AuditUnavailable
from v13.android_capability_contract import (
    ActionRequest, ActionOutcome, Capability, OutcomeStatus,
)


def request(request_id="one", dry_run=False):
    return ActionRequest(request_id, Capability.LAUNCH_APP, "com.example", 1.0, dry_run)


class Fake:
    def __init__(self, outcome=None, fail=False):
        self.calls = 0
        self.outcome = outcome
        self.fail = fail

    def execute(self, req):
        self.calls += 1
        if self.fail:
            raise TimeoutError("native outcome unknown")
        return self.outcome or ActionOutcome(
            req.request_id, req.capability, OutcomeStatus.SUCCESS, "unverified", 2.0
        )


def test_persist_attempt_restart_and_reject_replay(tmp_path):
    path = tmp_path / "audit.sqlite"
    fake = Fake()
    first = DurableCompanionTransport(path, fake)
    result = first.execute(request())
    assert result.status == OutcomeStatus.SUCCESS
    assert first.attempts()[0]["state"] == "REPORTED_SUCCESS"
    assert "com.example" not in path.read_bytes().decode("utf-8", errors="ignore")
    first.close()
    second = DurableCompanionTransport(path, fake)
    with pytest.raises(AuditUnavailable):
        second.execute(request())
    assert fake.calls == 1
    assert second.attempts()[0]["receipt_present"] == 1
    second.close()


def test_failed_transport_stays_unknown_after_restart(tmp_path):
    path = tmp_path / "audit.sqlite"
    fake = Fake(fail=True)
    journal = DurableCompanionTransport(path, fake)
    with pytest.raises(TimeoutError):
        journal.execute(request())
    journal.close()
    restarted = DurableCompanionTransport(path, fake)
    assert restarted.attempts()[0]["state"] == "UNKNOWN"
    with pytest.raises(AuditUnavailable):
        restarted.execute(request())
    assert fake.calls == 1
    restarted.close()


def test_dry_run_never_calls_native(tmp_path):
    fake = Fake()
    journal = DurableCompanionTransport(tmp_path / "audit.sqlite", fake)
    with pytest.raises(PermissionError):
        journal.execute(request(dry_run=True))
    assert fake.calls == 0
    assert journal.attempts() == ()
    journal.close()


def test_dispatcher_integration_requires_capability_and_verifier(tmp_path):
    from v13.android_action_audit import build_audited_dispatcher
    from v13.android_capability_contract import CapabilityRegistry

    class Verifier:
        def verify(self, req, outcome):
            return outcome.companion_receipt == "unverified"

    fake = Fake()
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
    with pytest.raises(ValueError):
        build_audited_dispatcher(registry, tmp_path / "bad.sqlite", fake, None)
    dispatcher, journal = build_audited_dispatcher(
        registry, tmp_path / "audit.sqlite", fake, Verifier()
    )
    assert dispatcher.dispatch(Capability.LAUNCH_APP, "com.example", dry_run=True).outcome.status == OutcomeStatus.DRY_RUN
    assert fake.calls == 0
    assert journal.attempts() == ()
    assert dispatcher.dispatch(Capability.LAUNCH_APP, "com.example", dry_run=False).outcome.status == OutcomeStatus.SUCCESS
    assert fake.calls == 1
    assert journal.attempts()[0]["state"] == "REPORTED_SUCCESS"
    registry.stop()
    with pytest.raises(PermissionError):
        dispatcher.dispatch(Capability.LAUNCH_APP, "com.example", dry_run=False)
    journal.close()


def test_off_capability_cannot_reach_audited_transport(tmp_path):
    from v13.android_action_audit import build_audited_dispatcher
    from v13.android_capability_contract import CapabilityRegistry

    class Verifier:
        def verify(self, req, outcome):
            return True

    fake = Fake()
    dispatcher, journal = build_audited_dispatcher(
        CapabilityRegistry(), tmp_path / "audit.sqlite", fake, Verifier()
    )
    with pytest.raises(PermissionError):
        dispatcher.dispatch(Capability.LAUNCH_APP, "com.example", dry_run=False)
    assert fake.calls == 0
    assert journal.attempts() == ()
    journal.close()
