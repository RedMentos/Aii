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
from v13.world_jepa_store_authority import verify_committed_transition_page, verify_committed_transitions
from v13.world_jepa_consumer import WorldJEPAStoreConsumer, _receipt_row, _source_disjoint_split
from v13.world_jepa_runtime import (DEFAULT_PERMISSIONS, PERMISSION_KEY, consume_after_commit, receiver_readout, memory_recall)


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 JEPA integration test")
    return store, session


def _add_focal_cycle_context(store, event_id, generation, refs, index, provenance_refs=None, cycle_number=1, persist_items=True):
    """Persist one C4 cycle; only the final producer cycle persists FocalItems."""
    item_ids = [
        f"focal-context-{index:04d}-{cycle_number:02d}-{offset:02d}"
        for offset in range(len(refs))
    ]
    cycle = contracts.packet(
        "FocalCycle",
        "C4_FOCAL",
        event_id,
        generation,
        refs if provenance_refs is None else provenance_refs,
        cycle=cycle_number,
        decision="IGNORE",
        coalition=item_ids,
        signals={},
        budget={"queries_left": 0, "inquisition_steps_left": 0, "cycles": cycle_number, "slots": len(item_ids)},
    )
    store.add_packet("FocalCycle", cycle)
    if not persist_items:
        return
    for item_id, ref in zip(item_ids, refs):
        item = contracts.packet(
            "FocalItem",
            "C4_FOCAL",
            event_id,
            generation,
            [ref],
            item_id=item_id,
            source_kind="MEMORY",
            source_refs=[ref],
            fact_hypothesis_status="HYPOTHESIS",
            state_type="ACTIVE",
            salience=0.5,
            uncertainty=0.1,
            priority=0.5,
            self_generated=False,
            created_wall=0.0,
            origin_event_id=event_id,
            age_ms=0,
            expiry={"turns_left": 1, "policy": "TEST_ONLY"},
            confidence_type="TEST",
            exact_fallback="SOURCE_REF",
            exact_fallback_refs=[ref],
            scale="event",
            covered_range=[{
                "source_id": ref["source_id"],
                "char_start": ref["char_start"],
                "char_end": ref["char_end"],
            }],
            compression_ratio=None,
            boundary_confidence=None,
            boundary_source="NONE",
            children=[],
            parents=[],
        )
        store.add_packet("FocalItem", item)

