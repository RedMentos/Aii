"""End-to-end Store integration for the V14 WorldJEPA consumer.

The fixture uses the real V13 SQLite Store, source blobs, EventEnvelope,
CorollaryCopy, ActionSelection and ActionOutcome producers. Its rows are
synthetic test experiences, not live user or Redmi data.
"""
import hashlib
import math

import pytest

from v13 import contracts, world_model
from v13.store import Store
from t8_store_authority import verify_committed_transition_page, verify_committed_transitions
from world_jepa_consumer import WorldJEPAStoreConsumer, _source_disjoint_split


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 JEPA integration test")
    return store, session


def _add_transitions(store, session, start, count, status_overrides=None):
    status_overrides = status_overrides or {}
    action_ids = []
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        text = f"synthetic-user-content-{index:04d}" + ("x" * (index % 29))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        route = actions[index % len(actions)]

        # Selection must be persisted before dispatch: world_model.transitions()
        # admits only the committed selection that existed at action.created.
        selection = contracts.packet(
            "ActionSelection",
            "C2_CONTROL",
            event_id,
            generation,
            [event["source_ref"]],
            selected={
                "action_id": "TEXT_REPORT",
                "action_type": "TEXT_REPORT",
                "score": 0.0,
                "permission_class": "local_text_only",
                "focal_support": 0.0,
            },
            candidates=[],
            suppressed=[],
            permission_class="local_text_only",
            route_hint=route,
            stage="COMMIT",
        )
        store.add_packet("ActionSelection", selection)

        action_id = store.start_action(
            event_id,
            generation,
            forecast={
                "input_chars": len(text),
                "resource_state": "NORMAL",
            },
        )
        duration = 0.15 + (index % 13) * 0.07 + (index % len(actions)) * 0.025
        characters = 9 + (index % 23) * 3 + (index % len(actions)) * 2
        status = status_overrides.get(index, "FAILED" if index % 5 == 0 else "FINAL")
        store.finish_action(
            action_id,
            status,
            {"action_duration_s": duration, "characters": characters},
        )
        action_ids.append(action_id)
    return action_ids


