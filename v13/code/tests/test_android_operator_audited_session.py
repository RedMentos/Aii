"""Real Python module integration; synthetic companion, not Android proof."""
import sqlite3
import time

import pytest

from v13.android_capability_contract import (
    ActionOutcome, Capability, CapabilityRegistry, OutcomeStatus,
)
from v13.android_operator_audited_session import audited_operator_session


class Native:
    def __init__(self, receipt="verified", status=OutcomeStatus.SUCCESS):
        self.calls = 0
        self.receipt = receipt
        self.status = status

    def execute(self, req):
        self.calls += 1
        return ActionOutcome(req.request_id, req.capability, self.status,
                             self.receipt, time.time())


class Verifier:
    def verify(self, req, outcome):
        return outcome.companion_receipt == "verified"


def test_dry_approval_execute_and_persisted_restart(tmp_path):
    path = tmp_path / "audit.sqlite"
    native = Native()
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
    with audited_operator_session(registry, path, transport=native, verifier=Verifier()) as (command, journal):
        assert command(":android dry launch com.example").status == "DRY_RUN"
        assert journal.attempts() == ()
        assert command(":android execute launch com.example").status == "DENIED"
        assert native.calls == 0
        result = command(":android execute launch com.example", approve_local=lambda c, t: True)
        assert result.status == "SUCCESS"
        assert native.calls == 1
        assert journal.attempts()[0]["state"] == "REPORTED_SUCCESS"
        assert "com.example" not in path.read_bytes().decode(errors="ignore")
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT state FROM android_action_audit").fetchone()[0] == "REPORTED_SUCCESS"
    with audited_operator_session(CapabilityRegistry(), path, transport=native, verifier=Verifier()) as (command, journal):
        assert len(journal.attempts()) == 1
        assert command(":android execute launch com.example", approve_local=lambda c, t: True).status == "DENIED"
        assert native.calls == 1


def test_forged_receipt_not_recorded_as_success(tmp_path):
    native = Native(receipt="forged")
    with audited_operator_session(CapabilityRegistry({Capability.LAUNCH_APP: True}),
                                  tmp_path / "audit.sqlite", transport=native, verifier=Verifier()) as (command, journal):
        result = command(":android execute launch com.example", approve_local=lambda c, t: True)
        assert result.status == "FAILED"
        assert journal.attempts()[0]["state"] == "FAILED"
        assert journal.attempts()[0]["receipt_present"] == 0


def test_stop_and_missing_dependencies(tmp_path):
    with pytest.raises(ValueError):
        with audited_operator_session(CapabilityRegistry(), tmp_path / "no.sqlite",
                                      transport=None, verifier=Verifier()):
            pass
    native = Native()
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
    with audited_operator_session(registry, tmp_path / "yes.sqlite",
                                  transport=native, verifier=Verifier()) as (command, journal):
        registry.stop()
        assert command(":android execute launch com.example",
                       approve_local=lambda c, t: True).status == "DENIED"
        assert native.calls == 0
        assert journal.attempts() == ()


def test_malformed_execute_rejected_before_approval_or_audit(tmp_path):
    native = Native()
    approved = []
    registry = CapabilityRegistry({Capability.LAUNCH_APP: True})
    with audited_operator_session(registry, tmp_path / "audit.sqlite",
                                  transport=native, verifier=Verifier()) as (command, journal):
        result = command(":android execute launch com..example",
                         approve_local=lambda *args: approved.append(args) or True)
        assert result.status == "INVALID"
        assert approved == []
        assert native.calls == 0
        assert journal.attempts() == ()
        valid = command(":android execute launch com.example",
                        approve_local=lambda *args: True)
        assert valid.status == "SUCCESS"
        assert native.calls == 1
        assert journal.attempts()[0]["state"] == "REPORTED_SUCCESS"
