"""Persistent temporal WorldJEPA: real Store/T8 producer, synthetic test experiences.

No native GGUF, Android or Redmi behavior is claimed by these fixtures.
"""
from types import SimpleNamespace
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
    _split_windows,
    build_temporal_windows,
)


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    return store


def _add_session(store, label, session_index, *, status_overrides=None, event_count=4):
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
        selection = contracts.packet(
            "ActionSelection", "C2_CONTROL", event_id, generation,
            [event["source_ref"]],
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

        # A learned source is protected while either active or rollback state retains it.
        source_row = active["active"]["experience_rows"][0]
        memory = Memory(store, {})
        with pytest.raises(ValueError, match="temporal WorldJEPA"):
            memory._forget_source(source_row["source_id"], source_row["event_id"])
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
        assert restored["previous"] is None
        assert len(restored["pending_rows"]) >= 100
        assert not (learner.home / second_record["checkpoint"]).exists()

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
    finally:
        store.close()


def test_source_forget_holds_store_lock_through_blob_unlink_against_republication(tmp_path):
    home = tmp_path / "source-forget-republication-store"
    store = _make_store(home)
    allow_unlink = threading.Event()
    refcount_checked = threading.Event()
    publish_started = threading.Event()
    publish_done = threading.Event()
    forget_done = threading.Event()
    errors = []
    new_ref = {}
    original_one = store.one
    try:
        source = store.source("shared-blob-content")
        session = store.new_session("forget race")
        event = store.event(session, "forget race event")
        memory = Memory(store, {})

        def gated_one(sql, params=()):
            result = original_one(sql, params)
            if "SELECT id FROM sources WHERE hash=? AND deleted=0" in sql:
                refcount_checked.set()
                if not allow_unlink.wait(5):
                    raise AssertionError("source-forget race gate timed out")
            return result

        store.one = gated_one

        def forget_source():
            try:
                memory._forget_source(source["source_id"], event["event_id"])
            except BaseException as exc:
                errors.append(exc)
            finally:
                forget_done.set()

        def republish_source():
            publish_started.set()
            try:
                new_ref["value"] = store.source("shared-blob-content")
            except BaseException as exc:
                errors.append(exc)
            finally:
                publish_done.set()

        forget_thread = threading.Thread(target=forget_source, daemon=True)
        forget_thread.start()
        assert refcount_checked.wait(5)
        publish_thread = threading.Thread(target=republish_source, daemon=True)
        publish_thread.start()
        assert publish_started.wait(5)

        # The forget thread is paused after the zero-refcount read. Its Store
        # RLock must remain held so Store.source cannot publish a new row that
        # would be orphaned by the pending blob unlink.
        lock_available = store.mutex.acquire(blocking=False)
        if lock_available:
            store.mutex.release()
        assert lock_available is False
        assert not publish_done.is_set()

        allow_unlink.set()
        forget_thread.join(5)
        publish_thread.join(5)
        assert not forget_thread.is_alive()
        assert not publish_thread.is_alive()
        assert forget_done.is_set() and publish_done.is_set()
        assert errors == []
        assert store.read_source(new_ref["value"]) == "shared-blob-content"
        assert (home / "data" / "blobs" / new_ref["value"]["sha256"]).is_file()
    finally:
        allow_unlink.set()
        store.one = original_one
        store.close()


def test_temporal_receiver_matrix_batches_bodyview_contract_with_single_readout_parity(tmp_path):
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

        matrix = learner.receiver_matrix(
            sessions[0], world_model.ACTIONS, history_length=2, nonblocking=True
        )
        assert matrix["status"] == "SHADOW_READOUT_ONLY"
        assert matrix["checkpoint_sha256"] == first["checkpoint_sha256"]
        assert matrix["native_body_consumed"] is False
        assert matrix["native_body_weights_changed"] is False
        assert matrix["decision_authority"] == "NONE"
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


def test_source_forget_uses_exact_structured_packet_and_state_references(tmp_path):
    home = tmp_path / "source-forget-exact-reference-store"
    store = _make_store(home)
    try:
        source = store.source("forget-target-payload")
        session = store.new_session("source forget")
        event = store.event(session, "source forget event")
        sid = source["source_id"]
        generation = event["brain_generation_id"]

        def add_packet(packet_id, payload):
            with store.tx() as conn:
                conn.execute(
                    "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                    (packet_id, "ForgetReferenceTest", event["event_id"],
                     generation, json.dumps(payload, sort_keys=True), 0.0),
                )

        add_packet("forget-exact-nested", {
            "schema": "test/1",
            "evidence": {"source_ref": {"source_id": sid}},
        })
        add_packet("forget-exact-source-list", {"source_ids": [sid]})
        add_packet("forget-prefix-collision", {
            "source_ref": {"source_id": sid + "0"}, "note": sid,
        })
        add_packet("forget-suffix-collision", {
            "source_ref": {"source_id": "x" + sid},
        })
        add_packet("forget-incidental-text", {"note": "not a source reference: " + sid})
        add_packet("forget-action-corollary", {
            "source_ref": {"source_id": sid},
        })
        with store.tx() as conn:
            conn.execute(
                "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?)",
                ("act-forget-corollary", event["event_id"], "TEST", "DISPATCHED",
                 "forget-action-corollary", "{}", None, 0.0),
            )

        exact_key = "cache:" + sid + ":exact"
        slash_key = "cache/" + sid + "/exact"
        prefix_key = "cache:" + sid + "0:collision"
        incidental_key = "note-" + sid + "-incidental"
        for key in (exact_key, slash_key, prefix_key, incidental_key):
            store.set_state(key, {"retained": True})

        Memory(store, {})._forget_source(sid, event["event_id"])

        assert store.one("SELECT deleted FROM sources WHERE id=?", (sid,))["deleted"] == 1
        for packet_id in ("forget-exact-nested", "forget-exact-source-list"):
            assert store.one("SELECT id FROM packets WHERE id=?", (packet_id,)) is None
        for packet_id in (
            "forget-prefix-collision", "forget-suffix-collision",
            "forget-incidental-text", "forget-action-corollary",
        ):
            assert store.one("SELECT id FROM packets WHERE id=?", (packet_id,)) is not None
        assert store.one("SELECT key FROM states WHERE key=?", (exact_key,)) is None
        assert store.one("SELECT key FROM states WHERE key=?", (slash_key,)) is None
        assert store.one("SELECT key FROM states WHERE key=?", (prefix_key,)) is not None
        assert store.one("SELECT key FROM states WHERE key=?", (incidental_key,)) is not None
    finally:
        store.close()