def test_real_store_t8_to_world_jepa_ema_b1_b2_restart_replay_and_rollback(tmp_path):
    store, session = _make_store(tmp_path / "brain")
    try:
        _add_transitions(store, session, 0, 256)
        raw_rows = world_model.transitions(store, limit=256)
        verified, rejected = verify_committed_transitions(store, limit=256)
        assert len(verified) >= 16, {
            "raw_rows": len(raw_rows),
            "rejected": rejected,
            "actions": store.rows("SELECT id,status,expected,outcome,created FROM actions ORDER BY created DESC LIMIT 2"),
            "selections": store.rows("SELECT event_id,generation_id,created,payload FROM packets WHERE kind='ActionSelection' ORDER BY created DESC LIMIT 2"),
            "raw_head": raw_rows[:1],
        }
        assert rejected == 0

        consumer = WorldJEPAStoreConsumer(
            store,
            tmp_path / "private-jepa",
            learning_enabled=True,
            seed=13,
            ensemble=2,
        )
        first = consumer.update(limit=256, steps=40, optimizer_permission=True)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        metrics = first["metrics"]
        assert metrics["source_verified"] is True
        assert metrics["train_holdout_id_disjoint"] is True
        assert metrics["train_holdout_source_disjoint"] is True
        assert metrics["train_holdout_content_disjoint"] is True
        assert metrics["train_rows"] >= 8 and metrics["holdout_rows"] >= 8
        assert metrics["parameter_delta_norm"] > 0
        assert metrics["ema_target_delta_norm"] > 0
        assert metrics["holdout_improved"] is True
        assert metrics["negative_controls_separated"] is True
        assert metrics["holdout_loss_delta"] < 0
        assert metrics["optimizer_moments_persisted"] is False
        assert math.isfinite(metrics["holdout_loss_before"])
        assert math.isfinite(metrics["holdout_loss_after"])
        assert math.isfinite(metrics["shuffled_action_holdout_loss"])
        assert math.isfinite(metrics["zero_action_holdout_loss"])
        assert first["native_body_weights_changed"] is False
        assert first["native_body_consumed"] is False
        assert first["runtime_wired"] is False
        first_sha = first["checkpoint_sha256"]

        detail = consumer.readout("B1_DETAIL", [0.2, 0.1, 0.3, 0.9], "simple")
        gist = consumer.readout("B2_GIST", [0.2, 0.1, 0.3, 0.9], "simple")
        assert detail["status"] == "SHADOW_READOUT_ONLY"
        assert math.isfinite(detail["prediction"]["predicted_action_duration_s"])
        assert math.isfinite(detail["prediction"]["predicted_output_characters"])
        assert 0 <= gist["prediction"]["predicted_success_probability"] <= 1
        self_model = consumer.readout("SELF_MODEL", [0.2, 0.1, 0.3, 0.9], "simple")
        assert self_model["role"] == "SELF_MODEL"
        assert 0 <= self_model["prediction"]["predicted_success_probability"] <= 1
        memory = consumer.recall([0.2, 0.1, 0.3, 0.9], "simple", limit=5)
        assert memory["status"] == "MEMORY_RECALL_SHADOW"
        assert 1 <= len(memory["items"]) <= 5
        assert all("source_id" in item and "source_sha256" in item and "outcome_sha256" in item for item in memory["items"])

        # A second batch must replay the old train split, commit a new immutable
        # checkpoint and retain the prior generation for exact rollback.
        _add_transitions(store, session, 256, 32)
        second = consumer.update(limit=288, steps=24, optimizer_permission=True)
        assert second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        assert second["metrics"]["replay_rows"] >= 8
        assert second["metrics"]["fit_steps_after"] > second["metrics"]["fit_steps_before"]
        assert second["metrics"]["old_holdout_loss_before"] is not None
        assert second["metrics"]["old_holdout_loss_after"] is not None
        assert math.isfinite(second["metrics"]["old_holdout_retention_delta"])
        assert second["checkpoint_sha256"] != first_sha
        assert len(list((tmp_path / "private-jepa").glob("jepa-*.npz"))) == 2

        restarted = WorldJEPAStoreConsumer(
            store, tmp_path / "private-jepa", learning_enabled=True
        )
        restored = restarted.restore()
        assert restored["status"] == "RESTORED"
        assert restored["checkpoint_sha256"] == second["checkpoint_sha256"]

        rolled_back = restarted.rollback()
        assert rolled_back["status"] == "ROLLED_BACK"
        assert rolled_back["checkpoint_sha256"] == first_sha
        restored_first = restarted.restore()
        assert restored_first["checkpoint_sha256"] == first_sha
        assert len(list((tmp_path / "private-jepa").glob("jepa-*.npz"))) == 2

        payload, version = store.state("v14.world_jepa.store_consumer", None)
        assert version >= 3
        assert payload["active"]["checkpoint_sha256"] == first_sha
        assert len(payload["active"]["processed_ids"]) == 256
        assert payload["scan_cursor"] == 256
        assert "synthetic-user-content-" not in repr(payload)
    finally:
        store.close()


def test_world_jepa_consumer_requires_both_local_learning_gates(tmp_path):
    store, session = _make_store(tmp_path / "brain-gates")
    try:
        _add_transitions(store, session, 0, 64)
        disabled = WorldJEPAStoreConsumer(
            store, tmp_path / "disabled", learning_enabled=False
        )
        result = disabled.update(limit=64, steps=8, optimizer_permission=True)
        assert result["status"] == "LEARNING_DISABLED"
        assert store.state("v14.world_jepa.store_consumer", None)[0] is None

        enabled = WorldJEPAStoreConsumer(
            store, tmp_path / "enabled", learning_enabled=True
        )
        pending = enabled.update(limit=64, steps=8, optimizer_permission=False)
        assert pending["status"] == "PENDING_OPTIMIZER_PERMISSION"
        assert store.state("v14.world_jepa.store_consumer", None)[0] is None
    finally:
        store.close()

