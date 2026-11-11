"""Android control lifecycle QA: approval boundaries, restart and audit durability.

Runs against the real broker on the Android-first Core candidate. These tests
do NOT claim AccessibilityService/MediaProjection or device execution.
"""
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from v13.android_control import AndroidControlBroker, ControlDenied


def test_restart_requires_new_operator_start_and_new_approval(tmp_path):
    db = tmp_path / "audit.sqlite"
    first = AndroidControlBroker(db)
    first.start()
    pending = first.propose("tap", {"x": 12, "y": 34})
    first.approve(pending.action_id, confirmed_by_local_ui=True)
    first.close()

    restarted = AndroidControlBroker(db)
    with pytest.raises(ControlDenied):
        restarted.execute(pending.action_id)
    with pytest.raises(ControlDenied):
        restarted.approve(pending.action_id, confirmed_by_local_ui=True)
    restarted.start()
    with pytest.raises(ControlDenied):
        restarted.execute(pending.action_id)
    events = restarted.events()
    assert [row[1] for row in events].count("operator_stop") == 1
    assert [row[1] for row in events].count("approved") == 1
    assert any(row[1] == "execution_denied" for row in events)
    restarted.close()


def test_concurrent_execute_is_one_shot_and_audited(tmp_path):
    broker = AndroidControlBroker(tmp_path / "audit.sqlite")
    broker.start()
    proposal = broker.propose("back", {})
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)

    def attempt(_):
        try:
            return broker.execute(proposal.action_id)["status"]
        except ControlDenied:
            return "DENIED"

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, range(48)))
    assert results.count("DRY_RUN_ONLY") == 1
    assert results.count("DENIED") == 47
    events = [row[1] for row in broker.events() if row[0] == proposal.action_id]
    assert events.count("dry_run") == 1
    assert events.count("execution_denied") == 47
    broker.close()


def test_stop_revokes_all_approvals_and_audit_survives_reopen(tmp_path):
    db = tmp_path / "audit.sqlite"
    broker = AndroidControlBroker(db)
    broker.start()
    approved = broker.propose("type_text", {"text": "hello"})
    broker.approve(approved.action_id, confirmed_by_local_ui=True)
    broker.stop()
    broker.start()
    with pytest.raises(ControlDenied):
        broker.execute(approved.action_id)
    broker.close()

    with sqlite3.connect(db) as conn:
        persisted = conn.execute(
            "SELECT event FROM control_audit WHERE action_id = ? ORDER BY id",
            (approved.action_id,),
        ).fetchall()
    assert [row[0] for row in persisted] == [
        "proposed", "approved", "execution_denied"
    ]