def test_source_forget_fails_closed_on_opaque_packet_without_partial_tombstone(tmp_path):
    home = tmp_path / "source-forget-opaque-packet-store"
    store = _make_store(home)
    try:
        source = store.source("forget-target-opaque")
        session = store.new_session("source forget opaque")
        event = store.event(session, "source forget opaque event")
        with store.tx() as conn:
            conn.execute(
                "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                ("forget-opaque-packet", "OpaqueTest", event["event_id"],
                 event["brain_generation_id"], "{not-json", 0.0),
            )

        with pytest.raises(ValueError, match="malformed packet JSON"):
            Memory(store, {})._forget_source(source["source_id"], event["event_id"])

        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (source["source_id"],)
        )["deleted"] == 0
        assert store.one(
            "SELECT id FROM packets WHERE id=?", ("forget-opaque-packet",)
        ) is not None
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
        cognition = Cognition(runtime)
        for role in ("B1_DETAIL", "B2_GIST"):
            result = cognition.offer(role, event, 0, time.monotonic() + 5.0)
            assert result["role"] == role

        prompts = {}
        for messages in runner.calls:
            payload = json.loads(messages[1]["content"])
            assert "body_state" in payload
            state = payload["body_state"]
            assert state["authority"] == "STATE_NOT_FACT"
            assert "world_jepa_temporal" in state, state
            prior = state["world_jepa_temporal"]
            assert prior["status"] == "SHADOW_READOUT_ONLY"
            assert prior["native_body_consumed"] is False
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

        query_rows = store.rows(
            "SELECT payload FROM packets WHERE kind='QueryPacket' AND event_id=? ORDER BY created",
            (event["event_id"],),
        )
        assert len(query_rows) == 2
        for row in query_rows:
            query_packet = json.loads(row["payload"])
            role = query_packet["target_role"]
            ref = query_packet["bodyview"]["body_state_ref"]
            assert ref in query_packet["provenance"]
            stored = json.loads(store.read_source(ref))
            assert stored["schema"] == "V14_BODY_STATE_WITH_WORLDJEPA_AUDIT/2"
            audit = stored["temporal_world_jepa_audit"]
            assert audit["body_state_created"] is True
            # The source record is created before Cognition.offer consumes it.
            # The QueryPacket plus captured native prompt above is the consumption proof.
            assert audit["body_prompt_consumed"] is False
            assert audit["checkpoint_sha256"] == trained["checkpoint_sha256"]
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

