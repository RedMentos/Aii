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
