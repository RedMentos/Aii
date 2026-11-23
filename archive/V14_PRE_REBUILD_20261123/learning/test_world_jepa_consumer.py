"""End-to-end Store integration for the V14 WorldJEPA consumer.

The fixture uses the real V13 SQLite Store, source blobs, EventEnvelope,
CorollaryCopy, ActionSelection and ActionOutcome producers. Its rows are
synthetic test experiences, not live user or Redmi data.
"""
import hashlib
import math

import pytest

from v13 import contracts, world_jepa, world_model
from v13.store import Store
from t8_store_authority import verify_committed_transition_page, verify_committed_transitions
from world_jepa_consumer import WorldJEPAStoreConsumer, _source_disjoint_split


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 JEPA integration test")
    return store, session


def _add_transitions(store, session, start, count, status_overrides=None, source_text_factory=None):
    status_overrides = status_overrides or {}
    action_ids = []
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        text = (source_text_factory(index) if source_text_factory is not None
                else f"synthetic-user-content-{index:04d}" + ("x" * (index % 29)))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        action_index = index % len(actions)
        route = actions[action_index]

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
        # Controlled action-conditioned signal: the committed route changes
        # both observed duration and output size; independent nuisance terms
        # keep the fixture from being a pure action lookup. This is a synthetic
        # positive control, not a claim about real-user outcome distributions.
        duration = 0.15 + action_index * 0.65 + (index % 13) * 0.02
        characters = 9 + action_index * 24 + (index % 23) * 0.75
        status = status_overrides.get(index, "FAILED" if index % 5 == 0 else "FINAL")
        store.finish_action(
            action_id,
            status,
            {"action_duration_s": duration, "characters": characters},
        )
        action_ids.append(action_id)
    return action_ids


def _source_text_for_partition(target, prefix):
    for index in range(10000):
        text = f"{prefix}-{index}"
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        if int.from_bytes(digest[:8], "big") % 2 == target:
            return text
    raise AssertionError("could not construct source digest partition")


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
        first = consumer.update(limit=256, steps=120, optimizer_permission=True)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        metrics = first["metrics"]
        assert metrics["source_verified"] is True
        assert metrics["train_holdout_id_disjoint"] is True
        assert metrics["train_holdout_source_disjoint"] is True
        assert metrics["train_holdout_source_sha256_disjoint"] is True
        assert metrics["train_holdout_content_disjoint"] is True
        assert metrics["train_rows"] >= 8 and metrics["holdout_rows"] >= 8
        assert metrics["parameter_delta_norm"] > 0
        assert metrics["ema_target_delta_norm"] > 0
        assert metrics["holdout_improved"] is True
        assert metrics["old_holdout_retained"] is True
        assert metrics["retention_gate_accepted"] is True
        assert metrics["negative_controls_separated"] is True, {key: metrics[key] for key in ("holdout_loss_after", "shuffled_action_holdout_loss", "zero_action_holdout_loss", "holdout_loss_delta")}
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

        # A second cohort is promoted only if its new holdout and old-retention
        # gates both pass. Rejection is also valid: preserve the prior checkpoint
        # and keep the new cohort pending for a later update with more evidence.
        _add_transitions(store, session, 256, 32)
        second = consumer.update(limit=288, steps=24, optimizer_permission=True)
        if second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
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
        else:
            assert second["status"] == "UTILITY_GATE_REJECTED", second
            assert second["utility_gate_accepted"] is False
            assert not (second["holdout_improved"] and second["negative_controls_separated"]
                        and second["old_holdout_retained"])
            assert second["native_body_weights_changed"] is False
            assert second["fit_steps_after"] > second["fit_steps_before"]
            payload, version = store.state("v14.world_jepa.store_consumer", None)
            assert version >= 3
            assert payload["active"]["checkpoint_sha256"] == first_sha
            assert len(payload["active"]["processed_ids"]) == 256
            assert len(payload["pending_rows"]) == 32
            assert payload["scan_cursor"] == 288
            assert len(list((tmp_path / "private-jepa").glob("jepa-*.npz"))) == 1
            restarted = WorldJEPAStoreConsumer(
                store, tmp_path / "private-jepa", learning_enabled=True
            )
            restored = restarted.restore()
            assert restored["status"] == "RESTORED"
            assert restored["checkpoint_sha256"] == first_sha
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

