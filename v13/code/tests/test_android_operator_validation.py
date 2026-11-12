"""Operator grammar regression: malformed commands must not reach native transport."""
from v13.android_capability_contract import CapabilityRegistry
from v13.android_companion_dispatch import AndroidDispatcher
from v13.android_operator_bridge import dispatch_operator_command


def test_invalid_launch_tap_and_back_never_dispatch():
    registry = CapabilityRegistry()
    dispatcher = AndroidDispatcher(registry)
    invalid = (
        ":android dry launch com.example.app;rm",
        ":android dry launch https://example.org",
        ":android dry launch com..app",
        ":android dry tap 1.5,2",
        ":android dry tap -1,2",
        ":android dry tap 99999,2",
        ":android dry tap 1,2 extra",
        ":android dry back another_action",
        ":android dry launch com.example.app\\x7f",
    )
    for command in invalid:
        assert dispatch_operator_command(command, dispatcher).status == "INVALID"
    assert registry.history() == ()


def test_valid_package_tap_and_back_are_dry_only():
    registry = CapabilityRegistry()
    dispatcher = AndroidDispatcher(registry)
    for command in (
        ":android dry launch com.example.app",
        ":android dry tap 1080,2400",
        ":android dry back",
    ):
        assert dispatch_operator_command(command, dispatcher).status == "DRY_RUN"
    assert len(registry.history()) == 3


def test_invalid_execute_does_not_request_local_approval():
    called = []
    dispatcher = AndroidDispatcher(CapabilityRegistry())
    result = dispatch_operator_command(
        ":android execute tap 99999,1", dispatcher,
        approve_local=lambda *args: called.append(args) or True,
    )
    assert result.status == "INVALID"
    assert called == []
