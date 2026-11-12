from v13.android_capability_contract import Capability, CapabilityRegistry
from v13.android_companion_dispatch import AndroidDispatcher
from v13.android_operator_bridge import dispatch_operator_command

def test_dry_run_without_native_transport():
    d = AndroidDispatcher(CapabilityRegistry())
    result = dispatch_operator_command(':android dry launch com.example.app', d)
    assert result.status == 'DRY_RUN'
    assert result.capability == 'launch_app'
    assert result.request_id

def test_execute_needs_local_approval_and_native_transport():
    d = AndroidDispatcher(CapabilityRegistry({Capability.LAUNCH_APP: True}))
    assert dispatch_operator_command(':android execute launch com.example.app', d).status == 'DENIED'
    assert dispatch_operator_command(':android execute launch com.example.app', d, approve_local=lambda c, t: False).status == 'DENIED'
    assert dispatch_operator_command(':android execute launch com.example.app', d, approve_local=lambda c, t: True).status == 'DENIED'

def test_invalid_and_sensitive_text_not_echoed():
    d = AndroidDispatcher(CapabilityRegistry())
    for line in ('launch com.example.app', ':android execute launch', ':android dry type secret' + chr(10) + 'other', ':android dry unknown target'):
        result = dispatch_operator_command(line, d)
        assert result.status in ('INVALID', 'DENIED')
        assert 'secret' not in result.detail

def test_back_default_and_stop():
    registry = CapabilityRegistry()
    d = AndroidDispatcher(registry)
    assert dispatch_operator_command(':android dry back', d).status == 'DRY_RUN'
    registry.stop()
    assert dispatch_operator_command(':android dry back', d).status == 'DENIED'
