import json

from v13.flow_audit_dashboard import snapshot
from v13.store import Store


def test_dashboard_snapshot_is_global_latest_completed_turn_redacted_and_read_only(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        first_session = store.new_session("first private chat")
        first_event = store.event(first_session, "PRIVATE_USER_ONE")
        store.message(
            first_session, first_event["event_id"], "assistant", "PRIVATE_ASSISTANT_ONE",
            status="DEADLINE", metadata={
                "runner": {"role": "C3_LANGUAGE", "status": "DEADLINE",
                           "actual_model": "fixture-c3", "prompt_tokens": 5,
                           "generated_tokens": 0, "synthetic": True}
            },
        )
        second_session = store.new_session("second private chat")
        second_event = store.event(second_session, "PRIVATE_USER_TWO")
        store.message(
            second_session, second_event["event_id"], "assistant", "PRIVATE_ASSISTANT_TWO",
            status="FINAL", metadata={
                "runner": {"role": "C3_LANGUAGE", "status": "FINAL",
                           "actual_model": "fixture-c3", "prompt_tokens": 13,
                           "generated_tokens": 4, "synthetic": True}
            },
        )
        # A newer active session with no completed assistant turn must not
        # make the dashboard imply that the prior completed turn was current.
        pending_session = store.new_session("active chat without a completed answer")
        pending_event = store.event(pending_session, "PRIVATE_PENDING_TEXT")
        store.message(
            pending_session, pending_event["event_id"], "assistant", "PRIVATE_PENDING_ASSISTANT",
            status="STREAMING", metadata={
                "runner": {"role": "C3_LANGUAGE", "status": "STREAMING",
                           "actual_model": "/private/model/path", "prompt_tokens": 999,
                           "generated_tokens": 0}
            },
        )
    finally:
        store.close()

    db = home / "data" / "db" / "brain.sqlite3"
    before = db.read_bytes()
    result = snapshot(home)
    after = db.read_bytes()
    rendered = json.dumps(result, ensure_ascii=False)

    assert result["availability"] == "AVAILABLE"
    assert result["selection_scope"] == "LATEST_COMPLETED_TURN_ALL_SESSIONS"
    assert result["assistant_status"] == "FINAL"
    assert result["c3"]["prompt_tokens"] == 13
    assert result["c3"]["generated_tokens"] == 4
    assert result["evidence_level"] == "SYNTHETIC_FIXTURE"
    assert result["redmi_status"] == "REDMI_UNVERIFIED"
    assert result["read_only"] is True
    assert result["private_text_returned"] is False
    assert before == after
    for secret in (
        "PRIVATE_USER_ONE", "PRIVATE_ASSISTANT_ONE",
        "PRIVATE_USER_TWO", "PRIVATE_ASSISTANT_TWO",
        first_event["event_id"], second_event["event_id"], pending_event["event_id"],
        first_session, second_session, pending_session,
        "PRIVATE_PENDING_TEXT",
    ):
        assert secret not in rendered


def test_dashboard_snapshot_reports_no_turns(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    store.close()
    assert snapshot(home) == {
        "availability": "NO_TURNS",
        "selection_scope": "LATEST_COMPLETED_TURN_ALL_SESSIONS",
    }


def test_dashboard_snapshot_fails_closed_when_store_is_missing(tmp_path):
    assert snapshot(tmp_path / "missing") == {
        "availability": "UNAVAILABLE",
        "reason": "AUDIT_READ_FAILED",
    }


def test_dashboard_snapshot_reports_no_completed_turn_when_only_streaming_assistant_exists(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        session = store.new_session("pending only")
        event = store.event(session, "PRIVATE_PENDING_ONLY_TEXT")
        store.message(
            session, event["event_id"], "assistant", "PRIVATE_PENDING_ONLY_ASSISTANT",
            status="STREAMING", metadata={
                "runner": {"role": "C3_LANGUAGE", "status": "STREAMING",
                           "actual_model": "/private/model/path", "prompt_tokens": 12,
                           "generated_tokens": 0}
            },
        )
    finally:
        store.close()
    assert snapshot(home) == {
        "availability": "NO_TURNS",
        "selection_scope": "LATEST_COMPLETED_TURN_ALL_SESSIONS",
    }
