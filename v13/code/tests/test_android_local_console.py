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


def test_durable_stop_blocks_new_enabled_registry_after_restart(tmp_path):
    path = tmp_path / "audit.sqlite"
    native = Native()
    with android_local_console(
        CapabilityRegistry({Capability.LAUNCH_APP: True}), path,
        transport=native, verifier=Verifier()
    ) as cmd:
        assert cmd(":android stop").status == "STOPPED"
    assert (tmp_path / "audit.sqlite.stopped").read_bytes().startswith(b"V13_ANDROID_STOP_V1")
    with android_local_console(
        CapabilityRegistry({Capability.LAUNCH_APP: True}), path,
        transport=native, verifier=Verifier()
    ) as cmd:
        assert "stopped=true" in cmd(":android status").detail
        assert cmd(":android dry launch com.example").status == "DENIED"
        assert cmd(":android execute launch com.example",
                   approve_local=lambda *_: True).status == "DENIED"
    assert native.calls == 0


def test_foreign_stop_marker_fails_closed(tmp_path):
    path = tmp_path / "audit.sqlite"
    (tmp_path / "audit.sqlite.stopped").write_text("invalid marker")
    with android_local_console(
        CapabilityRegistry({Capability.LAUNCH_APP: True}), path,
        transport=Native(), verifier=Verifier()
    ) as cmd:
        assert "stopped=true" in cmd(":android status").detail
        assert cmd(":android execute launch com.example",
                   approve_local=lambda *_: True).status == "DENIED"


def test_stop_latch_inaccessible_marker_fails_closed(tmp_path, monkeypatch):
    from v13.android_stop_latch import StopLatch
    from v13 import android_stop_latch
    latch = StopLatch(tmp_path / "audit.sqlite")
    original = android_stop_latch.os.lstat

    def inaccessible(path):
        if str(path) == str(latch.path):
            raise PermissionError("permission denied")
        return original(path)

    monkeypatch.setattr(android_stop_latch.os, "lstat", inaccessible)
    assert latch.engaged() is True


def test_stop_latch_missing_marker_allows_fresh_session(tmp_path):
    from v13.android_stop_latch import StopLatch
    assert StopLatch(tmp_path / "audit.sqlite").engaged() is False
