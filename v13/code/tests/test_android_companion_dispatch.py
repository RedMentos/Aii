from v13.android_capability_contract import (
    ActionOutcome, Capability, CapabilityRegistry, OutcomeStatus,
)
from v13.android_companion_dispatch import AndroidDispatcher


class FakeCompanion:
    def __init__(self, status=OutcomeStatus.SUCCESS):
        self.status = status
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        return ActionOutcome(request.request_id, request.capability, self.status, "receipt", 1.0)


class FakeVerifier:
    def __init__(self, accepted):
        self.accepted = accepted
        self.calls = 0

    def verify(self, request, outcome):
        self.calls += 1
        return self.accepted


def test_dry_run_never_invokes_companion():
    transport = FakeCompanion()
    dispatcher = AndroidDispatcher(CapabilityRegistry(), transport=transport)
    result = dispatcher.dispatch(Capability.TAP, "12,24")
    assert result.outcome.status == OutcomeStatus.DRY_RUN
    assert transport.calls == 0


def test_enabled_without_authenticated_transport_is_denied():
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
    result = AndroidDispatcher(registry).dispatch(Capability.LAUNCH_APP, "com.example.app", dry_run=False)
    assert result.outcome.status == OutcomeStatus.DENIED
    assert registry.history() == (result.outcome,)


def test_authenticated_success_and_unverified_failure():
    for accepted, expected in ((True, OutcomeStatus.SUCCESS), (False, OutcomeStatus.FAILED)):
        registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
        verifier = FakeVerifier(accepted)
        transport = FakeCompanion()
        result = AndroidDispatcher(registry, transport=transport, verifier=verifier).dispatch(
            Capability.LAUNCH_APP, "com.example.app", dry_run=False
        )
        assert result.outcome.status == expected
        assert transport.calls == verifier.calls == 1
        assert registry.history() == (result.outcome,)


def test_bad_native_response_fails_without_retry():
    class Mismatch:
        def execute(self, request):
            return ActionOutcome("different", request.capability, OutcomeStatus.SUCCESS, "receipt", 1.0)

    registry = CapabilityRegistry({Capability.TAP: True})
    result = AndroidDispatcher(registry, transport=Mismatch(), verifier=FakeVerifier(True)).dispatch(
        Capability.TAP, "12,24", dry_run=False
    )
    assert result.outcome.status == OutcomeStatus.FAILED
    assert len(registry.history()) == 1


def test_disabled_capability_never_reaches_transport():
    import pytest
    transport = FakeCompanion()
    with pytest.raises(PermissionError):
        AndroidDispatcher(CapabilityRegistry(), transport=transport, verifier=FakeVerifier(True)).dispatch(
            Capability.TAP, "12,24", dry_run=False
        )
    assert transport.calls == 0


def test_stop_during_native_call_cancels_once_and_rejects_late_success():
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})

    class StopThenSuccess:
        def execute(self, request):
            registry.stop()
            return ActionOutcome(request.request_id, request.capability,
                                 OutcomeStatus.SUCCESS, "late-receipt", 1.0)

    result = AndroidDispatcher(
        registry, transport=StopThenSuccess(), verifier=FakeVerifier(True)
    ).dispatch(Capability.LAUNCH_APP, "com.example.app", dry_run=False)
    assert result.outcome.status == OutcomeStatus.CANCELLED
    assert registry.history() == (result.outcome,)
    assert registry.outcome_for(result.request.request_id) == result.outcome


def test_stop_cancels_multiple_pending_requests_with_audit():
    registry = CapabilityRegistry({Capability.TAP: True})
    a = registry.request(Capability.TAP, "1,2", dry_run=False)
    b = registry.request(Capability.TAP, "3,4", dry_run=False)
    registry.stop()
    assert {o.request_id for o in registry.history()} == {a.request_id, b.request_id}
    assert all(o.status == OutcomeStatus.CANCELLED for o in registry.history())
    import pytest
    with pytest.raises(ValueError):
        registry.settle(ActionOutcome(a.request_id, a.capability,
                                      OutcomeStatus.SUCCESS, "late", 1.0))
    assert len(registry.history()) == 2