def _add_transitions(store, session, start, count, status_overrides=None, source_text_factory=None, context_source_refs_factory=None, focal_cycle_context_refs_factory=None, focal_cycle_provenance_refs_factory=None, focal_cycle_history_factory=None):
    status_overrides = status_overrides or {}
    action_ids = []
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        text = (source_text_factory(index) if source_text_factory is not None
                else f"synthetic-user-content-{index:04d}" + ("x" * (index % 29)))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        cycle_history = (
            focal_cycle_history_factory(index) or []
            if focal_cycle_history_factory is not None else []
        )
        if type(cycle_history) is not list:
            raise TypeError("focal_cycle_history_factory must return a list")
        for cycle_number, cycle_refs in enumerate(cycle_history, start=1):
            if cycle_refs:
                _add_focal_cycle_context(
                    store, event_id, generation, cycle_refs, index,
                    cycle_number=cycle_number,
                    persist_items=False,
                )
        focal_refs = (
            focal_cycle_context_refs_factory(index) or []
            if focal_cycle_context_refs_factory is not None else []
        )
        if focal_refs:
            cycle_refs = (
                focal_cycle_provenance_refs_factory(focal_refs)
                if focal_cycle_provenance_refs_factory is not None else focal_refs
            )
            _add_focal_cycle_context(
                store, event_id, generation, focal_refs, index,
                provenance_refs=cycle_refs,
                cycle_number=len(cycle_history) + 1,
                persist_items=True,
            )
        action_index = index % len(actions)
        route = actions[action_index]

        # Selection must be persisted before dispatch: world_model.transitions()
        # admits only the committed selection that existed at action.created.
        context_source_refs = (
            context_source_refs_factory(index) or []
            if context_source_refs_factory is not None else []
        )
        assistant_message_id = store.message(session, event_id, "assistant")
        selection_source_refs = [event["source_ref"]]
        selection = contracts.packet(
            "ActionSelection",
            "C2_CONTROL",
            event_id,
            generation,
            selection_source_refs,
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
        message_status = status if status in {
            "FINAL", "CANCELLED", "DEADLINE", "ERROR", "INTERRUPTED"
        } else "ERROR"
        store.finish_message(
            assistant_message_id, message_status,
            {
                "action_selection": selection["packet_id"],
                "context_source_refs": [event["source_ref"], *context_source_refs],
                "selected_offer_ids": [],
            },
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


def test_source_disjoint_holdout_groups_shared_context_lineage():
    rows = []
    routes = ("simple", "detail", "gist", "both")
    for source_index in range(32):
        source_id = f"context-source-{source_index:02d}"
        source_sha = hashlib.sha256(source_id.encode()).hexdigest()
        for action_index, route in enumerate(routes):
            action_id = f"context-action-{source_index:02d}-{action_index}"
            rows.append({
                "action_id": action_id, "source_id": source_id, "source_sha256": source_sha,
                "fingerprint": hashlib.sha256((action_id + "-fp").encode()).hexdigest(),
                "outcome_sha256": hashlib.sha256((action_id + "-outcome").encode()).hexdigest(),
                "created": float(source_index * 4 + action_index),
                "s": [source_index / 32.0, action_index / 4.0, 0.25, 0.75],
                "a": route, "y": [0.1 + source_index / 100.0, float(action_index % 2), 0.2 + action_index / 10.0],
            })
    source_ids = sorted({row["source_id"] for row in rows})
    def digest_partition(source_id):
        digest = hashlib.sha256(source_id.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % 2
    source_a, source_b = next(
        (left, right) for left in source_ids for right in source_ids
        if left < right and digest_partition(left) != digest_partition(right)
    )
    shared_context = {
        "source_id": "shared-recalled-context",
        "sha256": hashlib.sha256(b"shared recalled context").hexdigest(),
        "char_start": 0, "char_end": 23, "modality": "text",
    }
    for row in rows:
        primary = {
            "source_id": row["source_id"], "sha256": row["source_sha256"],
            "char_start": 0, "char_end": 8, "modality": "text",
        }
        row["source_refs"] = [primary]
        if row["source_id"] in {source_a, source_b}:
            row["source_refs"].append(shared_context)

    split = _source_disjoint_split(rows)
    by_id = {row["action_id"]: row for row in rows}
    train_ids, holdout_ids = set(split["train_action_ids"]), set(split["holdout_action_ids"])
    train_pairs = {
        (ref["source_id"], ref["sha256"])
        for action_id in train_ids for ref in by_id[action_id]["source_refs"]
    }
    holdout_pairs = {
        (ref["source_id"], ref["sha256"])
        for action_id in holdout_ids for ref in by_id[action_id]["source_refs"]
    }
    assert train_pairs.isdisjoint(holdout_pairs)
    fold_a = "train" if any(by_id[action_id]["source_id"] == source_a for action_id in train_ids) else "holdout"
    fold_b = "train" if any(by_id[action_id]["source_id"] == source_b for action_id in train_ids) else "holdout"
    assert fold_a == fold_b
    assert split["manifest"]["source_disjoint"] is True
    assert split["manifest"]["source_sha256_disjoint"] is True


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
            "UPDATED_EXPERIMENTAL_WORLD_JEPA", "UTILITY_GATE_REJECTED"
        }
        first_payload, _ = store.state("v14.world_jepa.store_consumer", None)
        first_active = set(first_payload["active"]["processed_ids"]) if first_payload["active"] else set()
        first_pending = {row["action_id"] for row in first_payload["pending_rows"]}
        first_accounted = first_active | first_pending
        assert set(ids[:64]).issubset(first_accounted)
        assert not (set(ids[64:128]) & first_accounted)
        first_cursor = first_payload["scan_cursor"]
        assert first_cursor == first["scan_cursor"] and first_cursor > 0

        consumer = WorldJEPAStoreConsumer(store, tmp_path / "private-backlog", learning_enabled=True)
        second = consumer.update(limit=64, steps=8, optimizer_permission=True)
        assert second["status"] in {
            "UPDATED_EXPERIMENTAL_WORLD_JEPA", "UTILITY_GATE_REJECTED"
        }
        assert second["scan_cursor"] > first_cursor
        second_payload, _ = store.state("v14.world_jepa.store_consumer", None)
        second_active = set(second_payload["active"]["processed_ids"]) if second_payload["active"] else set()
        second_pending = {row["action_id"] for row in second_payload["pending_rows"]}
        second_accounted = second_active | second_pending
        assert set(ids[:128]).issubset(second_accounted)
        assert not (set(ids[128:192]) & second_accounted)
        assert second_payload["scan_cursor"] == second["scan_cursor"]
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
        _add_transitions(store, session, 0, 64)
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-digest-leak", learning_enabled=True
        )
        result = consumer.update(limit=64, steps=40, optimizer_permission=True)
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


def _set_runtime_permissions(store, *, learning_enabled, optimizer_permission,
                             steps=120, replay_mode="uniform"):
    _, version = store.state(PERMISSION_KEY, dict(DEFAULT_PERMISSIONS))
    store.set_state(PERMISSION_KEY, {
        "learning_enabled": learning_enabled,
        "optimizer_permission": optimizer_permission,
        "steps": steps,
        "replay_mode": replay_mode,
    }, expected=version)


def test_runtime_facade_defaults_off_without_creating_learning_state(tmp_path):
    home = tmp_path / "brain"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 64)
        result = consume_after_commit(store, home, limit=64)
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert result["status"] == "OFF"
        assert result["runtime_adapter_called"] is True
        assert state is None
        assert not (home / "world_jepa").exists()
    finally:
        store.close()