def test_utility_gate_rejects_old_holdout_regression_even_when_new_holdout_improves(tmp_path, monkeypatch):
    store, session = _make_store(tmp_path / "brain-retention-gate")
    checkpoint_dir = tmp_path / "private-retention-gate"
    try:
        _add_transitions(store, session, 0, 256)
        consumer = WorldJEPAStoreConsumer(
            store, checkpoint_dir, learning_enabled=True, seed=13, ensemble=2
        )
        first = consumer.update(limit=256, steps=120, optimizer_permission=True)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        previous_sha = first["checkpoint_sha256"]

        _add_transitions(store, session, 256, 32)
        # Calls are: new holdout before, old holdout before, new holdout after,
        # shuffled-action control, zero-action control, old holdout after.
        losses = iter((1.0, 0.5, 0.4, 0.8, 0.7, 0.6))
        with monkeypatch.context() as patch:
            patch.setattr(world_jepa.WorldJEPA, "partial_fit", lambda self, *args, **kwargs: None)
            patch.setattr(
                world_jepa.WorldJEPA, "prediction_loss",
                lambda self, *args, **kwargs: next(losses),
            )
            rejected = consumer.update(limit=288, steps=8, optimizer_permission=True)

        assert rejected["status"] == "UTILITY_GATE_REJECTED"
        assert rejected["holdout_improved"] is True
        assert rejected["negative_controls_separated"] is True
        assert rejected["old_holdout_retained"] is False
        assert rejected["retention_gate_accepted"] is False
        assert rejected["utility_gate_accepted"] is False
        assert rejected["old_holdout_loss_before"] == 0.5
        assert rejected["old_holdout_loss_after"] == 0.6

        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert payload["active"]["checkpoint_sha256"] == previous_sha
        assert payload["scan_cursor"] == 288
        assert len(payload["pending_rows"]) == 32
        assert len(list(checkpoint_dir.glob("jepa-*.npz"))) == 1
    finally:
        store.close()


