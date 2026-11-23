"""Persistent temporal WorldJEPA: real Store/T8 producer, synthetic test experiences.

No native GGUF, Android or Redmi behavior is claimed by these fixtures.
"""
from types import SimpleNamespace
import importlib.util
import hashlib
from pathlib import Path
import json
import threading

import numpy as np
import pytest

from v13 import bodyview, contracts, world_jepa, world_model
from v13.memory import Memory
from v13.sleep import SleepRuntime
from v13.store import Store
from v13.world_jepa_runtime import PERMISSION_KEY
from v13.world_jepa_store_authority import verify_committed_temporal_page
from v13.world_jepa_temporal import (
    STATE_KEY,
    TemporalWorldJEPAStoreConsumer,
    _record_references_source,
    _split_windows,
    build_temporal_windows,
)


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    return store


def _add_session(store, label, session_index, *, status_overrides=None, event_count=4,
                 context_source_refs_factory=None):
    status_overrides = status_overrides or {}
    session = store.new_session(label)
    event_ids = []
    for offset in range(event_count):
        text = f"{label}-session-{session_index:03d}-event-{offset:02d}-" + ("x" * ((session_index + offset) % 31))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        action_index = (session_index + offset) % len(world_model.ACTIONS)
        route = world_model.ACTIONS[action_index]
        selection_source_refs = [event["source_ref"]]
        if context_source_refs_factory is not None:
            selection_source_refs.extend(context_source_refs_factory(session_index, offset) or [])
        selection = contracts.packet(
            "ActionSelection", "C2_CONTROL", event_id, generation,
            selection_source_refs,
            selected={
                "action_id": "TEXT_REPORT", "action_type": "TEXT_REPORT",
                "score": 0.0, "permission_class": "local_text_only",
                "focal_support": 0.0,
            },
            candidates=[], suppressed=[], permission_class="local_text_only",
            route_hint=route, stage="COMMIT",
        )
        store.add_packet("ActionSelection", selection)
        action_id = store.start_action(
            event_id, generation,
            forecast={"input_chars": len(text), "resource_state": "NORMAL"},
        )
        status = status_overrides.get(offset, "FINAL" if action_index < 2 else "FAILED")
        store.finish_action(
            action_id, status,
            {
                "action_duration_s": 0.2 + action_index * 0.7 + (session_index % 9) * 0.03,
                "characters": 12 + action_index * 28 + (session_index % 11) * 1.5,
            },
        )
        event_ids.append(event_id)
    return session, event_ids

def _permissions(store, *, replay_mode="uniform", steps=80):
    store.set_state(PERMISSION_KEY, {
        "learning_enabled": True,
        "optimizer_permission": True,
        "steps": steps,
        "replay_mode": replay_mode,
    })


def _make_dataset(store, label, count=32, *, start_index=0):
    sessions = []
    events = []
    for offset in range(count):
        index = start_index + offset
        overrides = {}
        if index % 8 == 0:
            overrides[1] = "CANCELLED"
        if index == 1:
            overrides[2] = "OUTCOME_UNKNOWN"
        if index % 7 == 0:
            overrides[3] = "INTERRUPTED"
        session, event_ids = _add_session(
            store, label, index, status_overrides=overrides
        )
        sessions.append(session)
        events.extend(event_ids)
    return sessions, events


def _sleep(store, home):
    sleep = object.__new__(SleepRuntime)
    sleep.r = SimpleNamespace(
        store=store, home=home, cancel_event=threading.Event(),
        guard=SimpleNamespace(update=lambda _snapshot: "NORMAL"),
        resources=lambda: {},
    )
    sleep.resource_state = lambda: "NORMAL"
    return sleep


def test_temporal_page_and_dense_windows_keep_known_omissions_and_reject_unknown_gaps(tmp_path):
    home = tmp_path / "temporal-window-store"
    store = _make_store(home)
    try:
        _make_dataset(store, "window-cohort", 16)
        receipts, rejected, cursor, scanned, censored, has_more = verify_committed_temporal_page(
            store, after_seq=0, limit=64
        )
        assert rejected == 0
        assert scanned == 64
        assert censored >= 1
        assert has_more is False
        rows = []
        from v13.world_jepa_temporal import _receipt_row
        for receipt in receipts:
            if receipt.status != "OUTCOME_UNKNOWN":
                rows.append(_receipt_row(store, receipt))
        windows = build_temporal_windows(store, rows)
        assert len(windows) >= 24
        assert {len(window["X"]) for window in windows} == {10}
        assert {len(window["A"]) for window in windows} == {4}
        assert any(window["censored"] for window in windows)
        # Every window is a contiguous, generation-consistent sequence.
        for window in windows:
            assert len(window["action_ids"]) in (3, 4)
            assert len(set(window["source_sha256s"])) == len(window["source_sha256s"])
            assert window["generation_id"]
    finally:
        store.close()


def test_temporal_action_selection_context_lineage_is_persisted_and_source_disjoint(tmp_path):
    store = _make_store(tmp_path / "temporal-context-lineage")
    try:
        shared = store.source("shared recalled context source", "MEMORY")
        session_ids = []
        for index in range(4):
            session, _events = _add_session(
                store, "context-lineage", index, event_count=8,
                context_source_refs_factory=(
                    (lambda _session, _offset, ref=shared: [ref])
                    if index in (0, 1) else None
                ),
            )
            session_ids.append(session)
        receipts, rejected, _cursor, _scanned, _censored, has_more = verify_committed_temporal_page(
            store, after_seq=0, limit=64
        )
        assert rejected == 0 and has_more is False
        from v13.world_jepa_temporal import _receipt_row, _split_windows
        rows = [_receipt_row(store, receipt) for receipt in receipts
                if receipt.status != "OUTCOME_UNKNOWN"]
        shared_rows = [row for row in rows if row["session_id"] in set(session_ids[:2])]
        assert shared_rows
        assert all(
            any(ref["source_id"] == shared["source_id"] for ref in row["source_refs"])
            for row in shared_rows
        )
        windows = build_temporal_windows(store, rows)
        train, holdout, split = _split_windows(windows)
        train_sessions = {window["session_id"] for window in train}
        holdout_sessions = {window["session_id"] for window in holdout}
        assert (session_ids[0] in train_sessions) == (session_ids[1] in train_sessions)
        assert (session_ids[0] in holdout_sessions) == (session_ids[1] in holdout_sessions)
        train_lineage = {
            source for window in train for source in window["lineage_source_ids"]
        }
        holdout_lineage = {
            source for window in holdout for source in window["lineage_source_ids"]
        }
        assert not train_lineage & holdout_lineage
        assert split["source_disjoint"] is True
        assert shared["source_id"] in train_lineage or shared["source_id"] in holdout_lineage
    finally:
        store.close()


def test_temporal_source_forget_detects_evicted_action_selection_context_and_censored_outcomes(tmp_path):
    store = _make_store(tmp_path / "temporal-context-forget")
    try:
        from v13.world_jepa_temporal import _receipt_row, _record_references_source
        context = store.source("context source to forget", "MEMORY")
        _session, event_ids = _add_session(
            store, "context-forget", 0, event_count=4, status_overrides={0: "INTERRUPTED"},
            context_source_refs_factory=lambda _session, _offset: [context],
        )
        receipts, rejected, _cursor, _scanned, _censored, _more = verify_committed_temporal_page(
            store, after_seq=0, limit=16
        )
        assert rejected == 0
        target_receipt = next(receipt for receipt in receipts if receipt.event_id == event_ids[0])
        target = store.one(
            "SELECT a.id AS action_id,a.rowid AS scan_seq FROM actions a WHERE a.event_id=?",
            (event_ids[0],),
        )
        assert target is not None and target_receipt.status == "INTERRUPTED"
        _receipt_row(store, target_receipt)
        evicted_record = {
            "scan_cursor": target["scan_seq"],
            "experience_rows": [],
            "retention_holdouts": [],
            "learning_intents": {},
        }
        assert _record_references_source(
            store, evicted_record, context["source_id"]
        ) is True
        assert _record_references_source(
            store, evicted_record, context["source_id"], {target["action_id"]}
        ) is False
        assert _record_references_source(
            store, dict(evicted_record, scan_cursor=target["scan_seq"] - 1),
            context["source_id"],
        ) is False
        assert _record_references_source(
            store, evicted_record, "unrelated-context-source"
        ) is False
        with store.tx() as connection:
            connection.execute("UPDATE sources SET deleted=1 WHERE id=?", (context["source_id"],))
        try:
            _receipt_row(store, target_receipt)
        except ValueError:
            pass
        else:
            raise AssertionError("revoked ActionSelection context source was accepted")
    finally:
        store.close()