def test_runtime_facade_requires_both_strict_boolean_gates(tmp_path):
    home = tmp_path / "brain-gates"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 64)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=False
        )
        pending = consume_after_commit(store, home, limit=64)
        assert pending["status"] == "PENDING_OPTIMIZER_PERMISSION"
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert state is None

        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=1
        )
        rejected = consume_after_commit(store, home, limit=64)
        assert rejected["status"] == "PENDING_OPTIMIZER_PERMISSION"
        assert rejected["optimizer_permission"] is False
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert state is None
    finally:
        store.close()


def test_runtime_facade_persists_numeric_jepa_and_exposes_b1_b2_memory_shadow(tmp_path):
    home = tmp_path / "brain-runtime"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 256)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        result = consume_after_commit(store, home, limit=256)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        assert result["runtime_adapter_called"] is True
        assert result["decision_authority"] == "NONE"
        assert result["native_body_weights_changed"] is False
        assert result["native_body_consumed"] is False
        metrics = result["metrics"]
        assert metrics["parameter_delta_norm"] > 0
        assert metrics["ema_target_delta_norm"] > 0
        assert metrics["train_holdout_source_sha256_disjoint"] is True
        assert metrics["retention_gate_accepted"] is True

        payload, version = store.state("v14.world_jepa.store_consumer", None)
        assert version >= 1
        assert payload["schema"] == 3
        assert payload["active"]["checkpoint_sha256"] == result["checkpoint_sha256"]
        assert payload["active"]["receiver_heads"].keys() == {
            "B1_DETAIL", "B2_GIST", "SELF_MODEL"
        }

        state = [0.2, 0.1, 0.3, 0.9]
        detail = receiver_readout(store, "B1_DETAIL", state, "simple", home)
        gist = receiver_readout(store, "B2_GIST", state, "simple", home)
        assert detail["status"] == "SHADOW_READOUT_ONLY"
        assert detail["native_body_consumed"] is False
        assert gist["status"] == "SHADOW_READOUT_ONLY"
        assert 0 <= gist["prediction"]["predicted_success_probability"] <= 1
        memory = memory_recall(store, state, "simple", limit=5, home=home)
        assert memory["status"] == "MEMORY_RECALL_SHADOW"
        assert memory["items"]
        assert all("source_sha256" in item and "outcome_sha256" in item
                   for item in memory["items"])

        active_sha = payload["active"]["checkpoint_sha256"]
        _set_runtime_permissions(
            store, learning_enabled=False, optimizer_permission=False
        )
        disabled = consume_after_commit(store, home, limit=64)
        after, _ = store.state("v14.world_jepa.store_consumer", None)
        assert disabled["status"] == "OFF"
        assert after["active"]["checkpoint_sha256"] == active_sha
    finally:
        store.close()


def test_verified_t8_receipt_preserves_complete_source_ref(tmp_path):
    store, session = _make_store(tmp_path / "brain-source-ref")
    try:
        _add_transitions(store, session, 0, 16)
        receipts, rejected = verify_committed_transitions(store, limit=64)
        assert rejected == 0
        assert len(receipts) == 16
        source_ref = receipts[0].source_ref
        assert {"source_id", "sha256", "char_start", "char_end", "modality"} <= set(source_ref)
    finally:
        store.close()


