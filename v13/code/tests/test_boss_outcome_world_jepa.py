"""Integration: Core audited outcomes must match real fake-world receipts before JEPA."""
import sqlite3
import pytest
from v13.android_goal_learning_demo import run_demo
from v13.android_control import AndroidControlBroker


def test_audited_operator_world_jepa_restart(tmp_path):
    first = run_demo(tmp_path, first=0, count=18, learn=True)
    assert first["tasks_completed_this_run"] == 18
    assert first["audited_simulated_outcome_count"] == first["action_receipt_count"]
    assert first["outcome_audit_restarted_and_matched"] is True
    assert first["learning"]["readback"]["inference_reload_exact_loss"] is True
    assert first["native_android_executed"] is False
    second = run_demo(tmp_path, first=18, count=18, learn=False)
    assert second["audited_simulated_outcome_count"] == second["action_receipt_count"]
    assert second["audited_simulated_outcome_count"] > first["audited_simulated_outcome_count"]
    assert second["total_persisted_notes"] == 36


def test_missing_accepted_outcome_is_not_treated_as_learning_evidence(tmp_path):
    run_demo(tmp_path, first=0, count=1, learn=False)
    path = tmp_path / "android_demo_broker.sqlite"
    # Adversarial corruption of an untrusted test database: runtime must reject
    # mismatch before entering JEPA. Not a claim of cryptographic integrity.
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM control_audit WHERE event='simulated_outcome'")
    with pytest.raises(ValueError, match="audit differs"):
        run_demo(tmp_path, first=1, count=1, learn=False)


def test_terminal_dispatch_failure_cannot_count_as_world_learning_receipt(tmp_path):
    """A terminal dispatch failure is not proof of an applied Notes action."""
    run_demo(tmp_path, first=0, count=1, learn=False)
    path = tmp_path / "android_demo_broker.sqlite"
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT id FROM control_audit WHERE event='simulated_outcome' ORDER BY id LIMIT 1"
        ).fetchone()
        assert row is not None
        db.execute("UPDATE control_audit SET event='simulation_dispatch_failed' WHERE id=?", row)
    with pytest.raises(ValueError, match="audit differs"):
        run_demo(tmp_path, first=1, count=1, learn=True)
    assert not (tmp_path / "android_goal_shadow_jepa.npz").exists()