def test_single_session_waits_for_disjoint_temporal_holdout_without_error(tmp_path):
    home = tmp_path / "single-session-temporal-wait"
    store = _make_store(home)
    try:
        _add_session(store, "single-session", 0, event_count=32)
        _permissions(store, steps=40)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        result = learner.update(
            limit=64, max_pages=4, steps=40,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert result["status"] == "WAITING_FOR_MORE_T8_DATA", result
        assert result["reason"] == "NEED_MORE_SOURCE_DISJOINT_SESSIONS"
        state, _ = store.state(STATE_KEY, None)
        assert state["active"] is None
        assert len(state["pending_rows"]) == 32
        assert not list((home / "world_jepa_temporal").glob("jepa-*.npz"))
    finally:
        store.close()


def test_pending_single_session_rows_resume_after_restart_with_second_session(tmp_path):
    home = tmp_path / "temporal-pending-restart"
    store = _make_store(home)
    try:
        _add_session(store, "first-cohort", 0, event_count=32)
        _permissions(store, steps=40)
        first_learner = TemporalWorldJEPAStoreConsumer(store, seed=41, ensemble=2)
        first = first_learner.update(
            limit=64, max_pages=4, steps=40,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert first["status"] == "WAITING_FOR_MORE_T8_DATA", first
        assert first["reason"] == "NEED_MORE_SOURCE_DISJOINT_SESSIONS"
        before, _ = store.state(STATE_KEY, None)
        assert len(before["pending_rows"]) == 32
        first_cursor = before["scan_cursor"]
        store.close()

        # Reopen the same durable Store; the second independent session makes
        # a genuine session-disjoint train/holdout split possible.
        store = Store(home)
        _add_session(store, "second-cohort", 1, event_count=32)
        _permissions(store, steps=40)
        resumed = TemporalWorldJEPAStoreConsumer(store, seed=41, ensemble=2)
        second = resumed.update(
            limit=64, max_pages=4, steps=40,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert second["status"] in {
            "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA",
            "RETENTION_GATE_REJECTED",
            "UTILITY_GATE_REJECTED",
        }, second
        assert second["verified_receipts"] == 32
        after, _ = store.state(STATE_KEY, None)
        assert after["scan_cursor"] > first_cursor
        active_ids = {
            row["action_id"] for row in (after.get("active") or {}).get("experience_rows", [])
        }
        pending_ids = {row["action_id"] for row in after["pending_rows"]}
        all_ids = active_ids | pending_ids
        assert len(all_ids) == 64
        assert len(active_ids) + len(pending_ids) == len(all_ids)
    finally:
        store.close()


def test_temporal_world_jepa_updates_ema_checkpoint_and_b1_b2_shadow_receivers(tmp_path):
    home = tmp_path / "temporal-learning-store"
    store = _make_store(home)
    try:
        sessions, event_ids = _make_dataset(store, "A", 32)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        first = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert first["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", first
        metrics = first["metrics"]
        assert metrics["source_disjoint"] is True
        assert metrics["train_windows"] >= 8 and metrics["holdout_windows"] >= 8
        assert metrics["parameter_delta_norm"] > 0
        assert metrics["ema_target_delta_norm"] > 0
        assert metrics["optimizer_steps"] >= 80
        assert metrics["censored_observed"] >= 1
        assert metrics["unknown_skipped"] >= 1
        assert metrics["holdout_mse_after"] <= metrics["holdout_mse_before"] * 1.05 + 1e-9
        assert metrics["holdout_mse_after"] < metrics["shuffled_target_mse"]
        assert metrics["holdout_mse_after"] < metrics["shuffled_action_mse"]
        assert first["optimizer_state_persisted"] is True
        assert first["native_body_consumed"] is False
        assert first["native_body_weights_changed"] is False
        assert first["decision_authority"] == "NONE"

        state, _ = store.state(STATE_KEY, None)
        assert state["active"]["checkpoint_sha256"] == first["checkpoint_sha256"]
        assert len(state["active"]["experience_rows"]) >= 100
        assert len(state["active"]["retention_holdouts"]) == 1
        assert state["active"]["fit_steps"] >= 80

        # The WorldJEPA producer now issues typed source-bound LearningIntents
        # to the B1/B2 float receiver adapters and records exact parameter diffs.
        from v13.world_jepa_learning_intent import (
            validate_learning_intent, validate_weight_delta_receipt,
        )
        active_record = state["active"]
        intents = active_record["learning_intents"]
        receipts = active_record["weight_delta_receipts"]
        assert set(intents) == {"B1_DETAIL", "B2_GIST"}
        assert set(receipts) == {"B1_DETAIL", "B2_GIST"}
        for role in ("B1_DETAIL", "B2_GIST"):
            intent, receipt = intents[role], receipts[role]
            assert validate_learning_intent(intent) is True
            assert validate_weight_delta_receipt(receipt) is True
            assert intent["producer_organ"] == "WORLD_JEPA_TEMPORAL"
            assert intent["target_organ"] == role
            assert intent["target_model_revision"] == "v14-temporal-receiver-adapter-v1"
            assert intent["target_parameter_scope"] == role + ".temporal_receiver_head.weights+bias"
            assert intent["objective_revision"] == "v14-temporal-receiver-outcome-mse-v1"
            assert intent["optimizer_revision"] == "RIDGE_CLOSED_FORM_V1"
            assert intent["source_ids"] and intent["t8_transition_ids"]
            assert set(intent["train_cohort_ids"]).isdisjoint(intent["validation_cohort_ids"])
            assert set(intent["source_sha256s"]).isdisjoint(intent["validation_source_sha256s"])
            assert intent["consent_snapshot"]["learning_enabled"] is True
            assert intent["consent_snapshot"]["optimizer_permission"] is True
            assert intent["eligibility_trace"]["path_id"] == "world_predictor"
            assert intent["neuromodulation"]["status"] == "READY"
            assert intent["gradient_budget"]["method"] == "CLOSED_FORM_RIDGE"
            assert intent["approval_id"] is None
            assert intent["age_capability"] == "SHADOW_ONLY_NO_NATIVE_BODY_RIGHT"
            assert intent["authority"] == "NONE"
            assert intent["native_body_weights_changed"] is False
            assert intent["target_adapter_parameters_changed"] is True
            assert intent["status"] == "SHADOW_ADAPTER_UPDATED"
            assert intent["checkpoint_sha256"] == first["checkpoint_sha256"]
            assert receipt["intent_id"] == intent["intent_id"]
            assert receipt["receipt_id"] == intent["weight_delta_receipt_id"]
            assert receipt["source_provenance_sha256"] == intent["provenance_sha256"]
            assert receipt["checkpoint_sha256"] == first["checkpoint_sha256"]
            assert receipt["old_parameter_sha256"] is None
            assert receipt["new_parameter_sha256"] == intent["new_parameter_sha256"]
            assert receipt["parameter_delta_norm"] > 0
            assert receipt["holdout_mse_after"] == pytest.approx(intent["holdout_mse_after"])
            assert receipt["world_retention_pass"] is True
            assert receipt["target_adapter_retention"] == "NOT_MEASURED"
            assert receipt["gradient_measured"] is False
            assert receipt["native_body_weights_changed"] is False
            assert receipt["target_adapter_parameters_changed"] is True

        bad_intent = dict(intents["B1_DETAIL"])
        bad_intent["target_organ"] = "C3_LANGUAGE"
        with pytest.raises(ValueError, match="learning intent contract"):
            validate_learning_intent(bad_intent)
        bad_cohort = dict(intents["B1_DETAIL"])
        bad_cohort["validation_cohort_ids"] = list(bad_cohort["train_cohort_ids"])
        with pytest.raises(ValueError, match="learning intent cohort leakage"):
            validate_learning_intent(bad_cohort)

        # Restart must reload the exact same persisted checkpoint and optimizer state.
        restarted = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        active, _ = store.state(STATE_KEY, None)
        assert active["active"]["checkpoint_sha256"] == first["checkpoint_sha256"]
        action = max(active["active"]["action_support"], key=active["active"]["action_support"].get)
        from v13.world_jepa_consumer import receiver_utility_gate
        for role, history_length in (("B1_DETAIL", 2), ("B2_GIST", 3)):
            gate = receiver_utility_gate(active["active"]["receiver_metrics"], role)
            assert gate["accepted"] is (gate["reason"] == "HELDOUT_BEATS_MEAN_AND_NEGATIVE_CONTROLS")
            readout = restarted.receiver_readout(
                role, sessions[0], action, history_length=history_length,
            )
            expected_status = "SHADOW_READOUT_ONLY" if gate["accepted"] else "RECEIVER_UTILITY_REJECTED"
            assert readout["status"] == expected_status
            assert readout["receiver_utility"] == gate
            assert readout["decision_authority"] == "NONE"
            assert readout["native_body_consumed"] is False
            assert readout["native_body_weights_changed"] is False
            if readout["status"] == "SHADOW_READOUT_ONLY":
                assert np.isfinite(readout["uncertainty"])
                assert readout["support_samples"] >= 8
                assert readout["checkpoint_sha256"] == first["checkpoint_sha256"]

        # Forget invalidates a source-bearing active checkpoint before tombstoning.
        source_row = active["active"]["experience_rows"][0]
        checkpoint_path = learner.home / active["active"]["checkpoint"]
        from v13.memory import Memory
        Memory(store, {})._forget_source(source_row["source_id"], source_row["event_id"])
        forgotten, _ = store.state(STATE_KEY, None)
        assert forgotten["active"] is None
        assert forgotten["previous"] is None
        assert forgotten["scan_cursor"] == 0
        assert forgotten["pending_rows"] == []
        assert not checkpoint_path.exists()
        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (source_row["source_id"],)
        )["deleted"] == 1
        import json
        forget_log = store.one(
            "SELECT metrics FROM telemetry WHERE kind=? ORDER BY id DESC LIMIT 1",
            ("forget",),
        )
        assert forget_log is not None
        forget_metrics = json.loads(forget_log["metrics"])
        assert forget_metrics["component"] == "world_predictor"
        assert forget_metrics["count"] == 1
        assert forget_metrics["source_id"] == source_row["source_id"]
        assert forget_metrics["status"] == "PASS"
    finally:
        store.close()


def test_temporal_source_forget_checks_scanned_history_beyond_bounded_replay_and_ignores_pending(tmp_path):
    """An evicted-but-scanned T8 source still taints parameters; pending-only does not."""
    store = _make_store(tmp_path / "temporal-forget-scanned-history")
    try:
        _sessions, _events = _make_dataset(store, "forget-scanned-history", 8)
        target = store.one(
            """SELECT a.id AS action_id,a.rowid AS scan_seq,e.source_id
               FROM actions a JOIN events e ON e.id=a.event_id
               WHERE a.outcome IS NOT NULL AND a.expected LIKE ?
                 AND a.status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED')
               ORDER BY a.rowid ASC LIMIT 1""",
            ('%"forecast"%',),
        )
        assert target is not None
        # Deliberately model the bounded checkpoint after this row has aged out
        # of experience_rows, holdouts and LearningIntent provenance.
        evicted_record = {
            "scan_cursor": target["scan_seq"],
            "experience_rows": [],
            "retention_holdouts": [],
            "learning_intents": {},
        }
        assert _record_references_source(
            store, evicted_record, target["source_id"]
        ) is True
        # A scanned-but-not-trained pending row is removed without invalidating
        # an otherwise clean checkpoint.
        assert _record_references_source(
            store, evicted_record, target["source_id"], {target["action_id"]}
        ) is False
        assert _record_references_source(
            store, evicted_record, "unrelated-source"
        ) is False
        before_row = dict(evicted_record, scan_cursor=target["scan_seq"] - 1)
        assert _record_references_source(
            store, before_row, target["source_id"]
        ) is False
    finally:
        store.close()


def test_temporal_source_forget_promotes_clean_previous_and_replays_after_restart(tmp_path):
    home = tmp_path / "temporal-forget-clean-previous"
    store = _make_store(home)
    try:
        # Use the full 256-action scan budget so the source/session-disjoint
        # receiver holdout is stable across randomly generated Store identities.
        _make_dataset(store, "forget-fallback-A", 64)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        first = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert first["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", first
        first_state, _ = store.state(STATE_KEY, None)
        first_sha = first_state["active"]["checkpoint_sha256"]
        first_cursor = first_state["scan_cursor"]
        first_path = learner.home / first_state["active"]["checkpoint"]

        _sessions, second_events = _make_dataset(
            store, "forget-fallback-B", 64, start_index=64,
        )
        second = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert second["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", json.dumps(second, sort_keys=True)
        second_state, _ = store.state(STATE_KEY, None)
        second_record = second_state["active"]
        second_path = learner.home / second_record["checkpoint"]
        second_event_set = set(second_events)
        source_row = next(
            row for row in second_record["experience_rows"]
            if row["event_id"] in second_event_set
        )
        source_id = source_row["source_id"]
        assert not any(
            row["source_id"] == source_id
            for row in second_state["previous"]["experience_rows"]
        )

        from v13.memory import Memory
        Memory(store, {})._forget_source(source_id, source_row["event_id"])

        restored, _ = store.state(STATE_KEY, None)
        assert restored["active"]["checkpoint_sha256"] == first_sha
        assert restored["previous"] is None
        assert restored["scan_cursor"] == first_cursor
        assert restored["pending_rows"]
        assert all(row["source_id"] != source_id for row in restored["pending_rows"])
        assert not second_path.exists()
        assert first_path.is_file()
        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (source_id,)
        )["deleted"] == 1
        import json
        forget_log = store.one(
            "SELECT metrics FROM telemetry WHERE kind=? ORDER BY id DESC LIMIT 1",
            ("forget",),
        )
        forget_metrics = json.loads(forget_log["metrics"])
        assert forget_metrics["count"] == 1
        assert forget_metrics["retained_cases_saved"] > 0
        assert forget_metrics["source_id"] == source_id

        # The promoted checkpoint and retry queue survive a real SQLite reopen.
        store.close()
        store = Store(home)
        restarted = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        retry = restarted.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert retry["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", retry
        replayed, _ = store.state(STATE_KEY, None)
        assert all(row["source_id"] != source_id
                   for row in replayed["active"]["experience_rows"])
        assert replayed["active"]["checkpoint_sha256"] == retry["checkpoint_sha256"]
        assert replayed["active"]["metrics"]["source_disjoint"] is True
    finally:
        store.close()


def test_temporal_source_forget_invalidates_both_checkpoints_then_rebuilds_from_remaining_t8(tmp_path):
    home = tmp_path / "temporal-forget-full-replay"
    store = _make_store(home)
    try:
        _sessions, first_events = _make_dataset(store, "forget-full-A", 32)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        first = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert first["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", first
        _make_dataset(store, "forget-full-B", 32, start_index=32)
        second = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert second["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", second
        before, _ = store.state(STATE_KEY, None)
        active_path = learner.home / before["active"]["checkpoint"]
        previous_path = learner.home / before["previous"]["checkpoint"]
        first_event_set = set(first_events)
        source_row = next(
            row for row in before["active"]["experience_rows"]
            if row["event_id"] in first_event_set
        )
        source_id = source_row["source_id"]
        assert any(row["source_id"] == source_id
                   for row in before["previous"]["experience_rows"])

        from v13.memory import Memory
        Memory(store, {})._forget_source(source_id, source_row["event_id"])

        invalidated, _ = store.state(STATE_KEY, None)
        assert invalidated["active"] is None
        assert invalidated["previous"] is None
        assert invalidated["scan_cursor"] == 0
        assert invalidated["pending_rows"] == []
        assert not active_path.exists()
        assert not previous_path.exists()
        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (source_id,)
        )["deleted"] == 1
        import json
        forget_log = store.one(
            "SELECT metrics FROM telemetry WHERE kind=? ORDER BY id DESC LIMIT 1",
            ("forget",),
        )
        forget_metrics = json.loads(forget_log["metrics"])
        assert forget_metrics["count"] == 2
        assert forget_metrics["retained_cases_saved"] == 0
        assert forget_metrics["source_id"] == source_id

        # Restart must reconstruct only from the surviving, source-verified T8 ledger.
        store.close()
        store = Store(home)
        restarted = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        rebuilt = restarted.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert rebuilt["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", rebuilt
        after, _ = store.state(STATE_KEY, None)
        assert all(row["source_id"] != source_id
                   for row in after["active"]["experience_rows"])
        assert after["active"]["checkpoint_sha256"] == rebuilt["checkpoint_sha256"]
        assert after["active"]["metrics"]["source_disjoint"] is True
    finally:
        store.close()


def test_temporal_source_forget_unrelated_source_preserves_active_checkpoint(tmp_path):
    home = tmp_path / "temporal-forget-negative-control"
    store = _make_store(home)
    try:
        _make_dataset(store, "forget-negative-control", 32)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        trained = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert trained["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", trained
        before, _ = store.state(STATE_KEY, None)
        active_sha = before["active"]["checkpoint_sha256"]
        active_path = learner.home / before["active"]["checkpoint"]

        unrelated_session = store.new_session("unrelated source-forget negative control")
        unrelated_event = store.event(unrelated_session, "not present in temporal T8")
        unrelated_source = unrelated_event["source_ref"]["source_id"]
        from v13.memory import Memory
        Memory(store, {})._forget_source(unrelated_source, unrelated_event["event_id"])

        after, _ = store.state(STATE_KEY, None)
        assert after["active"]["checkpoint_sha256"] == active_sha
        assert after["previous"] is None
        assert active_path.is_file()
        assert all(row["source_id"] != unrelated_source
                   for row in after["active"]["experience_rows"])
        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (unrelated_source,)
        )["deleted"] == 1
    finally:
        store.close()


def test_sleep_runtime_invokes_temporal_consumer_but_default_permissions_stay_off(tmp_path):
    home = tmp_path / "temporal-sleep-runtime"
    store = _make_store(home)
    try:
        _sessions, event_ids = _make_dataset(store, "sleep", 4)
        sleep = _sleep(store, home)
        result = sleep._run_world_jepa(event_ids[-1])
        assert result["status"] == "POSTCOMMIT_PROCESSED"
        assert result["learning"]["status"] == "OFF"
        assert result["temporal"]["status"] == "OFF"
        assert result["planner"]["status"] == "NO_CHECKPOINT"
        assert store.state(PERMISSION_KEY, None)[0] is None
        assert store.state(STATE_KEY, None)[0] is None
        assert result["native_body_weights_changed"] is False
        assert result["decision_authority"] == "NONE"
    finally:
        store.close()


def test_sleep_runtime_commits_source_verified_base_and_temporal_learning_after_t8_outcome(tmp_path):
    home = tmp_path / "sleep-enabled-temporal-postcommit"
    store = _make_store(home)
    try:
        _sessions, event_ids = _make_dataset(store, "sleep-enabled", 64)
        _permissions(store, steps=80)
        sleep = _sleep(store, home)

        # This is the real SleepRuntime postcommit entry point: it discovers the
        # committed ActionOutcome in Store and invokes both persistent learners.
        result = sleep._run_world_jepa(event_ids[-1], limit=64)
        assert result["status"] in {"POSTCOMMIT_PROCESSED", "PARTIAL"}, result
        assert result["action_status"] in {"FINAL", "FAILED", "ERROR", "DEADLINE", "REJECTED", "CANCELLED", "ABORTED", "INTERRUPTED"}
        assert result["learning"]["status"] not in {"ERROR", "CANCELLED"}, result["learning"]
        temporal = result["temporal"]
        assert temporal["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", temporal
        assert temporal["checkpoint_committed"] is True
        assert temporal["metrics"]["source_disjoint"] is True
        assert temporal["metrics"]["parameter_delta_norm"] > 0
        assert temporal["metrics"]["ema_target_delta_norm"] > 0
        assert temporal["metrics"]["optimizer_steps"] >= 40
        assert temporal["metrics"]["steps_this_update"] == 40  # runtime adapter cap
        assert temporal["optimizer_state_persisted"] is True
        assert temporal["native_body_weights_changed"] is False
        assert temporal["decision_authority"] == "NONE"

        persisted, _ = store.state(STATE_KEY, None)
        assert persisted["active"]["checkpoint_sha256"] == temporal["checkpoint_sha256"]
        assert len(persisted["active"]["experience_rows"]) >= 100
        assert store.one(
            "SELECT id FROM actions WHERE event_id=? AND outcome IS NOT NULL",
            (event_ids[-1],),
        ) is not None
    finally:
        store.close()


def test_sleep_runtime_keeps_unknown_outcomes_out_of_the_learning_loop(tmp_path):
    home = tmp_path / "sleep-unknown-outcome"
    store = _make_store(home)
    try:
        _sessions, event_ids = _make_dataset(store, "sleep-unknown", 32)
        _permissions(store, steps=80)
        sleep = _sleep(store, home)

        # Session 1 / event 2 is deliberately OUTCOME_UNKNOWN. It must remain
        # a gap, unlike known CANCELLED/ABORTED/INTERRUPTED omissions.
        result = sleep._run_world_jepa(event_ids[6], limit=64)
        assert result["status"] == "NO_COMMITTED_OUTCOME", result
        assert result["dispatch"] is False
        assert store.state(STATE_KEY, None)[0] is None
    finally:
        store.close()


def test_temporal_adam_scale_changes_numeric_delta_without_corrupting_moments():
    full = world_jepa.Adam({"w": np.asarray([1.0])}, 0.1)
    quarter = world_jepa.Adam({"w": np.asarray([1.0])}, 0.1)
    grads = {"w": np.asarray([0.5])}

    full.step(grads)
    quarter.step(grads, scale=0.25)

    full_delta = 1.0 - full.p["w"][0]
    quarter_delta = 1.0 - quarter.p["w"][0]
    assert quarter_delta == pytest.approx(full_delta * 0.25)
    assert np.array_equal(full.m["w"], quarter.m["w"])
    assert np.array_equal(full.v["w"], quarter.v["w"])
    with pytest.raises(ValueError):
        quarter.step(grads, scale=1.01)


def test_temporal_active_neuromodulation_scales_real_optimizer_updates(tmp_path, monkeypatch):
    home = tmp_path / "temporal-neuromod-active"
    store = _make_store(home)
    try:
        _make_dataset(store, "neuromod-active", 32)
        _permissions(store, steps=40)
        from v13.neuromod import Neuromod

        neuromod = Neuromod(store)
        neuromod.set_local_mode("ACTIVE", authority="EXPLICIT_HUMAN")
        scales = []
        original_step = world_jepa.Adam.step

        def capture_step(self, grads, scale=1.0):
            scales.append(scale)
            return original_step(self, grads, scale=scale)

        monkeypatch.setattr(world_jepa.Adam, "step", capture_step)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=41, ensemble=2)
        result = learner.update(
            limit=64, max_pages=4, steps=40,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert result["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", result
        credit = result["metrics"]["neuromodulation"]
        assert credit["mode"] == "ACTIVE"
        assert credit["applied"] is True
        assert credit["mean_prediction_rmse"] > 0
        assert credit["eligibility"] > 0
        assert credit["modulator"] > 0
        assert credit["trace_packets_written"] > 0
        assert credit["modulator_packets_written"] > 0
        assert 0 < credit["learning_rate_scale"] <= 1
        assert scales
        assert all(value == pytest.approx(credit["learning_rate_scale"]) for value in scales)
        assert result["metrics"]["parameter_delta_norm"] > 0
        assert result["metrics"]["ema_target_delta_norm"] > 0
        assert neuromod.local_mode() == "ACTIVE"
    finally:
        store.close()


def test_temporal_active_neuromodulation_veto_prevents_weight_update(tmp_path, monkeypatch):
    home = tmp_path / "temporal-neuromod-veto"
    store = _make_store(home)
    try:
        _make_dataset(store, "neuromod-veto", 32)
        _permissions(store, steps=40)
        from v13.neuromod import Neuromod

        event_id = store.one(
            "SELECT id FROM events ORDER BY created DESC,id DESC LIMIT 1"
        )["id"]
        neuromod = Neuromod(store)
        neuromod.signal(
            event_id, path="world_predictor",
            source_class="real_deterministic_outcome",
            safety_veto=True, world_prediction_error=1.0,
        )
        neuromod.set_local_mode("ACTIVE", authority="EXPLICIT_HUMAN")
        steps = []
        original_step = world_jepa.Adam.step

        def capture_step(self, grads, scale=1.0):
            steps.append(scale)
            return original_step(self, grads, scale=scale)

        monkeypatch.setattr(world_jepa.Adam, "step", capture_step)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=43, ensemble=2)
        result = learner.update(
            limit=64, max_pages=4, steps=40,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert result["status"] == "MODULATOR_VETO", result
        assert result["checkpoint_committed"] is False
        assert result["neuromodulation"]["mode"] == "ACTIVE"
        assert steps == []
        assert store.state(STATE_KEY, None)[0] is None
    finally:
        store.close()


def test_temporal_rollback_restores_previous_checkpoint_and_retries_pending_rows_after_restart(tmp_path):
    home = tmp_path / "temporal-rollback-retry-store"
    store = _make_store(home)
    try:
        _make_dataset(store, "rollback-A", 32)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        first = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert first["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", first
        first_state, _ = store.state(STATE_KEY, None)
        first_record = first_state["active"]
        first_sha = first_record["checkpoint_sha256"]
        first_intent_ids = {
            role: intent["intent_id"]
            for role, intent in first_record["learning_intents"].items()
        }
        first_receipt_ids = {
            role: receipt["receipt_id"]
            for role, receipt in first_record["weight_delta_receipts"].items()
        }

        _make_dataset(store, "rollback-B", 32)
        second = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert second["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", second
        second_state, _ = store.state(STATE_KEY, None)
        second_record = second_state["active"]
        assert second_record["checkpoint_sha256"] != first_sha
        assert second_record["fit_steps"] > first_record["fit_steps"]

        rollback = learner.rollback()
        assert rollback["status"] == "ROLLED_BACK", rollback
        restored, _ = store.state(STATE_KEY, None)
        assert restored["active"]["checkpoint_sha256"] == first_sha
        assert restored["active"]["fit_steps"] == first_record["fit_steps"]
        assert {
            role: intent["intent_id"]
            for role, intent in restored["active"]["learning_intents"].items()
        } == first_intent_ids
        assert {
            role: receipt["receipt_id"]
            for role, receipt in restored["active"]["weight_delta_receipts"].items()
        } == first_receipt_ids
        assert restored["previous"] is None
        assert len(restored["pending_rows"]) >= 100
        assert not (learner.home / second_record["checkpoint"]).exists()

        # Close and reopen SQLite itself, not merely the learner object. The
        # source-bound intents and delta receipts must survive the real DB restart.
        store.close()
        store = Store(home)
        reopened, _ = store.state(STATE_KEY, None)
        assert reopened["active"]["checkpoint_sha256"] == first_sha
        assert {
            role: intent["intent_id"]
            for role, intent in reopened["active"]["learning_intents"].items()
        } == first_intent_ids
        assert {
            role: receipt["receipt_id"]
            for role, receipt in reopened["active"]["weight_delta_receipts"].items()
        } == first_receipt_ids
        assert len(reopened["pending_rows"]) >= 100

        # Restart must preserve the restored checkpoint and make rolled-back
        # source-verified rows explicitly retryable without requiring a new T8 event.
        restarted = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        retry = restarted.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert retry["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", retry
        assert retry["verified_receipts"] == 0
        assert retry["pending_retried"] >= 100
        assert retry["optimizer_state_persisted"] is True
        assert retry["metrics"]["parameter_delta_norm"] > 0
        assert retry["metrics"]["ema_target_delta_norm"] > 0
        assert retry["metrics"]["optimizer_steps"] > first_record["fit_steps"]
        active, _ = store.state(STATE_KEY, None)
        assert active["active"]["checkpoint_sha256"] == retry["checkpoint_sha256"]
        assert active["previous"]["checkpoint_sha256"] == first_sha
        assert active["pending_rows"] == []
        assert active["previous"]["learning_intents"] == first_record["learning_intents"]
        assert active["previous"]["weight_delta_receipts"] == first_record["weight_delta_receipts"]
        assert active["active"]["learning_intents"] != first_record["learning_intents"]
        assert active["active"]["weight_delta_receipts"] != first_record["weight_delta_receipts"]
    finally:
        store.close()




def test_temporal_receiver_matrix_batches_bodyview_contract_with_single_readout_parity(tmp_path, monkeypatch):
    home = tmp_path / "temporal-bodyview-matrix-store"
    store = _make_store(home)
    try:
        sessions, _ = _make_dataset(store, "matrix", 32)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        first = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert first["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", first

        # Foreground reads must not synchronously load a cold checkpoint.
        # A slow/cold model load belongs to the idle warm-up path only.
        learner._ephemeral_model = None
        learner._ephemeral_checkpoint_sha = None
        original_load = learner._load_model

        def unexpected_foreground_load(_record):
            raise AssertionError("warm-only receiver attempted a cold checkpoint load")

        learner._load_model = unexpected_foreground_load
        try:
            cold_matrix = learner.receiver_matrix(
                sessions[0], world_model.ACTIONS, history_length=2,
                nonblocking=True, warm_only=True,
            )
            assert cold_matrix["status"] == "MODEL_NOT_WARM"
            cold_recall = learner.episodic_recall(
                sessions[0], history_length=2, limit=4,
                nonblocking=True, warm_only=True,
            )
            assert cold_recall["status"] == "MODEL_NOT_WARM"
        finally:
            learner._load_model = original_load

        warm = learner.warm_active_checkpoint()
        assert warm["status"] == "WARMED"

        # The warm recall path has a cooperative budget: after a slow query or
        # candidate batch it must stop before embedding the remaining candidates.
        import time
        model = learner._ephemeral_model
        original_latent = model.latent
        latent_calls = 0

        def slow_latent(values, target=False):
            nonlocal latent_calls
            latent_calls += 1
            time.sleep(0.03)
            return original_latent(values, target=target)

        monkeypatch.setattr(model, "latent", slow_latent)
        recall = learner.episodic_recall(
            sessions[0], history_length=2, limit=4, nonblocking=True,
            budget_s=0.04, warm_only=True,
        )
        assert recall["status"] == "BUDGET_EXCEEDED", recall
        assert latent_calls <= 2, latent_calls

        matrix = learner.receiver_matrix(
            sessions[0], world_model.ACTIONS, history_length=2,
            nonblocking=True, warm_only=True,
        )
        assert matrix["status"] == "SHADOW_READOUT_ONLY"
        assert matrix["checkpoint_sha256"] == first["checkpoint_sha256"]
        assert matrix["native_body_consumed"] is False
        assert matrix["native_body_weights_changed"] is False
        assert matrix["decision_authority"] == "NONE"
        assert set(matrix["learning_intent_ids"]) == {"B1_DETAIL", "B2_GIST"}
        assert set(matrix["weight_delta_receipt_ids"]) == {"B1_DETAIL", "B2_GIST"}
        assert set(matrix["matrix"]) == set(world_model.ACTIONS)

        for action in world_model.ACTIONS:
            for role in ("B1_DETAIL", "B2_GIST"):
                batched = matrix["matrix"][action][role]
                single = learner.receiver_readout(
                    role, sessions[0], action, history_length=2
                )
                assert batched["status"] == "SHADOW_READOUT_ONLY"
                assert single["status"] == "SHADOW_READOUT_ONLY"
                assert batched["prediction"].keys() == single["prediction"].keys()
                for key, value in single["prediction"].items():
                    assert batched["prediction"][key] == pytest.approx(value, rel=1e-10, abs=1e-10)
                assert batched["uncertainty"] == pytest.approx(single["uncertainty"], rel=1e-10, abs=1e-10)
                assert batched["support_samples"] == single["support_samples"]
                assert batched["support_scope"] == "TRAIN_SPLIT_ONLY"
                assert batched["support_min_samples"] == 8
                assert batched["checkpoint_sha256"] == single["checkpoint_sha256"]
                assert batched["source_sha256"] == single["source_sha256"]
                assert batched["history_action_ids"] == single["history_action_ids"]
                assert batched["history_source_sha256s"] == single["history_source_sha256s"]
                assert batched["receiver_utility"] == single["receiver_utility"]
                assert batched["learning_intent_id"] == matrix["learning_intent_ids"][role]
                assert single["learning_intent_id"] == matrix["learning_intent_ids"][role]
                assert batched["weight_delta_receipt_id"] == matrix["weight_delta_receipt_ids"][role]
                assert single["weight_delta_receipt_id"] == matrix["weight_delta_receipt_ids"][role]
                assert batched["target_adapter_revision"] == "v14-temporal-receiver-adapter-v1"
                assert batched["native_body_consumed"] is False
                assert batched["native_body_weights_changed"] is False

        # Session 1 has a deliberate OUTCOME_UNKNOWN at event 2. The receiver
        # must not bridge that gap, even though earlier contiguous history exists.
        gap = learner.receiver_matrix(
            sessions[1], world_model.ACTIONS, history_length=2, nonblocking=True
        )
        assert gap["status"] == "NONCONTIGUOUS_HISTORY"
        assert gap["matrix"] == {}

        # Session 2 has a complete contiguous history and remains a valid receiver.
        other = learner.receiver_matrix(
            sessions[2], world_model.ACTIONS, history_length=2, nonblocking=True
        )
        assert other["status"] == "SHADOW_READOUT_ONLY"
        assert other["history_source_sha256s"] != matrix["history_source_sha256s"]

        # A missing history is a negative control, not a fabricated readout.
        missing = learner.receiver_matrix(
            "no-such-session", world_model.ACTIONS, history_length=2, nonblocking=True
        )
        assert missing["status"] == "INSUFFICIENT_HISTORY"
        assert missing["matrix"] == {}

        # Foreground nonblocking reads must fail closed when the shared JEPA
        # lock is held exclusively by a checkpoint writer.
        with learner._locked(True):
            with pytest.raises(BlockingIOError):
                learner.receiver_matrix(
                    sessions[0], world_model.ACTIONS, history_length=2, nonblocking=True
                )
    finally:
        store.close()


def test_temporal_A_B_C_A_replay_ablation_uses_matched_steps_and_retains_old_cohorts(tmp_path):
    home = tmp_path / "temporal-multishift-retention-store"
    store = _make_store(home)
    try:
        _make_dataset(store, "A", 32, start_index=0)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        cohort_a = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert cohort_a["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", cohort_a
        state_a, _ = store.state(STATE_KEY, None)
        sha_a = state_a["active"]["checkpoint_sha256"]
        steps_a = state_a["active"]["fit_steps"]
        anchor_a = state_a["active"]["retention_holdouts"][0]
        assert len(anchor_a["target_latents"]) == len(anchor_a["X"])
        assert len(anchor_a["target_sha256"]) == 64

        _make_dataset(store, "B", 32, start_index=32)
        cohort_b_replay = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert cohort_b_replay["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", cohort_b_replay
        assert cohort_b_replay["metrics"]["replay_mode"] == "uniform"
        assert cohort_b_replay["metrics"]["steps_this_update"] == 80
        assert len(cohort_b_replay["metrics"]["retention_mse_before"]) == 1
        assert cohort_b_replay["metrics"]["retention_pass"] is True
        assert cohort_b_replay["metrics"]["retention_reference"] == "FIXED_EMA_TARGET_ANCHOR"
        state_b, _ = store.state(STATE_KEY, None)
        assert state_b["active"]["retention_holdouts"][0] == anchor_a

        # Fork the same A checkpoint and same B receipts into a matched no-replay
        # attempt. Rollback preserves B as pending, so no new T8 event is needed.
        assert learner.rollback()["status"] == "ROLLED_BACK"
        restored_a, _ = store.state(STATE_KEY, None)
        assert restored_a["active"]["checkpoint_sha256"] == sha_a
        cohort_b_no_replay = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="none",
        )
        assert cohort_b_no_replay["status"] in {
            "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA",
            "RETENTION_GATE_REJECTED",
            "UTILITY_GATE_REJECTED",
        }, cohort_b_no_replay
        no_replay_metrics = cohort_b_no_replay["metrics"]
        assert cohort_b_no_replay["pending_retried"] >= 100
        assert no_replay_metrics["replay_mode"] == "none"
        assert no_replay_metrics["steps_this_update"] == cohort_b_replay["metrics"]["steps_this_update"]
        assert no_replay_metrics["optimizer_steps"] == cohort_b_replay["metrics"]["optimizer_steps"]
        assert no_replay_metrics["train_windows"] < cohort_b_replay["metrics"]["train_windows"]
        if cohort_b_no_replay["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA":
            assert learner.rollback()["status"] == "ROLLED_BACK"
        restored_a, _ = store.state(STATE_KEY, None)
        assert restored_a["active"]["checkpoint_sha256"] == sha_a

        # Reapply B with replay, then carry A→B→C→A through two further cohorts.
        cohort_b_replay_again = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert cohort_b_replay_again["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", cohort_b_replay_again
        assert cohort_b_replay_again["pending_retried"] >= 100
        assert cohort_b_replay_again["metrics"]["steps_this_update"] == 80

        _make_dataset(store, "C", 32, start_index=64)
        cohort_c = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert cohort_c["status"] in {
            "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", "RETENTION_GATE_REJECTED"
        }, cohort_c
        state_c, _ = store.state(STATE_KEY, None)
        if cohort_c["status"] == "RETENTION_GATE_REJECTED":
            # This is a valid negative result: the retention veto must leave the
            # previous accepted checkpoint active and keep C retryable. Never
            # weaken the 10% gate or label the candidate as a successful update.
            assert cohort_c["checkpoint_committed"] is False
            assert cohort_c["metrics"]["retention_pass"] is False
            assert any(
                after > before * 1.10 + 1e-9
                for before, after in zip(
                    cohort_c["metrics"]["retention_mse_before"],
                    cohort_c["metrics"]["retention_mse_after"],
                )
            )
            assert state_c["active"]["checkpoint_sha256"] == cohort_b_replay_again["checkpoint_sha256"]
            assert state_c["previous"]["checkpoint_sha256"] == sha_a
            assert len(state_c["pending_rows"]) >= cohort_c["verified_receipts"]
        else:
            assert cohort_c["metrics"]["retention_pass"] is True
            assert state_c["active"]["checkpoint_sha256"] == cohort_c["checkpoint_sha256"]

        # A2 is a disjoint-source reacquisition of A's distribution. If the
        # measured retention gate accepts it, assert the numeric/checkpoint diff;
        # if not, assert the prior accepted checkpoint remains intact.
        _make_dataset(store, "A2", 32, start_index=0)
        cohort_a2 = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert cohort_a2["status"] in {
            "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA",
            "RETENTION_GATE_REJECTED", "UTILITY_GATE_REJECTED",
        }, cohort_a2
        metrics = cohort_a2["metrics"]
        if cohort_c["status"] == "RETENTION_GATE_REJECTED":
            assert cohort_a2["pending_retried"] >= cohort_c["verified_receipts"]
        if cohort_a2["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA":
            assert metrics["retention_pass"] is True
            assert metrics["source_disjoint"] is True
            assert metrics["parameter_delta_norm"] > 0
            assert metrics["encoder_delta_norm"] > 0
            assert metrics["predictor_delta_norm"] > 0
            assert metrics["ema_target_delta_norm"] > 0
            assert metrics["parent_checkpoint_sha256"] == state_c["active"]["checkpoint_sha256"]
            assert metrics["optimizer_steps"] > steps_a
            assert metrics["holdout_mse_after"] <= metrics["holdout_mse_before"] * 1.05 + 1e-9
            assert all(
                after <= before * 1.10 + 1e-9
                for before, after in zip(
                    metrics["retention_mse_before"], metrics["retention_mse_after"]
                )
            )
            final_state, _ = store.state(STATE_KEY, None)
            assert final_state["active"]["checkpoint_sha256"] == cohort_a2["checkpoint_sha256"]
            assert len(final_state["active"]["retention_holdouts"]) == 3
        else:
            final_state, _ = store.state(STATE_KEY, None)
            assert cohort_a2["checkpoint_committed"] is False
            assert final_state["active"]["checkpoint_sha256"] == state_c["active"]["checkpoint_sha256"]
            assert final_state["pending_rows"]
    finally:
        store.close()


def test_temporal_rollback_reports_absence_without_fabricating_a_prior_checkpoint(tmp_path):
    home = tmp_path / "temporal-rollback-store"
    store = _make_store(home)
    try:
        learner = TemporalWorldJEPAStoreConsumer(store)
        result = learner.rollback()
        assert result["status"] == "NO_ROLLBACK_CHECKPOINT"
        assert result["checkpoint_committed"] is False
    finally:
        store.close()






def test_source_disjoint_partition_is_stable_across_random_runtime_ids(tmp_path):
    stores = [
        _make_store(tmp_path / "split-stability-a"),
        _make_store(tmp_path / "split-stability-b"),
    ]
    partitions = []
    try:
        for store in stores:
            _make_dataset(store, "split-stability", 16)
            receipts, rejected, _cursor, scanned, _censored, has_more = verify_committed_temporal_page(
                store, after_seq=0, limit=64
            )
            assert rejected == 0
            assert scanned == 64
            assert has_more is False
            rows = []
            from v13.world_jepa_temporal import _receipt_row
            for receipt in receipts:
                if receipt.status != "OUTCOME_UNKNOWN":
                    rows.append(_receipt_row(store, receipt))
            windows = build_temporal_windows(store, rows)
            train, holdout, metrics = _split_windows(windows)
            assert metrics["source_disjoint"] is True
            train_sources = {source for window in train for source in window["source_sha256s"]}
            holdout_sources = {source for window in holdout for source in window["source_sha256s"]}
            assert train_sources.isdisjoint(holdout_sources)
            partitions.append((train_sources, holdout_sources))
        assert partitions[0] == partitions[1]
    finally:
        for store in stores:
            store.close()


def test_temporal_world_jepa_history_reaches_actual_b1_b2_offer_prompts_with_measured_gate(tmp_path, monkeypatch):
    import time
    from v13 import agi
    from v13.cognition import Cognition

    class CaptureRunner:
        def __init__(self):
            self.calls = []
            self.last_metrics = {}

        def generate(self, messages, cancel_event, deadline, tokens, schema):
            self.calls.append(messages)
            self.last_metrics = {
                "status": "FINAL", "duration_s": 0.001, "generated_tokens": 1,
            }
            yield json.dumps({
                "summary": "Use the verified recent action history.",
                "quotes": ["use the verified recent action history"],
                "uncertainty": "low",
                "needs_reentry": False,
            })

    class CapturePool:
        def __init__(self, runner):
            self.runner = runner

        def get(self, role):
            return self.runner

    class Models:
        def revision(self, role):
            return "synthetic-" + role

    monkeypatch.setattr(
        agi, "hub",
        lambda _runtime: SimpleNamespace(
            skills=SimpleNamespace(select=lambda _text: [])
        ),
    )
    home = tmp_path / "temporal-cognition-consumer"
    store = _make_store(home)
    try:
        sessions, _ = _make_dataset(store, "matrix", 64)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        trained = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert trained["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", trained

        # The prompt consumer must use the measured, persisted disjoint-holdout
        # utility gates from this exact trained checkpoint. Never manufacture an
        # accepted gate in the fixture: that would prove wiring but not learning.
        state, _ = store.state(STATE_KEY, None)
        from v13.world_jepa_consumer import receiver_utility_gate
        for gate_role in ("B1_DETAIL", "B2_GIST"):
            gate = receiver_utility_gate(state["active"]["receiver_metrics"], gate_role)
            assert gate["accepted"], {"role": gate_role, "gate": gate,
                                      "metrics": state["active"]["receiver_metrics"]}
        assert state["active"]["checkpoint_sha256"] == trained["checkpoint_sha256"]

        text = "Current request: use the verified recent action history."
        event = store.event(sessions[0], text)
        runner = CaptureRunner()
        runtime = SimpleNamespace(
            store=store,
            home=home,
            session=sessions[0],
            cfg={
                "b2_state_slots": 0,
                "b2_control": "two_body",
                "b2_context_chars": 128,
                "memory_threshold": 0.25,
                "b2_offer_body_state": True,
                "b2_quote_select": "off",
                "observer_tokens": 256,
                "offer_style": "solve",
                "offer_quote_min_chars": 0,
                "offer_quote_context_chars": 0,
                "b1_recent_source_chars": 0,
                "segment_mode": "fixed",
                "body_question_b1": "",
                "body_question_b2": "",
                "body_question_scope": "always",
                "observer_mode": "foreground",
                "deadline_seconds": 30,
            },
            guard=SimpleNamespace(state="NORMAL", mode="GREEN"),
            models=Models(),
            pool=CapturePool(runner),
            cancel_event=threading.Event(),
        )
        runtime._temporal_world_jepa_consumer = learner
        cognition = Cognition(runtime)

        # A cold foreground call must fail closed without entering a slow model load.
        learner._ephemeral_model = None
        learner._ephemeral_checkpoint_sha = None
        original_load = learner._load_model
        cold_load_calls = 0

        def slow_cold_load(record):
            nonlocal cold_load_calls
            cold_load_calls += 1
            time.sleep(0.2)
            return original_load(record)

        learner._load_model = slow_cold_load
        try:
            cold_offer = cognition.offer(
                "B1_DETAIL", event, 0, time.monotonic() + 5.0
            )
            assert cold_offer["role"] == "B1_DETAIL"
            cold_payload = json.loads(runner.calls[-1][1]["content"])
            assert "world_jepa_temporal" not in cold_payload["body_state"]
            assert cold_load_calls == 0
        finally:
            learner._load_model = original_load

        warm = learner.warm_active_checkpoint()
        assert warm["status"] == "WARMED"
        for role in ("B1_DETAIL", "B2_GIST"):
            result = cognition.offer(role, event, 0, time.monotonic() + 5.0)
            assert result["role"] == role

        assert len(runner.calls) == 3
        prompts = {}
        for messages in runner.calls[1:]:
            payload = json.loads(messages[1]["content"])
            assert "body_state" in payload
            state = payload["body_state"]
            assert state["authority"] == "STATE_NOT_FACT"
            assert "world_jepa_temporal" in state, state
            assert "mode" in state["world"] and "observed_actions" in state["world"]
            assert "scope" not in state["world"]
            prior = state["world_jepa_temporal"]
            assert prior["status"] == "SHADOW_READOUT_ONLY"
            assert prior["native_body_consumed"] is False
            assert prior["native_body_weights_changed"] is False
            assert prior["decision_authority"] == "NONE"
            assert len(json.dumps(state, separators=(",", ":"))) <= 700
            prompts[state["role"]] = prior

        assert set(prompts) == {"B1_DETAIL", "B2_GIST"}
        detail, gist = prompts["B1_DETAIL"], prompts["B2_GIST"]
        assert detail["history_length"] == 2
        assert gist["history_length"] == 3
        assert detail["target"] == "DURATION+OUTPUT_CHARS"
        assert gist["target"] == "P_FINAL_NOT_CORRECTNESS"
        assert all(len(value) == 8 for value in detail["history_sources"])
        assert all(len(value) == 8 for value in gist["history_sources"])
        assert detail["checkpoint"] == gist["checkpoint"] == trained["checkpoint_sha256"][:12]
        assert "prediction" in detail["note"]
        assert "not fact/permission" in detail["note"]
        assert "prediction" in gist["note"]
        assert "not fact/permission" in gist["note"]
        assert all(len(row) == 4 for row in detail["rows"])
        assert all(len(row) == 3 for row in gist["rows"])

        query_rows = store.rows(
            "SELECT payload FROM packets WHERE kind='QueryPacket' AND event_id=? ORDER BY created",
            (event["event_id"],),
        )
        temporal_query_rows = []
        non_temporal_query_count = 0
        for row in query_rows:
            query_packet = json.loads(row["payload"])
            ref = query_packet["bodyview"]["body_state_ref"]
            stored = json.loads(store.read_source(ref))
            audit = stored.get("temporal_world_jepa_audit")
            if (stored.get("schema") == "V14_BODY_STATE_WITH_WORLDJEPA_AUDIT/2"
                    and isinstance(audit, dict)
                    and audit.get("status") == "READOUT_CREATED"):
                temporal_query_rows.append((query_packet, ref, stored))
            else:
                non_temporal_query_count += 1
        # The cold B1 negative-control offer also emits a QueryPacket and a
        # source-bound OMITTED audit; only the two warm readouts are receivers.
        assert len(temporal_query_rows) == 2
        assert non_temporal_query_count >= 1
        for query_packet, ref, stored in temporal_query_rows:
            role = query_packet["target_role"]
            assert ref in query_packet["provenance"]
            audit = stored["temporal_world_jepa_audit"]
            assert audit["body_state_created"] is True
            # The source record is created before Cognition.offer consumes it.
            # The QueryPacket plus captured native prompt above is the consumption proof.
            assert audit["body_prompt_consumed"] is False
            assert audit["checkpoint_sha256"] == trained["checkpoint_sha256"]
            assert audit["learning_intent_ids"][role] == trained["learning_intent_ids"][role]
            assert audit["weight_delta_receipt_ids"][role] == trained["weight_delta_receipt_ids"][role]
            assert audit["role"] == role
            assert audit["history_length"] == (2 if role == "B1_DETAIL" else 3)
            assert audit["target_semantics"] == (
                "B1_DURATION_OUTPUT_SIZE" if role == "B1_DETAIL"
                else "B2_P_FINAL_NOT_ANSWER_CORRECTNESS"
            )
            assert len(audit["history_action_ids"]) == audit["history_length"]
            assert len(audit["history_source_sha256s"]) == audit["history_length"]
            assert all(len(value) == 64 for value in audit["history_source_sha256s"])
            assert audit["native_body_consumed"] is False
            assert audit["native_body_weights_changed"] is False
            assert audit["decision_authority"] == "NONE"
            assert audit["supported_action_samples"]
            assert all(value >= 8 for value in audit["supported_action_samples"].values())

        # A writer holding the temporal JEPA lock must not stall the foreground
        # B1 offer; the optional readout is omitted and the normal body state remains.
        runner.calls.clear()
        started = time.monotonic()
        with learner._locked(True):
            result = cognition.offer(
                "B1_DETAIL", event, 0, time.monotonic() + 5.0
            )
            elapsed = time.monotonic() - started
        assert result["role"] == "B1_DETAIL"
        assert elapsed < 1.0
        fallback = json.loads(runner.calls[-1][1]["content"])["body_state"]
        assert "world_jepa_temporal" not in fallback
        assert fallback["authority"] == "STATE_NOT_FACT"
    finally:
        store.close()

def test_bodyview_records_rejected_temporal_gate_without_prompt_leak(tmp_path, monkeypatch):
    from v13 import agi

    monkeypatch.setattr(
        agi, "hub",
        lambda _runtime: SimpleNamespace(
            skills=SimpleNamespace(select=lambda _text: [])
        ),
    )
    home = tmp_path / "temporal-bodyview-rejected-gate"
    store = _make_store(home)
    try:
        sessions, _ = _make_dataset(store, "rejected-gate", 32)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        trained = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert trained["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", trained

        # Explicit negative control: the learned holdout receiver is rejected.
        state, version = store.state(STATE_KEY, None)
        prefix = "b1_detail"
        state["active"]["receiver_metrics"].update({
            prefix + "_holdout_mse": 2.0,
            prefix + "_mean_baseline_mse": 1.0,
            prefix + "_zero_latent_mse": 1.0,
            prefix + "_shuffled_latent_mse": 1.0,
        })
        store.set_state(STATE_KEY, state, expected=version)

        text = "Do not expose an unaccepted temporal prediction."
        event = store.event(sessions[0], text)
        runtime = SimpleNamespace(store=store, session=sessions[0], home=home)
        runtime._temporal_world_jepa_consumer = learner
        warm = learner.warm_active_checkpoint()
        assert warm["status"] == "WARMED"
        result = bodyview.body_state(runtime, event, "B1_DETAIL", text)
        assert result is not None
        assert "world_jepa_temporal" not in result["view"]
        stored = json.loads(store.read_source(result["source_ref"]))
        assert stored["schema"] == "V14_BODY_STATE_WITH_WORLDJEPA_AUDIT/2"
        audit = stored["temporal_world_jepa_audit"]
        assert audit["schema"] == "V14_TEMPORAL_WORLDJEPA_BODY_RECEIVER_AUDIT/1"
        assert audit["status"] == "OMITTED"
        assert audit["reason"] == "RECEIVER_UTILITY_REJECTED"
        assert audit["role"] == "B1_DETAIL"
        assert audit["event_id"] == event["event_id"]
        assert audit["history_length"] == 2
        assert audit["body_prompt_consumed"] is False
        assert audit["native_body_consumed"] is False
        assert audit["native_body_weights_changed"] is False
        assert audit["decision_authority"] == "NONE"
        assert text not in json.dumps(audit)
    finally:
        store.close()

def test_memory_forget_composes_temporal_guard_clears_warm_cache_and_replays(tmp_path):
    home = tmp_path / "temporal-memory-forget-runtime-hook"
    store = _make_store(home)
    try:
        _make_dataset(store, "memory-forget-runtime", 32)
        _permissions(store, steps=80)
        runtime = SimpleNamespace(store=store, home=home)
        from v13.world_jepa_temporal import runtime_consumer
        learner = runtime_consumer(runtime)
        trained = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert trained["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", trained
        assert trained["metrics"]["parameter_delta_norm"] > 0
        assert trained["metrics"]["ema_target_delta_norm"] > 0
        assert learner.warm_active_checkpoint()["status"] == "WARMED"

        before, _ = store.state(STATE_KEY, None)
        active = before["active"]
        row = next(row for row in active["experience_rows"] if row.get("source_refs"))
        source_ref = row["source_refs"][0]
        source_id = source_ref["source_id"]
        event_id = row["event_id"]
        checkpoint = learner.home / active["checkpoint"]
        assert checkpoint.is_file()
        assert learner._ephemeral_model is not None

        # This is the unchanged Memory API in the current release base. It
        # imports world_jepa_consumer.source_forget_guard at call time.
        Memory(store, {})._forget_source(source_id, event_id)

        after, _ = store.state(STATE_KEY, None)
        assert after["active"] is None
        assert after["previous"] is None
        assert after["scan_cursor"] == 0
        assert after["pending_rows"] == []
        assert not checkpoint.exists()
        assert learner._ephemeral_model is None
        assert learner._ephemeral_checkpoint_sha is None
        source = store.one("SELECT deleted FROM sources WHERE id=?", (source_id,))
        assert source is not None and source["deleted"] == 1
        with pytest.raises(ValueError):
            store.read_source(source_ref)

        # The deleted source is rejected on the durable T8 rescan; remaining
        # independent sessions can still train a fresh checkpoint.
        retrained = runtime_consumer(runtime).update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert retrained["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", retrained
        assert retrained["metrics"]["parameter_delta_norm"] > 0
        assert retrained["metrics"]["ema_target_delta_norm"] > 0
        current, _ = store.state(STATE_KEY, None)
        assert not _record_references_source(store, current["active"], source_id)
        assert all(
            source_id not in {ref["source_id"] for ref in item.get("source_refs", [])}
            for item in current["active"]["experience_rows"]
        )
    finally:
        store.close()
