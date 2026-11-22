"""Persistent temporal WorldJEPA: real Store/T8 producer, synthetic test experiences.

No native GGUF, Android or Redmi behavior is claimed by these fixtures.
"""
from types import SimpleNamespace
import threading

import numpy as np
import pytest

from v13 import contracts, world_model
from v13.memory import Memory
from v13.sleep import SleepRuntime
from v13.store import Store
from v13.world_jepa_runtime import PERMISSION_KEY
from v13.world_jepa_store_authority import verify_committed_temporal_page
from v13.world_jepa_temporal import (
    STATE_KEY,
    TemporalWorldJEPAStoreConsumer,
    build_temporal_windows,
)


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    return store


def _add_session(store, label, session_index, *, status_overrides=None):
    status_overrides = status_overrides or {}
    session = store.new_session(label)
    event_ids = []
    for offset in range(4):
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
        assert metrics["encoder_delta_norm"] > 0
        assert metrics["predictor_delta_norm"] > 0
        assert metrics["ema_target_delta_norm"] > 0
        assert metrics["checkpoint_parent_sha256"] is None
        assert metrics["checkpoint_sha256"] == first["checkpoint_sha256"]
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
        readout = restarted.receiver_readout("B1_DETAIL", sessions[0], action, history_length=2)
        assert readout["status"] in {"SHADOW_READOUT_ONLY", "RECEIVER_UTILITY_REJECTED"}
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

        # Distinct session histories must remain source-distinct in the batch result.
        gap = learner.receiver_matrix(
            sessions[1], world_model.ACTIONS, history_length=2, nonblocking=True
        )
        assert gap["status"] == "NONCONTIGUOUS_HISTORY"
        assert gap["matrix"] == {}

        other = learner.receiver_matrix(
            sessions[2], world_model.ACTIONS, history_length=2, nonblocking=True
        )
        assert other["status"] == "SHADOW_READOUT_ONLY"
        assert len(other["history_action_ids"]) == 2
        assert len(other["history_source_sha256s"]) == 2
        assert other["history_source_sha256s"] != matrix["history_source_sha256s"]
        broader = learner.receiver_matrix(
            sessions[2], world_model.ACTIONS, history_length=3, nonblocking=True
        )
        assert broader["status"] == "SHADOW_READOUT_ONLY"
        assert len(broader["history_action_ids"]) == 3
        assert len(broader["history_source_sha256s"]) == 3

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
        assert cohort_c["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", cohort_c
        assert len(cohort_c["metrics"]["retention_mse_before"]) == 2
        assert cohort_c["metrics"]["retention_pass"] is True

        # A2 is a disjoint-source reacquisition of A's distribution.
        _make_dataset(store, "A2", 32, start_index=0)
        cohort_a2 = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert cohort_a2["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", cohort_a2
        metrics = cohort_a2["metrics"]
        assert len(metrics["retention_mse_before"]) == 3
        assert len(metrics["retention_mse_after"]) == 3
        assert metrics["retention_pass"] is True
        assert metrics["source_disjoint"] is True
        assert metrics["parameter_delta_norm"] > 0
        assert metrics["ema_target_delta_norm"] > 0
        assert metrics["optimizer_steps"] > steps_a
        assert metrics["holdout_mse_after"] <= metrics["holdout_mse_before"] * 1.05 + 1e-9
        assert metrics["retention_mse_after"][0] <= metrics["retention_mse_before"][0] * 1.10 + 1e-9
        final_state, _ = store.state(STATE_KEY, None)
        assert final_state["active"]["checkpoint_sha256"] == cohort_a2["checkpoint_sha256"]
        assert len(final_state["active"]["retention_holdouts"]) == 3
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

def test_temporal_world_jepa_history_is_consumed_by_b1_b2_bodyview_with_distinct_horizons(tmp_path):
    import json
    import time
    from types import SimpleNamespace
    from v13 import bodyview

    home = tmp_path / "temporal-bodyview-integration"
    store = _make_store(home)
    try:
        sessions, _ = _make_dataset(store, "bodyview-temporal", 32)
        _permissions(store, steps=80)
        learner = TemporalWorldJEPAStoreConsumer(store, seed=29, ensemble=2)
        trained = learner.update(
            limit=64, max_pages=4, steps=80,
            optimizer_permission=True, replay_mode="uniform",
        )
        assert trained["status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA", trained
        event = store.event(sessions[0], "Current request: use the verified recent action history.")
        text = "Current request: use the verified recent action history."
        runtime = SimpleNamespace(
            store=store, home=home, session=sessions[0], cfg={},
            guard=SimpleNamespace(state="NORMAL", mode="GREEN"),
        )
        results = {}
        for role, expected_history, expected_target in (
            ("B1_DETAIL", 2, "B1_DURATION_OUTPUT_SIZE"),
            ("B2_GIST", 3, "B2_P_FINAL_NOT_ANSWER_CORRECTNESS"),
        ):
            result = bodyview.body_state(runtime, event, role, text)
            assert result is not None
            view = result["view"]
            assert "world_jepa_temporal" in view
            assert "world_jepa" not in view
            prior = view["world_jepa_temporal"]
            assert prior["status"] == "SHADOW_READOUT_ONLY"
            assert prior["history_length"] == expected_history
            assert prior["target"] == expected_target
            assert prior["native_body_consumed"] is False
            assert prior["decision_authority"] == "NONE"
            assert len(prior["rows"]) >= 2
            assert len(json.dumps(view, separators=(",", ":"))) <= bodyview.STATE_CHARS

            stored = json.loads(store.read_source(result["source_ref"]))
            assert stored["schema"] == "V14_BODY_STATE_WITH_WORLDJEPA_AUDIT/2"
            audit = stored["temporal_world_jepa_audit"]
            assert audit["checkpoint_sha256"] == trained["checkpoint_sha256"]
            assert audit["role"] == role
            assert audit["history_length"] == expected_history
            assert len(audit["history_action_ids"]) == expected_history
            assert len(audit["history_source_sha256s"]) == expected_history
            assert audit["body_prompt_consumed"] is True
            assert audit["native_body_consumed"] is False
            assert audit["native_body_weights_changed"] is False
            assert audit["decision_authority"] == "NONE"
            results[role] = prior

        assert results["B1_DETAIL"]["checkpoint"] == results["B2_GIST"]["checkpoint"]
        assert results["B1_DETAIL"]["history_length"] < results["B2_GIST"]["history_length"]

        started = time.monotonic()
        with learner._locked(True):
            busy = bodyview.body_state(runtime, event, "B1_DETAIL", text)
            elapsed = time.monotonic() - started
        assert elapsed < 1.0
        assert busy is not None
        assert "world_jepa_temporal" not in busy["view"]
    finally:
        store.close()
