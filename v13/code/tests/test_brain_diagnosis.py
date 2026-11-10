"""Real SQLite store tests: read-only brain doctor, privacy, and organ labels."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.brain_diagnosis import diagnose
from v13.operator import Operator
from v13.store import Store


@pytest.fixture
def brain(tmp_path):
    for name in ("data", "data/db", "data/blobs"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    db = Store(tmp_path)
    sid = db.new_session()
    runtime = SimpleNamespace(store=db, session=sid)
    yield db, sid, runtime
    db.close()


def test_world_prediction_and_memory_failure_are_distinct_organs(brain):
    db, sid, r = brain
    event = db.event(sid, "Predict the next action")["event_id"]
    db.log("world_jepa_unavailable", event, {
        "stage": "update", "error": "ValueError", "detail": "SENSITIVE_OUTPUT"
    })
    db.log("memory_retrieval_failed", event, {"error": "RuntimeError"})
    db.log("turn_finished", event, {"status": "FINAL"})
    report = json.loads(Operator(r).run(":brain diagnose"))
    assert report["kind"] == "READ_ONLY_DIAGNOSTIC"
    assert report["counts_by_organ"] == {"gedaechtnis": 1, "weltmodell": 1}
    assert {x["technical"] for x in report["findings"]} == {
        "World-JEPA / T8", "Context OS / F1"}
    assert all(x["weight_damage_proven"] is False for x in report["findings"])
    assert "SENSITIVE" not in json.dumps(report)
    assert "next_step" in report["findings"][0]


def test_failed_turn_stage_is_not_mistaken_for_confirmed_root_cause(brain):
    db, sid, r = brain
    event = db.event(sid, "Task")["event_id"]
    mid = db.message(sid, event, "assistant")
    db.finish_message(mid, "ERROR", {
        "error": "RuntimeError", "failure_stage": "native_answer",
        "detail": "PRIVATE CHAT CONTENT"
    })
    report = diagnose(db, sid)
    one = report["findings"][0]
    assert one["organ_id"] == "sprache"
    assert one["confidence"] == "LAST_STAGE_ONLY"
    assert one["signal"] == "TURN_ERROR"
    assert one["error_class"] == "RuntimeError"
    assert "PRIVATE" not in json.dumps(report)


def test_cross_session_telemetry_never_leaks_into_current_diagnosis(brain):
    db, sid, r = brain
    other = db.new_session()
    e = db.event(other, "Different user's material")["event_id"]
    db.log("memory_retrieval_failed", e, {"error": "RuntimeError"})
    assert diagnose(db, sid)["findings"] == []
    assert diagnose(db, other)["counts_by_organ"] == {"gedaechtnis": 1}


def test_unknown_error_is_not_randomly_blamed_on_language(brain):
    db, sid, r = brain
    e = db.event(sid, "Task")["event_id"]
    db.log("vague_unavailable", e, {"error": "ValueError"})
    x = diagnose(db, sid)["findings"][0]
    assert x["organ_id"] == "unknown" and x["technical"] == "UNKNOWN"
    assert x["confidence"] == "UNLOCATED"


def test_diagnostics_do_not_update_training_state_or_permissions(brain):
    db, sid, r = brain
    e = db.event(sid, "Question")["event_id"]
    db.log("body_jepa_failed", e, {"error": "ValueError"})
    before_state = db.rows("SELECT * FROM states")
    before_updates = db.rows("SELECT * FROM updates")
    before_action = db.rows("SELECT * FROM actions")
    report = json.loads(Operator(r).run(":brain diagnose 1"))
    assert report["counts_by_organ"] == {"lernen": 1}
    assert report["no_state_mutation"] and report["no_model_calls"]
    assert db.rows("SELECT * FROM states") == before_state
    assert db.rows("SELECT * FROM updates") == before_updates
    assert db.rows("SELECT * FROM actions") == before_action


def test_bounded_input_and_operator_origin_required(brain):
    _, sid, r = brain
    op = Operator(r)
    for command in (":brain diagnose 0", ":brain diagnose 31",
                    ":brain diagnose 1 2", ":brain diagnose wat"):
        with pytest.raises(ValueError):
            op.run(command)
    with pytest.raises(ValueError, match="lokale Operator"):
        op.run(":brain diagnose", origin="MODEL")


def test_brain_navigation_still_has_legacy_map_and_explanations(brain):
    _, _, r = brain
    op = Operator(r)
    assert json.loads(op.run(":brain map"))["kind"] == "READ_ONLY_NAVIGATION"
    assert json.loads(op.run(":brain explain b1"))["technical"] == "B1_DETAIL"
    assert json.loads(op.run(":brain diagnose"))["findings"] == []


def test_explicit_b1_b2_role_is_reported_for_generic_observer_failure(brain):
    db, sid, runtime = brain
    first = db.event(sid, "B1 detail work")["event_id"]
    second = db.event(sid, "B2 gist work")["event_id"]
    third = db.event(sid, "B1 learning work")["event_id"]
    db.log("offer_rejected", first, {"role": "B1_DETAIL", "error": "ValueError"})
    db.log("offer_rejected", second, {"role": "B2_GIST", "error": "ValueError"})
    db.log("body_jepa_failed", third, {"role": "B1_DETAIL", "error": "ValueError"})
    report = json.loads(Operator(runtime).run(":brain diagnose"))
    by_id = {x["event_id"]: x for x in report["findings"]}
    assert by_id[first]["organ_id"] == "detail"
    assert by_id[second]["organ_id"] == "ueberblick"
    assert by_id[first]["confidence"] == "EXPLICIT_RECORDED_ROLE_NOT_CAUSE"
    assert by_id[second]["affected_model_role"] == "B2_GIST"
    assert by_id[third]["organ_id"] == "lernen"
    assert by_id[third]["affected_model_role"] == "B1_DETAIL"
    assert all(x["weight_damage_proven"] is False for x in by_id.values())
