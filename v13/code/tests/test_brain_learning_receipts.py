"""Real SQLite evidence of learning stages, without fake native-weight claims."""
import json
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.store import Store


@pytest.fixture
def brain(tmp_path):
    for path in ("data", "data/db", "data/blobs"):
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    st = Store(tmp_path)
    session = st.new_session()
    r = SimpleNamespace(store=st, session=session, home=tmp_path)
    yield r
    st.close()


def _put_experience(r, session=None):
    sid = session or r.session
    evt = r.store.event(sid, "PRIVATE CHAT INSTRUCTION")
    event, source = evt["event_id"], evt["source_ref"]["source_id"]
    with r.store.tx() as db:
        db.execute("INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?)", (
            "mem1" + event, event, source, sid, "EPISODE",
            "SESSION", "SECRET MEMORY", "PRIVATE CHAT TEXT", 1, 0,
        ))
        db.execute("INSERT INTO replay VALUES (?,?,?,?,?,?)", (
            "replay1" + event, event, "T8", 1.0, "COMMITTED", 0,
        ))
        db.execute("INSERT INTO feedback VALUES (?,?,?,?,?,?,?)", (
            "fb1" + event, event, source, "CORRECTION", "SECRET FEEDBACK",
            "ALLOW", 0,
        ))
    return source


def test_memory_feedback_replay_are_records_not_pinned_model_learning(brain):
    r = brain
    _put_experience(r)
    report = json.loads(Operator(r).run(":brain learning"))
    assert report["kind"] == "READ_ONLY_LEARNING_RECEIPTS"
    assert report["experience"] == {
        "active_source_bound_memory_records": 1,
        "recorded_replay_items": 1,
        "recorded_feedback_items": 1,
        "counts_do_not_prove_learning": True,
    }
    assert report["active_model_updates"]["active_binding_count"] == 0
    assert report["active_model_updates"]["model_weight_learning_proven_here"] is False
    assert report["native_redmi_learning_proven"] is False
    assert report["full_agi_proven"] is False
    assert report["model_calls"] == 0
    assert "PRIVATE" not in json.dumps(report)
    assert "SECRET" not in json.dumps(report)


def test_revoked_and_other_session_sources_are_not_counted(brain):
    r = brain
    source = _put_experience(r)
    other = r.store.new_session()
    _put_experience(r, other)
    assert json.loads(Operator(r).run(":brain learning"))["experience"]["recorded_replay_items"] == 1
    with r.store.tx() as db:
        db.execute("UPDATE sources SET deleted=1 WHERE id=?", (source,))
    report = json.loads(Operator(r).run(":brain learning"))
    assert all(report["experience"][x] == 0 for x in (
        "active_source_bound_memory_records",
        "recorded_replay_items", "recorded_feedback_items",
    ))
    r.session = other
    report_other = json.loads(Operator(r).run(":brain learning"))
    assert report_other["experience"]["active_source_bound_memory_records"] == 1
    assert report_other["experience"]["recorded_replay_items"] == 1


def test_trainer_update_record_does_not_claim_actual_weight_improvement(brain):
    r = brain
    generation = r.store.generation_id
    with r.store.tx() as db:
        db.execute("INSERT INTO updates VALUES (?,?,?,?,?,?,?)", (
            "train-proposal", generation, "PENDING_APPROVAL", None, None,
            json.dumps({"role": "B1_DETAIL", "objective": "synthetic"}), 1,
        ))
        db.execute("INSERT INTO updates VALUES (?,?,?,?,?,?,?)", (
            "nominal-commit", generation, "COMMITTED", None, None,
            json.dumps({"role": "C3_LANGUAGE", "retention_pass": True}), 2,
        ))
        db.execute("INSERT INTO updates VALUES (?,?,?,?,?,?,?)", (
            "malformed-record", generation, "HIDDEN_UNKNOWN", None, None,
            json.dumps({"role": ["B2_GIST"]}), 3,
        ))
    report = json.loads(Operator(r).run(":brain learning"))["active_model_updates"]
    assert report["update_status_counts_last_256"]["PENDING_APPROVAL"] == 1
    assert report["update_status_counts_last_256"]["COMMITTED"] == 1
    assert report["unknown_update_status_count"] == 1
    assert report["roles"]["B1_DETAIL"]["candidate_update_records"] == 1
    assert report["roles"]["C3_LANGUAGE"]["committed_update_records"] == 1
    assert report["roles"]["B2_GIST"]["candidate_update_records"] == 0
    assert report["model_weight_learning_proven_here"] is False
    assert report["retention_proven_here"] is False
    assert report["active_binding_count"] == 0


def test_local_predictor_counters_not_presented_as_efficacy_proof(brain):
    r = brain
    r._online_world = SimpleNamespace(model=SimpleNamespace(seen=17))
    r._world_jepa_online = SimpleNamespace(_fit_steps=5)
    report = json.loads(Operator(r).run(":brain learning"))
    assert report["predictors"]["local_numeric_predictor"][
        "reported_observations_in_memory"] == 17
    assert report["predictors"]["world_jepa"]["reported_fit_steps_in_memory"] == 5
    assert report["predictors"]["local_numeric_predictor"][
        "independent_weight_delta_verified"] is False
    assert report["predictors"]["world_jepa"][
        "checkpoint_and_retention_verified_here"] is False
    r._online_world.model.seen = -10
    r._world_jepa_online._fit_steps = "madeup"
    report = json.loads(Operator(r).run(":brain learning"))
    assert report["predictors"]["local_numeric_predictor"][
        "reported_observations_in_memory"] is None
    assert report["predictors"]["world_jepa"][
        "reported_fit_steps_in_memory"] is None


def test_read_only_output_does_not_mutate_training_or_human_approval(brain):
    r = brain
    _put_experience(r)
    before = {
        table: r.store.rows(f"SELECT * FROM {table}")
        for table in ("updates", "states", "memories", "feedback", "requests")
    }
    report = json.loads(Operator(r).run(":brain learning"))
    assert report["state_mutation"] is False
    assert report["active_model_updates"]["operator_approval_inferred_from_pending"] is False
    for table in before:
        assert r.store.rows(f"SELECT * FROM {table}") == before[table]
    with pytest.raises(ValueError, match="lokale Operator"):
        Operator(r).run(":brain learning", origin="MODEL")