def test_source_disjoint_holdout_groups_all_actions_from_one_source():
    rows = []
    routes = ("simple", "detail", "gist", "both")
    for source_index in range(32):
        source_id = f"source-{source_index:02d}"
        source_sha = hashlib.sha256(source_id.encode()).hexdigest()
        for action_index, route in enumerate(routes):
            action_id = f"action-{source_index:02d}-{action_index}"
            rows.append({
                "action_id": action_id, "source_id": source_id, "source_sha256": source_sha,
                "fingerprint": hashlib.sha256((action_id + "-fp").encode()).hexdigest(),
                "outcome_sha256": hashlib.sha256((action_id + "-outcome").encode()).hexdigest(),
                "created": float(source_index * 4 + action_index),
                "s": [source_index / 32.0, action_index / 4.0, 0.25, 0.75],
                "a": route, "y": [0.1 + source_index / 100.0, float(action_index % 2), 0.2 + action_index / 10.0],
            })
    split = _source_disjoint_split(rows)
    by_id = {row["action_id"]: row for row in rows}
    train_sources = {by_id[action_id]["source_id"] for action_id in split["train_action_ids"]}
    holdout_sources = {by_id[action_id]["source_id"] for action_id in split["holdout_action_ids"]}
    assert train_sources.isdisjoint(holdout_sources)
    assert split["manifest"]["source_disjoint"] is True
    for source_id in {row["source_id"] for row in rows}:
        assert sum(source_id in group for group in (train_sources, holdout_sources)) == 1
    corrupt = [dict(row) for row in rows]
    corrupt[-1]["source_sha256"] = hashlib.sha256(b"changed-source").hexdigest()
    with pytest.raises(ValueError, match="source identity changed digest"):
        _source_disjoint_split(corrupt)


def test_censored_outcomes_are_never_learned_or_added_to_processed_ids(tmp_path):
    store, session = _make_store(tmp_path / "brain-censored")
    try:
        ids = _add_transitions(store, session, 0, 64, {
            0: "CANCELLED", 1: "ABORTED", 2: "OUTCOME_UNKNOWN", 3: "INTERRUPTED"
        })
        consumer = WorldJEPAStoreConsumer(store, tmp_path / "private-censored", learning_enabled=True)
        result = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        assert result["verified_receipts"] == 60
        assert result["censored_skipped"] == 4
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        processed = set(payload["active"]["processed_ids"])
        assert len(processed) == 60 and not (set(ids[:4]) & processed)
        assert payload["scan_cursor"] == 64
    finally:
        store.close()


def test_oldest_first_pages_do_not_starve_older_t8_backlog(tmp_path):
    store, session = _make_store(tmp_path / "brain-backlog")
    try:
        ids = _add_transitions(store, session, 0, 2050)
        page, rejected, cursor, scanned, censored, has_more = verify_committed_transition_page(
            store, after_seq=0, limit=64
        )
        assert rejected == 0 and scanned == 64 and censored == 0 and has_more is True
        assert page[0].action_id == ids[0] and page[-1].action_id == ids[63] and cursor > 0
        consumer = WorldJEPAStoreConsumer(store, tmp_path / "private-backlog", learning_enabled=True)
        first = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA" and first["metrics"]["has_more"] is True
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        processed = set(payload["active"]["processed_ids"])
        assert set(ids[:64]).issubset(processed) and not (set(ids[64:128]) & processed)
        first_cursor = first["scan_cursor"]
        consumer = WorldJEPAStoreConsumer(store, tmp_path / "private-backlog", learning_enabled=True)
        second = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA" and second["scan_cursor"] > first_cursor
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        processed = set(payload["active"]["processed_ids"])
        assert set(ids[:128]).issubset(processed) and not (set(ids[128:192]) & processed)
    finally:
        store.close()
