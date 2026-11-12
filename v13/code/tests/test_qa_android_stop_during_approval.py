"""QA regression: a durable stop arriving during approval must prevent dispatch.

Synthetic only. No Android OS authorization or device proof.
"""
import time

from v13.android_capability_contract import ActionOutcome, Capability, CapabilityRegistry, OutcomeStatus
from v13.android_local_console import android_local_console
from v13.android_stop_latch import StopLatch


class FakeNative:
    def __init__(self):
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        return ActionOutcome(request.request_id, request.capability,
                             OutcomeStatus.SUCCESS, "verified", time.time())


class FakeVerifier:
    def verify(self, request, outcome):
        return outcome.companion_receipt == "verified"


def test_stop_arriving_during_local_approval_denies_dispatch(tmp_path):
    audit = tmp_path / "audit.sqlite"
    native = FakeNative()
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})

    def approval_then_external_stop(*_):
        # Deterministic interleaving: another session stops the operator
        # after handle() checked the latch, but before dispatch().
        StopLatch(audit).engage()
        return True

    with android_local_console(registry, audit, transport=native,
                               verifier=FakeVerifier()) as command:
        result = command(":android execute launch com.example",
                         approve_local=approval_then_external_stop)
        assert result.status == "DENIED"
        assert native.calls == 0
        assert "stopped=true" in command(":android status").detail