def test_verified_t8_receipt_merges_final_focal_cycle_coalition_refs(tmp_path):
    store, session = _make_store(tmp_path / "brain-focal-cycle-lineage")
    try:
        context_ref = store.source("source admitted to the final C4 coalition", "MEMORY")
        _add_transitions(
            store, session, 0, 1,
            focal_cycle_context_refs_factory=lambda _index: [context_ref],
        )
        receipts, rejected = verify_committed_transitions(store, limit=16)
        assert rejected == 0 and len(receipts) == 1
        assert context_ref in receipts[0].source_refs
        row = _receipt_row(receipts[0])
        assert context_ref in row["source_refs"]
    finally:
        store.close()


def test_verified_t8_rejects_truncated_focal_cycle_coalition_lineage(tmp_path):
    store, session = _make_store(tmp_path / "brain-focal-cycle-truncated")
    try:
        refs = [
            store.source(f"coalition-source-{index:02d}", "MEMORY")
            for index in range(17)
        ]
        _add_transitions(
            store, session, 0, 1,
            focal_cycle_context_refs_factory=lambda _index: refs,
            # Reproduce the current producer's [:16] cap while all 17 FocalItems
            # remain present. The verifier must not certify the incomplete list.
            focal_cycle_provenance_refs_factory=lambda values: values[:16],
        )
        receipts, rejected = verify_committed_transitions(store, limit=16)
        assert receipts == [] and rejected == 1
    finally:
        store.close()


def test_verified_t8_rejects_revoked_focal_cycle_coalition_source(tmp_path):
    store, session = _make_store(tmp_path / "brain-focal-cycle-revoked")
    try:
        context_ref = store.source("revoked source admitted to C4", "MEMORY")
        _add_transitions(
            store, session, 0, 1,
            focal_cycle_context_refs_factory=lambda _index: [context_ref],
        )
        with store.tx() as connection:
            connection.execute(
                "UPDATE sources SET deleted=1 WHERE id=?", (context_ref["source_id"],)
            )
        receipts, rejected = verify_committed_transitions(store, limit=16)
        assert receipts == [] and rejected == 1
    finally:
        store.close()


def _memory_forget_source(store, source_id):
    from v13.memory import Memory
    memory = object.__new__(Memory)
    memory.s = store
    return memory._forget_source(source_id, None)


def test_verified_t8_receipt_persists_all_action_selection_context_refs(tmp_path):
    store, session = _make_store(tmp_path / "brain-context-lineage")
    try:
        context_ref = store.source("a recalled memory source", "MEMORY")
        _add_transitions(
            store, session, 0, 1,
            context_source_refs_factory=lambda _index: [context_ref],
        )
        receipts, rejected = verify_committed_transitions(store, limit=16)
        assert rejected == 0 and len(receipts) == 1
        assert context_ref in receipts[0].source_refs
        row = _receipt_row(receipts[0])
        assert context_ref in row["source_refs"]

        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-context-lineage", learning_enabled=True
        )
        pending = consumer.update(limit=16, steps=8, optimizer_permission=True)
        assert pending["status"] == "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT"
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert len(state["pending_rows"]) == 1
        assert context_ref in state["pending_rows"][0]["source_refs"]
    finally:
        store.close()


def test_verified_t8_rejects_revoked_action_selection_context_source(tmp_path):
    store, session = _make_store(tmp_path / "brain-revoked-context")
    try:
        context_ref = store.source("revoked recalled memory", "MEMORY")
        _add_transitions(
            store, session, 0, 1,
            context_source_refs_factory=lambda _index: [context_ref],
        )
        with store.tx() as connection:
            connection.execute(
                "UPDATE sources SET deleted=1 WHERE id=?", (context_ref["source_id"],)
            )
        receipts, rejected = verify_committed_transitions(store, limit=16)
        assert receipts == [] and rejected == 1
    finally:
        store.close()


def test_memory_forget_discards_untrained_pending_context_source(tmp_path):
    home = tmp_path / "brain-forget-pending-context"
    store, session = _make_store(home)
    try:
        context_ref = store.source("pending recalled memory", "MEMORY")
        _add_transitions(
            store, session, 0, 1,
            context_source_refs_factory=lambda _index: [context_ref],
        )
        consumer = WorldJEPAStoreConsumer(
            store, tmp_path / "private-pending-context", learning_enabled=True
        )
        result = consumer.update(limit=16, steps=8, optimizer_permission=True)
        assert result["status"] == "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT"
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert len(state["pending_rows"]) == 1
        assert context_ref in state["pending_rows"][0]["source_refs"]

        _memory_forget_source(store, context_ref["source_id"])

        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert state["pending_rows"] == []
        source = store.one(
            "SELECT deleted FROM sources WHERE id=?", (context_ref["source_id"],)
        )
        assert source is not None and source["deleted"] == 1
    finally:
        store.close()


