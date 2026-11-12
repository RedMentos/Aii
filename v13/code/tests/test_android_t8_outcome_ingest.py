"""Synthetic-only Android outcome -> T8 inbox tests; not phone or learning proof."""
from dataclasses import dataclass
from enum import Enum
import sqlite3
import pytest
from v13.android_t8_outcome_ingest import ingest_verified_outcome


class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Capability(Enum):
    LAUNCH_APP = "launch_app"


@dataclass
class Outcome:
    capability: Capability
    status: Status
    companion_receipt: str | None


class Registry:
    def __init__(self, outcome):
        self.outcome = outcome

    def outcome_for(self, ident):
        return self.outcome


class Journal:
    def __init__(self, state="REPORTED_SUCCESS", present=1):
        self.state, self.present = state, present

    def attempts(self):
        return ({"request_id": "id-1", "capability": "launch_app",
                 "state": self.state, "receipt_present": self.present},)


def test_verified_inbox_restart_and_duplicate(tmp_path):
    db = tmp_path / "t8.sqlite"
    reg = Registry(Outcome(Capability.LAUNCH_APP, Status.SUCCESS, "synthetic-receipt"))
    result = ingest_verified_outcome(reg, Journal(), "id-1", db)
    assert result["training_authority"] == "SHADOW_ONLY"
    assert result["android_device_verified"] is False
    with sqlite3.connect(db) as conn:
        stored = conn.execute("SELECT episode_json FROM android_t8_episode_inbox").fetchone()[0]
    assert "synthetic-receipt" not in stored
    assert "launch_app" in stored
    with pytest.raises(ValueError, match="duplicate"):
        ingest_verified_outcome(reg, Journal(), "id-1", db)


def test_fail_closed_invalid_receipts(tmp_path):
    db = tmp_path / "t8.sqlite"
    valid = Outcome(Capability.LAUNCH_APP, Status.SUCCESS, "receipt")
    for reg, journal in (
        (Registry(None), Journal()),
        (Registry(Outcome(Capability.LAUNCH_APP, Status.FAILED, "receipt")), Journal()),
        (Registry(Outcome(Capability.LAUNCH_APP, Status.SUCCESS, None)), Journal()),
        (Registry(valid), Journal("UNKNOWN")),
        (Registry(valid), Journal(present=0)),
    ):
        with pytest.raises(ValueError):
            ingest_verified_outcome(reg, journal, "id-1", db)
    assert not db.exists()


def test_actual_audited_dispatcher_to_t8_inbox(tmp_path):
    """Real V13 dispatcher/journal modules with synthetic companion only."""
    import time
    from v13.android_capability_contract import (
        ActionOutcome, Capability as RealCapability,
        CapabilityRegistry, OutcomeStatus,
    )
    from v13.android_operator_audited_session import audited_operator_session

    class Transport:
        def execute(self, request):
            return ActionOutcome(request.request_id, request.capability,
                                 OutcomeStatus.SUCCESS, "synthetic-signed-receipt",
                                 time.time())

    class Verifier:
        def verify(self, request, outcome):
            return outcome.companion_receipt == "synthetic-signed-receipt"

    registry = CapabilityRegistry({RealCapability.LAUNCH_APP: True})
    inbox = tmp_path / "t8-inbox.sqlite"
    with audited_operator_session(
        registry, tmp_path / "android-audit.sqlite",
        transport=Transport(), verifier=Verifier()
    ) as (command, journal):
        result = command(":android execute launch com.example",
                         approve_local=lambda capability, target: True)
        assert result.status == "SUCCESS"
        episode = ingest_verified_outcome(registry, journal, result.request_id, inbox)
        assert episode["capability"] == "launch_app"
        assert episode["training_authority"] == "SHADOW_ONLY"
    with sqlite3.connect(inbox) as db:
        assert db.execute("SELECT count(*) FROM android_t8_episode_inbox").fetchone()[0] == 1
