"""End-to-end Store integration for the V14 WorldJEPA consumer.

The fixture uses the real V13 SQLite Store, source blobs, EventEnvelope,
CorollaryCopy, ActionSelection and ActionOutcome producers. Its rows are
synthetic test experiences, not live user or Redmi data.
"""
import math

import pytest

from v13 import contracts, world_model
from v13.store import Store
from t8_store_authority import verify_committed_transitions_page
from world_jepa_consumer import (
    WorldJEPAStoreConsumer,
    _source_disjoint_split,
    _source_partition,
)


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 JEPA integration test")
    return store, session


def _add_transitions(store, session, start, count):
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        text = f"synthetic-user-content-{index:04d}" + ("x" * (index % 29))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        route = actions[index % len(actions)]
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
            forecast={"input_chars": len(text), "resource_state": "NORMAL"},
        )
        duration = 0.15 + (index % 13) * 0.07 + (index % len(actions)) * 0.025
        characters = 9 + (index % 23) * 3 + (index % len(actions)) * 2
        status = "FAILED" if index % 5 == 0 else "FINAL"
        store.finish_action(
            action_id,
            status,
            {"action_duration_s": duration, "characters": characters},
        )


def test_cursor_pages_cover_oldest_backlog_without_starvation(tmp_path):
    store, session = _make_store(tmp_path / "cursor-brain")
    try:
        _add_transitions(store, session, 0, 32)
        first, rejected_first, cursor1 = verify_committed_transitions_page(
            store, limit=12, after=None
        )
        second, rejected_second, cursor2 = verify_committed_transitions_page(
            store, limit=12, after=cursor1
        )
        third, rejected_third, cursor3 = verify_committed_transitions_page(
            store, limit=12, after=cursor2
        )
        ids = [item.action_id for item in first + second + third]
        assert [len(first), len(second), len(third)] == [12, 12, 8]
        assert len(ids) == len(set(ids)) == 32
        assert rejected_first + rejected_second + rejected_third == 0
        assert cursor3["action_id"] == ids[-1]
        assert [item.created for item in first + second + third] == sorted(
            item.created for item in first + second + third
        )
    finally:
        store.close()


def test_source_disjoint_split_groups_same_source_and_rejects_content_leak():
    actions = tuple(world_model.ACTIONS)
    rows = []
    for source_index in range(32):
        source_id = f"source-{source_index:03d}"
        for action_index in range(2):
            index = source_index * 2 + action_index
            rows.append({
                "action_id": f"action-{index:04d}",
                "source_id": source_id,
                "s": [0.1 + index * 0.001, 0.2, 0.3, 0.4],
                "a": actions[(source_index + action_index) % len(actions)],
                "y": [0.01 + index * 0.002, float(index % 2), 0.03 + index * 0.001],
            })
    split = _source_disjoint_split(rows)
    assert set(split["train_source_ids"]).isdisjoint(split["holdout_source_ids"])
    assert set(split["train_action_ids"]).isdisjoint(split["holdout_action_ids"])
    for source_id in {row["source_id"] for row in rows}:
        source_actions = {
            row["action_id"] for row in rows if row["source_id"] == source_id
        }
        assert (
            source_actions.issubset(set(split["train_action_ids"]))
            or source_actions.issubset(set(split["holdout_action_ids"]))
        )

    train_source = next(
        source for source in split["train_source_ids"]
        if _source_partition(source) == "train"
    )
    holdout_source = next(
        source for source in split["holdout_source_ids"]
        if _source_partition(source) == "holdout"
    )
    train_row = next(row for row in rows if row["source_id"] == train_source)
    holdout_row = next(row for row in rows if row["source_id"] == holdout_source)
    holdout_row["s"] = list(train_row["s"])
    holdout_row["a"] = train_row["a"]
    holdout_row["y"] = list(train_row["y"])
    with pytest.raises(ValueError, match="SOURCE_CONTENT_OVERLAP"):
        _source_disjoint_split(rows)


def test_real_store_t8_to_world_jepa_ema_b1_b2_restart_replay_and_rollback(tmp_path):
    store, session = _make_store(tmp_path / "brain")
    try:
        _add_transitions(store, session, 0, 16)
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-jepa", learning_enabled=True, seed=13, ensemble=2
        )
        buffered = consumer.update(limit=16, steps=40, optimizer_permission=True)
        assert buffered["status"] == "BUFFERED_WAITING_FOR_COHORT"
        pending_state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert len(pending_state["pending_rows"]) == 16
        assert pending_state["cursor"] == buffered["cursor"]

        _add_transitions(store, session, 16, 240)
        first = consumer.update(limit=240, steps=40, optimizer_permission=True)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        metrics = first["metrics"]
        assert metrics["source_verified"] is True
        assert metrics["train_holdout_id_disjoint"] is True
        assert metrics["train_holdout_source_disjoint"] is True
        assert metrics["train_holdout_content_disjoint"] is True
        assert metrics["train_rows"] >= 8 and metrics["holdout_rows"] >= 8
        assert metrics["parameter_delta_norm"] > 0
        assert metrics["ema_target_delta_norm"] > 0
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

        _add_transitions(store, session, 256, 32)
        second = consumer.update(limit=32, steps=24, optimizer_permission=True)
        assert second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        assert second["metrics"]["replay_rows"] >= 8
        assert second["metrics"]["fit_steps_after"] > second["metrics"]["fit_steps_before"]
        assert second["metrics"]["old_holdout_loss_before"] is not None
        assert second["metrics"]["old_holdout_loss_after"] is not None
        assert second["checkpoint_sha256"] != first_sha
        assert len(list((tmp_path / "private-jepa").glob("jepa-*.npz"))) == 2

        restarted = WorldJEPAStoreConsumer(store, tmp_path / "private-jepa", learning_enabled=True)
        restored = restarted.restore()
        assert restored["status"] == "RESTORED"
        assert restored["checkpoint_sha256"] == second["checkpoint_sha256"]

        rolled_back = restarted.rollback()
        assert rolled_back["status"] == "ROLLED_BACK"
        assert rolled_back["checkpoint_sha256"] == first_sha
        assert rolled_back["cursor_restored"] is True
        restored_first = restarted.restore()
        assert restored_first["checkpoint_sha256"] == first_sha
        assert len(list((tmp_path / "private-jepa").glob("jepa-*.npz"))) == 2

        payload, version = store.state("v14.world_jepa.store_consumer", None)
        assert version >= 4
        assert payload["active"]["checkpoint_sha256"] == first_sha
        assert len(payload["active"]["processed_ids"]) == 256
        assert payload["cursor"] == first["cursor"]
        assert payload["pending_rows"] == []
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