def test_memory_forget_rebuilds_after_source_used_by_active_world_jepa(tmp_path):
    home = tmp_path / "brain-forget-active"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 256)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        result = consume_after_commit(store, home, limit=256)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        active = state["active"]
        source_id = active["experience_rows"][0]["source_id"]
        checkpoint_path = home / "world_jepa" / active["checkpoint"]
        before = store.one("SELECT deleted FROM sources WHERE id=?", (source_id,))
        assert before is not None and before["deleted"] == 0

        _memory_forget_source(store, source_id)

        after = store.one("SELECT deleted FROM sources WHERE id=?", (source_id,))
        assert after is not None and after["deleted"] == 1
        current, _ = store.state("v14.world_jepa.store_consumer", None)
        assert current["active"] is None
        assert current["previous"] is None
        assert current["scan_cursor"] == 0
        assert current["pending_rows"] == []
        assert not checkpoint_path.exists()
    finally:
        store.close()

def test_memory_forget_rebuilds_after_source_replay_row_eviction(tmp_path):
    home = tmp_path / "brain-forget-evicted"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 256)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        result = consume_after_commit(store, home, limit=256)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, version = store.state("v14.world_jepa.store_consumer", None)
        active = dict(state["active"])
        target = active["experience_rows"][0]
        source_id = target["source_id"]
        action_id = target["action_id"]
        active["experience_rows"] = [
            row for row in active["experience_rows"] if row["action_id"] != action_id
        ]
        active["train_ids"] = [item for item in active["train_ids"] if item != action_id]
        active["holdout_ids"] = [item for item in active["holdout_ids"] if item != action_id]
        state = dict(state)
        state["active"] = active
        store.set_state("v14.world_jepa.store_consumer", state, expected=version)
        checkpoint_path = home / "world_jepa" / active["checkpoint"]

        _memory_forget_source(store, source_id)

        after = store.one("SELECT deleted FROM sources WHERE id=?", (source_id,))
        assert after is not None and after["deleted"] == 1
        current, _ = store.state("v14.world_jepa.store_consumer", None)
        assert current["active"] is None and current["previous"] is None
        assert current["scan_cursor"] == 0
        assert not checkpoint_path.exists()
    finally:
        store.close()

def test_memory_forget_rebuilds_after_context_source_replay_row_eviction(tmp_path):
    home = tmp_path / "brain-forget-evicted-context"
    store, session = _make_store(home)
    try:
        context_ref = store.source("context used by an old action", "MEMORY")
        ids = _add_transitions(
            store, session, 0, 256,
            focal_cycle_context_refs_factory=lambda index: [context_ref] if index == 0 else [],
        )
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        result = consume_after_commit(store, home, limit=256)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, version = store.state("v14.world_jepa.store_consumer", None)
        active = dict(state["active"])
        target = next(row for row in active["experience_rows"] if row["action_id"] == ids[0])
        assert context_ref in target["source_refs"]
        active["experience_rows"] = [
            row for row in active["experience_rows"] if row["action_id"] != ids[0]
        ]
        active["train_ids"] = [item for item in active["train_ids"] if item != ids[0]]
        active["holdout_ids"] = [item for item in active["holdout_ids"] if item != ids[0]]
        state = dict(state)
        state["active"] = active
        store.set_state("v14.world_jepa.store_consumer", state, expected=version)

        _memory_forget_source(store, context_ref["source_id"])

        after = store.one(
            "SELECT deleted FROM sources WHERE id=?", (context_ref["source_id"],)
        )
        assert after is not None and after["deleted"] == 1
        current, _ = store.state("v14.world_jepa.store_consumer", None)
        assert current["active"] is None and current["previous"] is None
        assert current["scan_cursor"] == 0
    finally:
        store.close()


