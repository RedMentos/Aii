"""End-to-end local Android console smoke, with synthetic native transport."""
import time

from v13.android_capability_contract import (
    ActionOutcome, Capability, CapabilityRegistry, OutcomeStatus,
)
from v13.android_local_console import android_local_console


class Native:
    def __init__(self):
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        return ActionOutcome(request.request_id, request.capability,
                             OutcomeStatus.SUCCESS, "verified", time.time())


class Verifier:
    def verify(self, request, outcome):
        return outcome.companion_receipt == "verified"


def test_console_dry_execute_status_stop_and_restart(tmp_path):
    path = tmp_path / "audit.sqlite"
    native = Native()
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
    with android_local_console(registry, path, transport=native, verifier=Verifier()) as cmd:
        assert cmd(":android status").status == "STATUS"
        assert cmd(":android dry launch com.example").status == "DRY_RUN"
        assert cmd(":android execute launch com.example").status == "DENIED"
        assert native.calls == 0
        assert cmd(":android execute launch com.example",
                   approve_local=lambda *_: True).status == "SUCCESS"
        assert native.calls == 1
        status = cmd(":android status")
        assert "outcomes=2" in status.detail
        assert "com.example" not in status.detail
        assert cmd(":android stop").status == "STOPPED"
        assert cmd(":android execute launch com.example",
                   approve_local=lambda *_: True).status == "DENIED"
        assert native.calls == 1
        assert "stopped=true" in cmd(":android status").detail
    with android_local_console(CapabilityRegistry(), path,
                               transport=native, verifier=Verifier()) as cmd:
        assert cmd(":android status").status == "STATUS"
        assert cmd(":android execute launch com.example",
                   approve_local=lambda *_: True).status == "DENIED"


def test_console_never_infers_permission_from_text(tmp_path):
    native = Native()
    with android_local_console(CapabilityRegistry(), tmp_path / "a.sqlite",
                               transport=native, verifier=Verifier()) as cmd:
        assert cmd("launch com.example").status == "INVALID"
        assert cmd(":android execute launch com.example",
                   approve_local=lambda *_: True).status == "DENIED"
        assert cmd(":android dry launch com..example").status == "INVALID"
        assert native.calls == 0
