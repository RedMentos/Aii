import pytest
from v13.android_capability_contract import (
    Capability, CapabilityRegistry, ActionOutcome, OutcomeStatus,
)

def test_default_off_and_dry_run():
    registry = CapabilityRegistry()
    with pytest.raises(PermissionError):
        registry.request(Capability.TAP, "20,30", dry_run=False)
    req = registry.request(Capability.TAP, "20,30")
    with pytest.raises(PermissionError):
        registry.settle(ActionOutcome(req.request_id, Capability.TAP, OutcomeStatus.SUCCESS, "fake", 1))
    assert not registry.history()

def test_companion_receipt_and_stop():
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
    req = registry.request(Capability.LAUNCH_APP, "com.example.app", dry_run=False)
    registry.settle(ActionOutcome(req.request_id, Capability.LAUNCH_APP, OutcomeStatus.SUCCESS, "receipt", 1))
    assert registry.history()[0].status == OutcomeStatus.SUCCESS
    registry.stop()
    with pytest.raises(PermissionError):
        registry.request(Capability.LAUNCH_APP, "com.example.app", dry_run=False)

def test_mismatch_and_invalid_target():
    registry = CapabilityRegistry()
    with pytest.raises(ValueError):
        registry.request(Capability.TAP, "bad\ncommand")
    req = registry.request(Capability.TAP, "20,30")
    with pytest.raises(ValueError):
        registry.settle(ActionOutcome(req.request_id, Capability.BACK, OutcomeStatus.DENIED, None, 1))