def test_memory_forget_conservatively_invalidates_nonfinal_focal_cycle_source_after_replay_row_eviction(tmp_path):
    home = tmp_path / "brain-forget-nonfinal-focal-context"
    store, session = _make_store(home)
    try:
        earlier_ref = store.source("source used only in an earlier C4 cycle", "MEMORY")
        final_ref = store.source("source retained in the final C4 coalition", "MEMORY")
        ids = _add_transitions(
            store, session, 0, 256,
            focal_cycle_history_factory=lambda index: [[earlier_ref]] if index == 0 else [],
            focal_cycle_context_refs_factory=lambda index: [final_ref] if index == 0 else [],
        )
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        result = consume_after_commit(store, home, limit=256)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, version = store.state("v14.world_jepa.store_consumer", None)
        active = dict(state["active"])
        target = next(row for row in active["experience_rows"] if row["action_id"] == ids[0])
        assert final_ref in target["source_refs"]
        # Earlier-cycle sources are part of the bounded T8 trajectory receipt,
        # even when they are absent from the final coalition.
        assert earlier_ref in target["source_refs"]
        active["experience_rows"] = [
            row for row in active["experience_rows"] if row["action_id"] != ids[0]
        ]
        active["train_ids"] = [item for item in active["train_ids"] if item != ids[0]]
        active["holdout_ids"] = [item for item in active["holdout_ids"] if item != ids[0]]
        state = dict(state)
        state["active"] = active
        store.set_state("v14.world_jepa.store_consumer", state, expected=version)

        _memory_forget_source(store, earlier_ref["source_id"])

        forgotten = store.one(
            "SELECT deleted FROM sources WHERE id=?", (earlier_ref["source_id"],)
        )
        assert forgotten is not None and forgotten["deleted"] == 1
        current, _ = store.state("v14.world_jepa.store_consumer", None)
        assert current["active"] is None and current["previous"] is None
        assert current["scan_cursor"] == 0
    finally:
        store.close()


def test_verified_t8_rejects_capped_nonfinal_focal_cycle_lineage_without_item_receipts(tmp_path):
    store, session = _make_store(tmp_path / "brain-focal-history-truncated")
    try:
        earlier_refs = [
            store.source(f"earlier-cycle-source-{index:02d}", "MEMORY")
            for index in range(16)
        ]
        final_ref = store.source("final-cycle-source", "MEMORY")
        _add_transitions(
            store, session, 0, 1,
            focal_cycle_history_factory=lambda index: [earlier_refs] if index == 0 else [],
            focal_cycle_context_refs_factory=lambda index: [final_ref] if index == 0 else [],
        )
        receipts, rejected = verify_committed_transitions(store, limit=16)
        assert receipts == [] and rejected == 1
    finally:
        store.close()


def test_memory_forget_uses_all_preaction_cycles_but_ignores_same_timestamp_postaction_cycle_after_row_eviction(tmp_path):
    home = tmp_path / "brain-forget-postaction-focal-context"
    store, session = _make_store(home)
    try:
        earlier_ref = store.source("source in C4 cycle one", "MEMORY")
        final_ref = store.source("source in C4 cycle two", "MEMORY")
        post_ref = store.source("source in a post-action C4 packet", "MEMORY")
        ids = _add_transitions(
            store, session, 0, 256,
            focal_cycle_history_factory=lambda index: [[earlier_ref]] if index == 0 else [],
            focal_cycle_context_refs_factory=lambda index: [final_ref] if index == 0 else [],
        )
        action = store.one(
            "SELECT id,event_id,created FROM actions WHERE id=?", (ids[0],)
        )
        event = store.one(
            "SELECT generation_id FROM events WHERE id=?", (action["event_id"],)
        )
        before = store.one("SELECT COALESCE(MAX(rowid),0) AS last_rowid FROM packets")
        # A post-action C4 packet can share the action's time.time() float.
        # Packet row order, not wall-clock equality, must define the causal cutoff.
        _add_focal_cycle_context(
            store, action["event_id"], event["generation_id"], [post_ref], 999,
            cycle_number=3, persist_items=True,
        )
        with store.tx() as connection:
            connection.execute(
                "UPDATE packets SET created=? WHERE event_id=? AND rowid>? AND kind IN ('FocalCycle','FocalItem')",
                (float(action["created"]), action["event_id"], before["last_rowid"]),
            )

        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        result = consume_after_commit(store, home, limit=256)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, version = store.state("v14.world_jepa.store_consumer", None)
        active = dict(state["active"])
        target = next(row for row in active["experience_rows"] if row["action_id"] == ids[0])
        assert earlier_ref in target["source_refs"]
        assert final_ref in target["source_refs"]
        assert post_ref not in target["source_refs"]
        active["experience_rows"] = [
            row for row in active["experience_rows"] if row["action_id"] != ids[0]
        ]
        active["train_ids"] = [item for item in active["train_ids"] if item != ids[0]]
        active["holdout_ids"] = [item for item in active["holdout_ids"] if item != ids[0]]
        state = dict(state)
        state["active"] = active
        store.set_state("v14.world_jepa.store_consumer", state, expected=version)
        cursor_before = state["scan_cursor"]

        _memory_forget_source(store, post_ref["source_id"])

        forgotten = store.one(
            "SELECT deleted FROM sources WHERE id=?", (post_ref["source_id"],)
        )
        assert forgotten is not None and forgotten["deleted"] == 1
        current, _ = store.state("v14.world_jepa.store_consumer", None)
        assert current["active"] is not None
        assert current["scan_cursor"] == cursor_before
    finally:
        store.close()