def test_utility_gate_rejects_non_improving_update_and_waits_for_new_data(tmp_path, monkeypatch):
    store, session = _make_store(tmp_path / "brain-utility-gate")
    checkpoint_dir = tmp_path / "private-utility-gate"
    try:
        _add_transitions(store, session, 0, 64)
        consumer = WorldJEPAStoreConsumer(
            store, checkpoint_dir, learning_enabled=True, seed=13, ensemble=2
        )

        with monkeypatch.context() as patch:
            patch.setattr(world_jepa.WorldJEPA, "partial_fit", lambda self, *args, **kwargs: None)
            patch.setattr(world_jepa.WorldJEPA, "prediction_loss", lambda self, *args, **kwargs: 1.0)
            rejected = consumer.update(limit=64, steps=8, optimizer_permission=True)

        assert rejected["status"] == "UTILITY_GATE_REJECTED"
        assert rejected["utility_gate_accepted"] is False
        assert rejected["holdout_improved"] is False
        assert rejected["negative_controls_separated"] is False
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert payload["active"] is None
        assert payload["scan_cursor"] == 64
        assert len(payload["pending_rows"]) == 64
        assert list(checkpoint_dir.glob("jepa-*.npz")) == []

        with monkeypatch.context() as patch:
            def unexpected_fit(*args, **kwargs):
                raise AssertionError("unchanged pending cohort must not be retrained")
            patch.setattr(world_jepa.WorldJEPA, "partial_fit", unexpected_fit)
            waiting = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert waiting["status"] == "WAITING_FOR_MORE_T8_DATA"
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert payload["scan_cursor"] == 64
        assert len(payload["pending_rows"]) == 64

        _add_transitions(store, session, 64, 64)
        fit_calls = {"count": 0}
        with monkeypatch.context() as patch:
            def no_op_fit(self, *args, **kwargs):
                fit_calls["count"] += 1
            patch.setattr(world_jepa.WorldJEPA, "partial_fit", no_op_fit)
            patch.setattr(world_jepa.WorldJEPA, "prediction_loss", lambda self, *args, **kwargs: 1.0)
            retried = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert fit_calls["count"] > 0
        assert retried["status"] == "UTILITY_GATE_REJECTED"
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert payload["scan_cursor"] == 128
        assert len(payload["pending_rows"]) == 128
        assert payload["active"] is None
        assert list(checkpoint_dir.glob("jepa-*.npz")) == []
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
    source_ids = sorted({row["source_id"] for row in rows})
    def old_source_id_partition(source_id):
        digest = hashlib.sha256(source_id.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % 2
    source_a, source_b = next(
        (left, right) for left in source_ids for right in source_ids
        if left < right and old_source_id_partition(left) != old_source_id_partition(right)
    )
    shared_digest = next(row["source_sha256"] for row in rows if row["source_id"] == source_a)
    # Different source IDs, same exact source bytes, and opposite old partitions.
    for row in rows:
        if row["source_id"] == source_b:
            row["source_sha256"] = shared_digest

    split = _source_disjoint_split(rows)
    by_id = {row["action_id"]: row for row in rows}
    train_sources = {by_id[action_id]["source_id"] for action_id in split["train_action_ids"]}
    holdout_sources = {by_id[action_id]["source_id"] for action_id in split["holdout_action_ids"]}
    train_hashes = {by_id[action_id]["source_sha256"] for action_id in split["train_action_ids"]}
    holdout_hashes = {by_id[action_id]["source_sha256"] for action_id in split["holdout_action_ids"]}
    assert train_sources.isdisjoint(holdout_sources)
    assert train_hashes.isdisjoint(holdout_hashes)
    assert split["manifest"]["source_disjoint"] is True
    assert split["manifest"]["source_sha256_disjoint"] is True
    for source_id in source_ids:
        assert sum(source_id in group for group in (train_sources, holdout_sources)) == 1
    fold_a = "train" if source_a in train_sources else "holdout"
    fold_b = "train" if source_b in train_sources else "holdout"
    assert fold_a == fold_b

    corrupt = [dict(row) for row in rows]
    corrupt[-1]["source_sha256"] = hashlib.sha256(b"changed-source").hexdigest()
    with pytest.raises(ValueError, match="source identity changed digest"):
        _source_disjoint_split(corrupt)


def test_censored_outcomes_are_never_learned_or_added_to_processed_ids(tmp_path):
    store, session = _make_store(tmp_path / "brain-censored")
    try:
        ids = _add_transitions(store, session, 0, 256, {
            0: "CANCELLED", 1: "ABORTED", 2: "OUTCOME_UNKNOWN", 3: "INTERRUPTED"
        })
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-censored", learning_enabled=True,
            seed=13, ensemble=2,
        )
        result = consumer.update(limit=256, steps=120, optimizer_permission=True)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        assert result["verified_receipts"] == 252
        assert result["censored_skipped"] == 4
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        processed = set(payload["active"]["processed_ids"])
        assert len(processed) == 252 and not (set(ids[:4]) & processed)
        assert payload["scan_cursor"] == 256
    finally:
        store.close()




def test_non_boolean_optimizer_permission_cannot_advance_censored_cursor(tmp_path):
    store, session = _make_store(tmp_path / "brain-strict-optimizer-gate")
    try:
        _add_transitions(
            store, session, 0, 8,
            status_overrides={index: "CANCELLED" for index in range(8)},
        )
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-strict-optimizer-gate", learning_enabled=True
        )
        with pytest.raises(ValueError, match="optimizer_permission must be bool"):
            consumer.update(limit=64, optimizer_permission=1)
        payload, version = store.state("v14.world_jepa.store_consumer", None)
        assert payload is None and version == 0

        allowed = consumer.update(limit=64, optimizer_permission=True)
        assert allowed["status"] == "NO_NEW_TRANSITIONS"
        assert allowed["scan_cursor"] == 0
        payload, version = store.state("v14.world_jepa.store_consumer", None)
        assert payload is None and version == 0
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
        assert first["status"] in {
            "UPDATED_EXPERIMENTAL_WORLD_JEPA", "UTILITY_GATE_REJECTED",
        }
        if first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
            assert first["metrics"]["has_more"] is True
        else:
            assert first["utility_gate_accepted"] is False
            assert first["native_body_weights_changed"] is False
            assert first["native_body_consumed"] is False
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        first_cursor = payload["scan_cursor"]
        assert first_cursor == cursor
        active_ids = set(payload["active"]["processed_ids"]) if payload["active"] else set()
        pending_ids = {row["action_id"] for row in payload["pending_rows"]}
        assert active_ids.isdisjoint(pending_ids)
        assert active_ids | pending_ids == set(ids[:64])
        assert not ((active_ids | pending_ids) & set(ids[64:128]))
        if first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
            assert active_ids == set(ids[:64]) and not pending_ids
        else:
            assert not active_ids and pending_ids == set(ids[:64])

        page2, rejected2, cursor2, scanned2, censored2, has_more2 = verify_committed_transition_page(
            store, after_seq=first_cursor, limit=64
        )
        assert rejected2 == 0 and scanned2 == 64 and censored2 == 0 and has_more2 is True
        assert [row.action_id for row in page2] == ids[64:128]
        consumer = WorldJEPAStoreConsumer(store, tmp_path / "private-backlog", learning_enabled=True)
        second = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert second["status"] in {
            "UPDATED_EXPERIMENTAL_WORLD_JEPA", "UTILITY_GATE_REJECTED",
        }
        if second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
            assert second["metrics"]["has_more"] is True
        else:
            assert second["utility_gate_accepted"] is False
            assert second["native_body_weights_changed"] is False
            assert second["native_body_consumed"] is False
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        second_cursor = payload["scan_cursor"]
        assert second_cursor == cursor2 and second_cursor > first_cursor
        active_ids = set(payload["active"]["processed_ids"]) if payload["active"] else set()
        pending_ids = {row["action_id"] for row in payload["pending_rows"]}
        assert active_ids.isdisjoint(pending_ids)
        assert active_ids | pending_ids == set(ids[:128])
        assert not ((active_ids | pending_ids) & set(ids[128:192]))
        if second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
            assert active_ids == set(ids[:128]) and not pending_ids
        else:
            assert pending_ids == set(ids[:128]) - active_ids
    finally:
        store.close()