def test_memory_forget_discards_untrained_pending_world_jepa_source(tmp_path):
    home = tmp_path / "brain-forget-pending"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 1)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=8
        )
        result = consume_after_commit(store, home, limit=16)
        assert result["status"] == "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT"
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert len(state["pending_rows"]) == 1
        source_id = state["pending_rows"][0]["source_id"]

        _memory_forget_source(store, source_id)

        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert state["pending_rows"] == []
        source = store.one("SELECT deleted FROM sources WHERE id=?", (source_id,))
        assert source is not None and source["deleted"] == 1
    finally:
        store.close()


def test_source_forget_guard_shares_training_file_lock(tmp_path):
    from threading import Event, Thread
    from v13.world_jepa_consumer import source_forget_guard

    home = tmp_path / "brain-forget-lock"
    store, _session = _make_store(home)
    try:
        consumer = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=False
        )
        started = Event()
        acquired = Event()

        def contender():
            started.set()
            with consumer._locked(True):
                acquired.set()

        worker = Thread(target=contender, daemon=True)
        with source_forget_guard(store, "source-not-present"):
            worker.start()
            assert started.wait(1.0)
            assert not acquired.wait(0.1)
        worker.join(2.0)
        assert acquired.is_set()
    finally:
        store.close()



def test_memory_forget_invalidates_source_retained_only_by_rollback_world_jepa(tmp_path):
    home = tmp_path / "brain-forget-rollback"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 256)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        result = consume_after_commit(store, home, limit=256)
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, version = store.state("v14.world_jepa.store_consumer", None)
        retained = state["active"]
        source_id = retained["experience_rows"][0]["source_id"]
        checkpoint_path = home / "world_jepa" / retained["checkpoint"]
        state = dict(state)
        state["active"] = None
        state["previous"] = retained
        state["scan_cursor"] = 0
        store.set_state(
            "v14.world_jepa.store_consumer", state, expected=version
        )

        _memory_forget_source(store, source_id)

        source = store.one("SELECT deleted FROM sources WHERE id=?", (source_id,))
        assert source is not None and source["deleted"] == 1
        current, _ = store.state("v14.world_jepa.store_consumer", None)
        assert current["active"] is None
        assert current["previous"] is None
        assert current["scan_cursor"] == 0
        assert not checkpoint_path.exists()
    finally:
        store.close()

def _hold_world_jepa_file_lock(lock_path, ready, release):
    import fcntl

    with open(lock_path, "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        ready.set()
        release.wait(5.0)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def test_source_forget_guard_waits_for_cross_process_training_lock(tmp_path):
    import multiprocessing
    import time
    from threading import Event, Thread
    from v13.world_jepa_consumer import source_forget_guard

    home = tmp_path / "brain-forget-cross-process"
    store, _session = _make_store(home)
    process = None
    release = None
    try:
        consumer = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=False
        )
        context = multiprocessing.get_context("spawn")
        ready, release = context.Event(), context.Event()
        process = context.Process(
            target=_hold_world_jepa_file_lock,
            args=(str(consumer.lock_path), ready, release),
        )
        process.start()
        assert ready.wait(3.0), "separate process did not acquire WorldJEPA lock"

        timer_fired = Event()

        def release_after_delay():
            time.sleep(0.25)
            release.set()
            timer_fired.set()

        timer = Thread(target=release_after_delay, daemon=True)
        timer.start()
        started = time.monotonic()
        with source_forget_guard(store, "qa-cross-process-lock-source"):
            pass
        elapsed = time.monotonic() - started

        timer.join(2.0)
        process.join(3.0)
        assert timer_fired.is_set()
        assert elapsed >= 0.15, "source forget bypassed the other process's training lock"
        assert process.exitcode == 0
    finally:
        if release is not None:
            release.set()
        if process is not None:
            process.join(3.0)
            if process.is_alive():
                process.terminate()
                process.join(1.0)
        store.close()


def test_memory_forget_restores_clean_previous_checkpoint_and_replays_remaining_t8(tmp_path):
    home = tmp_path / "brain-forget-clean-previous"
    store, session = _make_store(home)
    try:
        first_actions = _add_transitions(store, session, 0, 256)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        first = consume_after_commit(store, home, limit=256)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        second_actions = _add_transitions(store, session, 256, 32)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=24
        )
        second = consume_after_commit(store, home, limit=64)
        assert second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, _ = store.state("v14.world_jepa.store_consumer", None)
        active, previous = state["active"], state["previous"]
        source_row = store.one(
            "SELECT e.source_id FROM actions a JOIN events e ON e.id=a.event_id WHERE a.id=?",
            (second_actions[-1],),
        )
        source_id = source_row["source_id"]
        assert source_id in {row["source_id"] for row in active["experience_rows"]}
        assert source_id not in {row["source_id"] for row in previous["experience_rows"]}
        tainted_path = home / "world_jepa" / active["checkpoint"]
        clean_path = home / "world_jepa" / previous["checkpoint"]
        clean_sha = previous["checkpoint_sha256"]
        clean_cursor = previous["scan_cursor"]

        _memory_forget_source(store, source_id)

        restored, _ = store.state("v14.world_jepa.store_consumer", None)
        assert restored["active"]["checkpoint_sha256"] == clean_sha
        assert restored["previous"] is None
        assert restored["scan_cursor"] == clean_cursor
        assert restored["pending_rows"] == []
        assert not tainted_path.exists() and clean_path.is_file()

        _add_transitions(store, session, 288, 64)
        from v13.world_jepa_consumer import WorldJEPAStoreConsumer
        consumer = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=True
        )
        replay = consumer.update(
            limit=128, steps=24, optimizer_permission=True, replay_mode="uniform"
        )
        assert replay["rejected_receipts"] >= 1
        final, _ = consumer._read_state()
        active_rows = final["active"]["experience_rows"] if final["active"] else []
        assert source_id not in {row["source_id"] for row in active_rows}
        assert source_id not in {row["source_id"] for row in final["pending_rows"]}
        assert final["scan_cursor"] > clean_cursor
        assert second["checkpoint_sha256"] != first["checkpoint_sha256"]
    finally:
        store.close()


def test_memory_forget_invalidates_both_tainted_checkpoints_then_replays(tmp_path):
    home = tmp_path / "brain-forget-both-tainted"
    store, session = _make_store(home)
    try:
        first_actions = _add_transitions(store, session, 0, 256)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=120
        )
        first = consume_after_commit(store, home, limit=256)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        _add_transitions(store, session, 256, 32)
        _set_runtime_permissions(
            store, learning_enabled=True, optimizer_permission=True, steps=24
        )
        second = consume_after_commit(store, home, limit=64)
        assert second["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, _ = store.state("v14.world_jepa.store_consumer", None)
        active, previous = state["active"], state["previous"]
        source_row = store.one(
            "SELECT e.source_id FROM actions a JOIN events e ON e.id=a.event_id WHERE a.id=?",
            (first_actions[0],),
        )
        source_id = source_row["source_id"]
        assert source_id in {row["source_id"] for row in active["experience_rows"]}
        assert source_id in {row["source_id"] for row in previous["experience_rows"]}
        active_path = home / "world_jepa" / active["checkpoint"]
        previous_path = home / "world_jepa" / previous["checkpoint"]

        _memory_forget_source(store, source_id)

        reset, _ = store.state("v14.world_jepa.store_consumer", None)
        assert reset["active"] is None and reset["previous"] is None
        assert reset["scan_cursor"] == 0 and reset["pending_rows"] == []
        assert not active_path.exists() and not previous_path.exists()

        from v13.world_jepa_consumer import WorldJEPAStoreConsumer
        consumer = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=True
        )
        replay = consumer.update(
            limit=512, steps=120, optimizer_permission=True, replay_mode="uniform"
        )
        assert replay["rejected_receipts"] >= 1
        after, _ = consumer._read_state()
        rows = (
            after["active"]["experience_rows"]
            if after["active"] is not None else after["pending_rows"]
        )
        assert source_id not in {row["source_id"] for row in rows}
        assert after["scan_cursor"] > 0
        assert second["checkpoint_sha256"] != first["checkpoint_sha256"]
    finally:
        store.close()