def test_insufficient_source_cohort_persists_pending_page_and_resumes(tmp_path):
    store, session = _make_store(tmp_path / "brain-pending-source")
    try:
        first_ids = _add_transitions(
            store, session, 0, 64,
            source_text_factory=lambda _index: "identical-source-content",
        )
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-pending-source", learning_enabled=True, seed=13, ensemble=2
        )
        first = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert first["status"] == "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT"
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert payload["scan_cursor"] == 64
        assert len(payload["pending_rows"]) == 64
        assert {row["action_id"] for row in payload["pending_rows"]} == set(first_ids)

        second_ids = _add_transitions(store, session, 64, 64)
        resumed = WorldJEPAStoreConsumer(
            store, tmp_path / "private-pending-source", learning_enabled=True, seed=13, ensemble=2
        )
        second = resumed.update(limit=64, steps=24, optimizer_permission=True)
        assert second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        processed = set(payload["active"]["processed_ids"])
        assert set(first_ids + second_ids).issubset(processed)
        assert payload["pending_rows"] == []
        assert payload["scan_cursor"] == 128
        assert payload["active"]["metrics"]["train_holdout_source_sha256_disjoint"] is True
    finally:
        store.close()


def test_pending_cohort_rollback_rewinds_cursor_and_replays_verified_rows(tmp_path):
    store, session = _make_store(tmp_path / "brain-pending-rollback")
    try:
        _add_transitions(store, session, 0, 256)
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-pending-rollback", learning_enabled=True, seed=13, ensemble=2
        )
        initial = consumer.update(limit=256, steps=120, optimizer_permission=True)
        assert initial["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        _add_transitions(store, session, 256, 32)
        second = consumer.update(limit=288, steps=24, optimizer_permission=True)
        assert second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        pending_text = _source_text_for_partition(0, "pending-rollback-source")
        pending_id = _add_transitions(
            store, session, 288, 1, source_text_factory=lambda _index: pending_text
        )[0]
        staged = consumer.update(
            limit=64, steps=8, optimizer_permission=True, replay_mode="none"
        )
        assert staged["status"] == "INSUFFICIENT_NEW_TRAIN_ROWS"
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert payload["scan_cursor"] == 289
        assert len(payload["pending_rows"]) == 1
        assert payload["pending_rows"][0]["action_id"] == pending_id

        rolled_back = consumer.rollback()
        assert rolled_back["status"] == "ROLLED_BACK"
        assert rolled_back["checkpoint_sha256"] == initial["checkpoint_sha256"]
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert payload["scan_cursor"] == 256
        assert payload["pending_rows"] == []
        assert len(payload["active"]["processed_ids"]) == 256

        replayed = consumer.update(
            limit=64, steps=24, optimizer_permission=True, replay_mode="uniform"
        )
        assert replayed["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        payload, _ = store.state("v14.world_jepa.store_consumer", None)
        assert pending_id in set(payload["active"]["processed_ids"])
        assert payload["pending_rows"] == []
        assert payload["scan_cursor"] == 289
    finally:
        store.close()


def test_checkpoint_readback_rejects_source_sha256_leak(tmp_path):
    store, session = _make_store(tmp_path / "brain-digest-leak")
    try:
        # Match the robust action-conditioned cohort used by the main learner
        # integration test. The strict holdout/negative-control utility gate is
        # intentionally unchanged; 64 rows / 40 steps can be borderline across
        # supported NumPy versions (notably 2.5.x on Python 3.14).
        _add_transitions(store, session, 0, 256)
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-digest-leak", learning_enabled=True,
            seed=13, ensemble=2,
        )
        result = consumer.update(limit=256, steps=120, optimizer_permission=True)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        payload, version = store.state("v14.world_jepa.store_consumer", None)
        record = payload["active"]
        by_id = {row["action_id"]: row for row in record["experience_rows"]}
        train_source = by_id[record["train_ids"][0]]["source_id"]
        holdout_source = by_id[record["holdout_ids"][0]]["source_id"]
        train_digest = by_id[record["train_ids"][0]]["source_sha256"]
        assert train_source != holdout_source
        for row in record["experience_rows"]:
            if row["source_id"] == holdout_source:
                row["source_sha256"] = train_digest
        store.set_state("v14.world_jepa.store_consumer", payload, expected=version)
        restarted = WorldJEPAStoreConsumer(
            store, tmp_path / "private-digest-leak", learning_enabled=True
        )
        with pytest.raises(ValueError, match="persisted source digest holdout overlap"):
            restarted.restore()
    finally:
        store.close()


def test_replay_off_ablation_excludes_old_rows_and_uniform_mode_replays_them(tmp_path):
    store, session = _make_store(tmp_path / "brain-replay-ablation")
    try:
        _add_transitions(store, session, 0, 256)
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-replay-ablation", learning_enabled=True, seed=13, ensemble=2
        )
        first = consumer.update(limit=256, steps=120, optimizer_permission=True)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        first_payload, _ = store.state("v14.world_jepa.store_consumer", None)
        first_train = set(first_payload["active"]["train_ids"])
        assert len(first_train) >= 8

        _add_transitions(store, session, 256, 64)
        no_replay = consumer.update(
            limit=64, steps=120, optimizer_permission=True, replay_mode="none"
        )
        assert no_replay["status"] in {"UPDATED_EXPERIMENTAL_WORLD_JEPA", "UTILITY_GATE_REJECTED"}
        no_replay_metrics = no_replay.get("metrics", no_replay)
        assert no_replay_metrics["replay_mode"] == "none"
        assert no_replay_metrics["replay_candidate_rows"] >= 8
        assert no_replay_metrics["replay_rows"] == 0
        assert len(no_replay_metrics["fit_action_ids"]) >= 8
        assert set(no_replay_metrics["fit_action_ids"]) == set(no_replay_metrics["new_train_action_ids"])
        assert not (set(no_replay_metrics["fit_action_ids"]) & first_train)
        assert no_replay_metrics["old_holdout_loss_before"] is not None
        assert math.isfinite(no_replay_metrics["old_holdout_retention_delta"])

        _add_transitions(store, session, 320, 64)
        uniform = consumer.update(
            limit=128, steps=120, optimizer_permission=True, replay_mode="uniform"
        )
        assert uniform["status"] in {"UPDATED_EXPERIMENTAL_WORLD_JEPA", "UTILITY_GATE_REJECTED"}
        uniform_metrics = uniform.get("metrics", uniform)
        assert uniform_metrics["replay_mode"] == "uniform"
        assert uniform_metrics["replay_rows"] >= 8
        assert uniform_metrics["replay_rows"] == uniform_metrics["replay_candidate_rows"]
        assert uniform_metrics["replay_rows"] + uniform_metrics["new_train_rows"] == uniform_metrics["fit_rows"]
        assert first_train <= set(uniform_metrics["fit_action_ids"])
        assert uniform_metrics["old_holdout_loss_before"] is not None
        assert math.isfinite(uniform_metrics["old_holdout_retention_delta"])

        active_payload, _ = store.state("v14.world_jepa.store_consumer", None)
        restarted = WorldJEPAStoreConsumer(
            store, tmp_path / "private-replay-ablation", learning_enabled=True
        )
        assert restarted.restore()["checkpoint_sha256"] == active_payload["active"]["checkpoint_sha256"]
    finally:
        store.close()
