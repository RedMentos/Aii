"""SleepRuntime idle scheduler -> persistent WorldJEPA/Planner integration.

All transitions are synthetic fixtures written through the real SQLite Store.
No native GGUF body, Android device, or Redmi behavior is claimed.
"""
from types import SimpleNamespace
import os
import threading

EXPECT_OPTIMIZER_STATE_PERSISTED = True

from v13 import contracts, world_model
from v13.scheduler import EventScheduler
from v13.sleep import SleepRuntime
from v13.store import Store
from v13.world_jepa_consumer import WorldJEPAStoreConsumer, receiver_utility_gate
from v13.world_jepa_planner import consume_world_planner_shadow, read_world_planner_shadow
from v13.world_jepa_runtime import PERMISSION_KEY


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 postcommit runtime integration")
    return store, session


def _add_transitions(store, session, start, count, status_overrides=None):
    status_overrides = status_overrides or {}
    event_ids = []
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        text = f"synthetic-postcommit-source-{index:04d}" + ("x" * (index % 29))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        route = actions[index % len(actions)]
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
        action_index = index % len(actions)
        store.finish_action(
            action_id,
            status_overrides.get(index, "FAILED" if index % 5 == 0 else "FINAL"),
            {
                "action_duration_s": 0.15 + action_index * 0.65 + (index % 13) * 0.02,
                "characters": 9 + action_index * 24 + (index % 23) * 0.75,
            },
        )
        event_ids.append(event_id)
    return event_ids


def _sleep(store, home):
    sleep = object.__new__(SleepRuntime)
    sleep.r = SimpleNamespace(store=store, home=home, cancel_event=threading.Event(),
                              guard=SimpleNamespace(update=lambda _snapshot: "NORMAL"),
                              resources=lambda: {})
    sleep.scheduler = EventScheduler(store, {})
    return sleep


def _planner_expected_status(metrics):
    accepted = all(
        receiver_utility_gate(metrics, role)["accepted"]
        for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL")
    )
    return "SHADOW_PLANNER_READY" if accepted else "SHADOW_PLANNER_UNAVAILABLE"


def test_consumer_startup_reaps_crash_abandoned_checkpoint_names(tmp_path):
    home = tmp_path / "brain-pending-cleanup"
    store, _ = _make_store(home)
    try:
        checkpoint_dir = home / "world_jepa"
        checkpoint_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        orphan = checkpoint_dir / ".world-jepa-shadow-interrupted"
        orphan.write_bytes(b"interrupted before publication")
        orphan.chmod(0o600)
        target = checkpoint_dir / ("jepa-" + "b" * 32 + ".npz")
        target.write_bytes(b"published checkpoint")
        target.chmod(0o600)
        linked = checkpoint_dir / ".world-jepa-shadow-linked"
        os.link(target, linked)
        WorldJEPAStoreConsumer(store, checkpoint_dir, learning_enabled=True)
        assert not orphan.exists() and not linked.exists()
        assert target.read_bytes() == b"published checkpoint"
    finally:
        store.close()


def test_sleep_runtime_postcommit_requires_observed_outcome_and_keeps_gates_default_off(tmp_path):
    home = tmp_path / "brain-default-off"
    store, session = _make_store(home)
    try:
        sleep = _sleep(store, home)
        cancelled = _add_transitions(store, session, 0, 1, {0: "CANCELLED"})[0]
        assert sleep.schedule_world_jepa(cancelled) is None
        assert store.state("v14.world_jepa.store_consumer", None)[0] is None

        observed = _add_transitions(store, session, 1, 1)[0]
        assert sleep.schedule_world_jepa(observed) is None
        result = sleep._run_world_jepa(observed)
        assert result["status"] == "POSTCOMMIT_PROCESSED"
        assert result["learning"]["status"] == "OFF"
        assert result["planner"]["status"] == "NO_CHECKPOINT"
        assert result["decision_authority"] == "NONE"
        assert result["native_body_consumed"] is False
        assert result["native_body_weights_changed"] is False
        assert store.state(PERMISSION_KEY, None)[0] is None
        assert store.state("v14.world_jepa.store_consumer", None)[0] is None

        missing = store.event(session, "no committed action outcome")
        rejected = sleep._run_world_jepa(missing["event_id"])
        assert rejected["status"] == "NO_COMMITTED_OUTCOME"
    finally:
        store.close()


def test_sleep_tick_schedules_one_authorized_idle_batch_and_coalesces_turn_bursts(tmp_path):
    home = tmp_path / "brain-scheduler"
    store, session = _make_store(home)
    try:
        sleep = _sleep(store, home)
        first_event = _add_transitions(store, session, 0, 1)[0]
        assert sleep.schedule_world_jepa() is None

        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        scheduled_id = sleep.schedule_world_jepa()
        assert type(scheduled_id) is str and scheduled_id
        pending = sleep.scheduler.pending()
        scheduled = next(item for item in pending if item["id"] == scheduled_id)
        assert scheduled["kind"] == "IDLE"
        assert scheduled["action"] == "jepa_update"
        assert scheduled["payload"] == {"event_id": first_event}

        _add_transitions(store, session, 1, 1)
        assert sleep.schedule_world_jepa() is None
        assert len([item for item in sleep.scheduler.pending() if item["action"] == "jepa_update"]) == 1

        censored = _add_transitions(store, session, 2, 1, {2: "OUTCOME_UNKNOWN"})[0]
        assert sleep.schedule_world_jepa(censored) is None
    finally:
        store.close()


def test_sleep_jepa_job_runs_real_postcommit_consumer_and_persists_completion(tmp_path):
    home = tmp_path / "brain-scheduler-job"
    store, session = _make_store(home)
    try:
        event_id = _add_transitions(store, session, 0, 1)[0]
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        posted = sleep.schedule_world_jepa()
        dispatched = sleep.scheduler.next(idle=True, resource_state="NORMAL", quiet=False)
        assert dispatched is not None and dispatched["id"] == posted
        result = sleep.job(dispatched)
        assert result["status"] == "POSTCOMMIT_PROCESSED"
        history = sleep.scheduler.report()["history"]
        assert any(item["id"] == posted and item["status"] == "DONE" for item in history)
        cursor, _ = store.state("v14.world_jepa.sleep_cursor", None)
        assert cursor["last_event_id"] == event_id
    finally:
        store.close()


def test_sleep_jepa_job_requeues_one_bounded_continuation_when_more_t8_rows_exist(tmp_path):
    home = tmp_path / "brain-jepa-continuation"
    store, session = _make_store(home)
    try:
        event_id = _add_transitions(store, session, 0, 1)[0]
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        sleep._run_world_jepa = lambda event_id, limit=64: {
            "status": "POSTCOMMIT_PROCESSED",
            "event_id": event_id,
            "learning": {"status": "WAITING_FOR_MORE_T8_DATA", "has_more": True},
            "planner": {"status": "NO_CHECKPOINT"},
        }
        posted = sleep.scheduler.post(
            "IDLE", action="jepa_update", payload={"event_id": event_id},
            dedup="v14-world-jepa",
        )
        dispatched = sleep.scheduler.next(idle=True, resource_state="NORMAL", quiet=False)
        assert dispatched is not None and dispatched["id"] == posted
        result = sleep.job(dispatched)
        assert result["learning"]["has_more"] is True
        assert result["continuation_scheduled"] is True
        pending = [item for item in sleep.scheduler.pending() if item["action"] == "jepa_update"]
        assert len(pending) == 1
        assert pending[0]["payload"] == {"event_id": event_id}
    finally:
        store.close()


def test_sleep_runtime_postcommit_updates_world_jepa_ema_replay_and_planner_with_restart_rollback(tmp_path):
    home = tmp_path / "brain-runtime-jepa"
    store, session = _make_store(home)
    try:
        first_events = _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        first = sleep._run_world_jepa(first_events[-1], limit=256)
        assert first["status"] == "POSTCOMMIT_PROCESSED", first
        assert "learning" in first, first
        assert first["learning"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA", first
        first_metrics = first["learning"]["metrics"]
        assert first_metrics["optimizer_moments_persisted"] is EXPECT_OPTIMIZER_STATE_PERSISTED
        assert first_metrics["inverse_dynamics_optimizer_persisted"] is EXPECT_OPTIMIZER_STATE_PERSISTED
        assert first_metrics["optimizer_state_bootstrapped"] is False
        assert first_metrics["parameter_delta_norm"] > 0
        assert first_metrics["ema_target_delta_norm"] > 0
        assert first_metrics["holdout_improved"] is True
        assert first_metrics["negative_controls_separated"] is True
        assert first_metrics["retention_gate_accepted"] is True
        first_gate = {
            role: receiver_utility_gate(first_metrics, role)
            for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL")
        }
        first_planner_status = _planner_expected_status(first_metrics)
        assert first["planner"]["status"] == first_planner_status
        assert first["planner"]["persisted"] is True
        assert first["planner"]["decision_authority"] == "NONE"
        assert first["planner"]["dispatch"] is False
        assert first["planner"]["native_body_consumed"] is False
        assert first["planner"]["native_body_weights_changed"] is False
        assert first["planner"]["representation"] == "NUMERIC_ROLE_READOUTS_NOT_NATIVE_BODY_LATENT"
        for action in world_model.ACTIONS:
            for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL"):
                item = first["planner"]["candidate_readouts"][action][role]
                expected = "SHADOW_READOUT_ONLY" if first_gate[role]["accepted"] else "RECEIVER_UTILITY_REJECTED"
                assert item["status"] == expected
                if not first_gate[role]["accepted"]:
                    assert "prediction" not in item
        if first_planner_status == "SHADOW_PLANNER_READY":
            assert first["planner"]["memory_recall"]["status"] == "MEMORY_RECALL_SHADOW"
            assert first["planner"]["ranked_actions"]
        else:
            assert first["planner"]["memory_recall"]["status"] == "NO_RANKED_ACTION"
            assert first["planner"]["ranked_actions"] == []
        first_sha = first["learning"]["checkpoint_sha256"]
        assert first["planner"]["checkpoint_sha256"] == first_sha
        assert read_world_planner_shadow(store, first_events[-1])["status"] == first_planner_status

        second_events = _add_transitions(store, session, 256, 32)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 24, "replay_mode": "uniform",
        })
        second = sleep._run_world_jepa(second_events[-1], limit=256)
        assert second["learning"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        second_metrics = second["learning"]["metrics"]
        assert second_metrics["replay_rows"] >= 8
        assert second_metrics["fit_steps_after"] > second_metrics["fit_steps_before"]
        assert second_metrics["optimizer_moments_persisted"] is True
        assert second_metrics["optimizer_state_bootstrapped"] is False
        second_sha = second["learning"]["checkpoint_sha256"]
        assert second_sha != first_sha
        second_planner_status = _planner_expected_status(second_metrics)
        assert second["planner"]["status"] == second_planner_status

        restarted = WorldJEPAStoreConsumer(store, home / "world_jepa", learning_enabled=True)
        restored = restarted.restore()
        assert restored["status"] == "RESTORED"
        assert restored["checkpoint_sha256"] == second_sha
        restored_model = restarted._load_model(restarted._read_state()[0]["active"])
        if EXPECT_OPTIMIZER_STATE_PERSISTED:
            assert restored_model._training_state["main"]["t"] == second_metrics["fit_steps_after"]
        else:
            assert not hasattr(restored_model, "_training_state")
        rolled_back = restarted.rollback()
        assert rolled_back["status"] == "ROLLED_BACK"
        assert rolled_back["checkpoint_sha256"] == first_sha
        rolled_back_model = restarted._load_model(restarted._read_state()[0]["active"])
        if EXPECT_OPTIMIZER_STATE_PERSISTED:
            assert rolled_back_model._training_state["main"]["t"] == first_metrics["fit_steps_after"]
        else:
            assert not hasattr(rolled_back_model, "_training_state")
        assert read_world_planner_shadow(store, second_events[-1])["status"] == "STALE_CHECKPOINT"
        assert read_world_planner_shadow(store, first_events[-1])["status"] == first_planner_status

        persisted, _ = store.state("v14.world_jepa.store_consumer", None)
        assert persisted["active"]["checkpoint_sha256"] == first_sha
        assert "synthetic-postcommit-source-" not in repr(persisted)
        telemetry = store.rows(
            "SELECT metrics FROM telemetry WHERE kind='v14_world_jepa_postcommit' ORDER BY id"
        )
        assert telemetry
        assert "synthetic-postcommit-source-" not in repr(telemetry)
    finally:
        store.close()


def test_planner_refuses_censored_action_outcomes_even_when_they_are_terminal(tmp_path):
    home = tmp_path / "brain-censored-planner"
    store, session = _make_store(home)
    try:
        event_id = _add_transitions(store, session, 0, 1, {0: "CANCELLED"})[0]
        rejected = consume_world_planner_shadow(store, event_id, home=home)
        assert rejected["status"] == "NO_COMMITTED_OUTCOME"
        assert store.state("v14.world_jepa.planner_shadow:" + event_id, None)[0] is None
    finally:
        store.close()


def test_sleep_scheduler_uses_older_observed_outcome_when_newest_action_is_censored(tmp_path):
    home = tmp_path / "brain-censored-latest"
    store, session = _make_store(home)
    try:
        observed = _add_transitions(store, session, 0, 1)[0]
        _add_transitions(store, session, 1, 1, {1: "CANCELLED"})
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        posted = sleep.schedule_world_jepa()
        assert posted
        pending = next(item for item in sleep.scheduler.pending() if item["id"] == posted)
        assert pending["payload"] == {"event_id": observed}
    finally:
        store.close()


def test_sleep_jepa_cancelled_by_user_preemption_requeues_without_checkpoint_commit(tmp_path):
    home = tmp_path / "brain-jepa-cancel"
    store, session = _make_store(home)
    try:
        event_ids = _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)

        class CancelAfter:
            def __init__(self, threshold):
                self.threshold = threshold
                self.calls = 0
            def is_set(self):
                self.calls += 1
                return self.calls >= self.threshold

        cancel = CancelAfter(8)
        sleep.r.cancel_event = cancel
        posted = sleep.schedule_world_jepa(event_ids[-1])
        dispatched = sleep.scheduler.next(idle=True, resource_state="NORMAL", quiet=False)
        assert dispatched is not None and dispatched["id"] == posted
        result = sleep.job(dispatched)
        assert result["status"] == "CANCELLED"
        assert cancel.calls >= 8
        assert store.state("v14.world_jepa.store_consumer", None)[0] is None
        assert not list((home / "world_jepa").glob("jepa-*.npz"))
        pending = [item for item in sleep.scheduler.pending() if item["id"] == posted]
        assert len(pending) == 1 and pending[0]["status"] == "PENDING"
    finally:
        store.close()


def test_planner_only_checkpoint_readout_does_not_consume_future_learning_opt_in(tmp_path):
    home = tmp_path / "brain-jepa-gate-resume"
    store, session = _make_store(home)
    try:
        first_events = _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        first = sleep._run_world_jepa(first_events[-1], limit=256)
        assert "learning" in first, first
        assert first["learning"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA", first
        first_planner_status = _planner_expected_status(first["learning"]["metrics"])
        assert first["planner"]["status"] == first_planner_status

        later_event = _add_transitions(store, session, 256, 1)[0]
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": False, "optimizer_permission": False,
            "steps": 120, "replay_mode": "uniform",
        })
        posted = sleep.schedule_world_jepa()
        dispatched = sleep.scheduler.next(idle=True, resource_state="NORMAL", quiet=False)
        assert dispatched is not None and dispatched["id"] == posted
        planner_only = sleep.job(dispatched)
        assert planner_only["learning"]["status"] == "OFF"
        assert planner_only["planner"]["status"] == first_planner_status

        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        resumed = sleep.schedule_world_jepa()
        assert resumed
        event = next(item for item in sleep.scheduler.pending() if item["id"] == resumed)
        assert event["payload"] == {"event_id": later_event}
    finally:
        store.close()


def _wait_until(predicate, timeout=25.0):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return bool(predicate())


def test_real_runtime_worker_commits_turn_then_idle_jepa_persists_across_restart(tmp_path):
    """Exercise the real Runtime worker, not only a hand-called SleepRuntime facade."""
    import json
    import time

    from v13.runtime import Runtime

    home = tmp_path / "real-runtime-worker-jepa"
    runtime = Runtime(home, notify=lambda _message: None)
    checkpoint_sha = None
    fit_steps = None
    try:
        original_policy = runtime.sleep.cycle.policy

        def fast_idle_policy():
            policy = dict(original_policy())
            policy["tick_seconds"] = 0.01
            policy["enabled"] = False
            return policy

        runtime.sleep.cycle.policy = fast_idle_policy
        runtime.sleep.resource_state = lambda: "NORMAL"

        # A real Runtime.submit -> Runtime._worker -> Runtime._turn path.
        # Copy-exact keeps this acceptance test independent of installed GGUFs.
        turn_event_id = runtime.submit("Copy exactly: worker-jepa-lifecycle")
        def action_is_final():
            row = runtime.store.one(
                "SELECT status,outcome FROM actions WHERE event_id=?", (turn_event_id,)
            )
            return row is not None and row["status"] == "FINAL" and row["outcome"] is not None

        assert _wait_until(action_is_final)
        action = runtime.store.one(
            "SELECT status,outcome FROM actions WHERE event_id=?", (turn_event_id,)
        )
        assert action["status"] == "FINAL"
        assert action["outcome"] is not None
        assert runtime.store.one(
            "SELECT id FROM messages WHERE event_id=? AND role='assistant'",
            (turn_event_id,),
        ) is not None
        assert _wait_until(runtime.idle)

        # Keep the actual Runtime turn as the worker-lifecycle proof. Start the
        # learner cursor after it so the numeric update below uses a full,
        # source-disjoint 256-row synthetic cohort rather than mixing the generic
        # copy-exact action forecast into the JEPA training/holdout split.
        from v13.world_jepa_consumer import STATE_KEY, WorldJEPAStoreConsumer
        runtime_action = runtime.store.one(
            "SELECT rowid AS scan_seq FROM actions WHERE event_id=?", (turn_event_id,)
        )
        assert runtime_action is not None
        consumer = WorldJEPAStoreConsumer(runtime.store, home)
        consumer_state, consumer_version = consumer._read_state()
        consumer_state["scan_cursor"] = runtime_action["scan_seq"]
        runtime.store.set_state(STATE_KEY, consumer_state, expected=consumer_version)

        # Add a source-disjoint T8 cohort through the same durable Store API.
        # The temporary permission is test-only; production gates remain OFF.
        _add_transitions(runtime.store, runtime.session, 0, 256)
        latest = runtime.store.one(
            "SELECT event_id FROM actions WHERE outcome IS NOT NULL "
            "AND status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED') "
            "ORDER BY created DESC,id DESC LIMIT 1"
        )["event_id"]
        runtime.store.set_state(PERMISSION_KEY, {
            "learning_enabled": True,
            "optimizer_permission": True,
            "steps": 120,
            "replay_mode": "uniform",
        })
        original_run = runtime.sleep._run_world_jepa
        captured_runs = {}

        def capture_run(event_id, limit=64):
            result = original_run(event_id, limit=256)
            captured_runs[event_id] = result
            return result

        runtime.sleep._run_world_jepa = capture_run
        runtime.sleep.last_tick = -1e18
        runtime.wake.set()

        def learned_and_planned():
            state, _ = runtime.store.state("v14.world_jepa.store_consumer", None)
            cursor, _ = runtime.store.state("v14.world_jepa.sleep_cursor", None)
            active = state.get("active") if type(state) is dict else None
            return (
                type(active) is dict
                and type(cursor) is dict
                and cursor.get("last_learning_event_id") == latest
                and cursor.get("last_planner_event_id") == latest
            )

        assert _wait_until(lambda: latest in captured_runs and learned_and_planned())
        state, _ = runtime.store.state("v14.world_jepa.store_consumer", None)
        active = state["active"]
        checkpoint_sha = active["checkpoint_sha256"]
        fit_steps = active.get("fit_steps")
        assert type(checkpoint_sha) is str and len(checkpoint_sha) == 64
        worker_result = captured_runs[latest]
        learning = worker_result.get("learning", {})
        metrics = learning.get("metrics", {})
        assert learning.get("status") == "UPDATED_EXPERIMENTAL_WORLD_JEPA", {
            "worker_status": worker_result.get("status"),
            "learning_status": learning.get("status"),
            "planner_status": worker_result.get("planner", {}).get("status"),
        }
        assert metrics.get("parameter_delta_norm", 0) > 0
        assert metrics.get("ema_target_delta_norm", 0) > 0
        assert metrics.get("holdout_loss_after", float("inf")) < metrics.get("holdout_loss_before", float("-inf"))
        assert metrics.get("train_holdout_source_disjoint") is True
        assert metrics.get("negative_controls_separated") is True
        assert metrics.get("retention_gate_accepted") is True

        telemetry = runtime.store.rows(
            "SELECT event_id,metrics FROM telemetry WHERE kind='v14_world_jepa_postcommit' ORDER BY id"
        )
        assert telemetry
        decoded = [
            {
                "event_id": row["event_id"],
                **(json.loads(row["metrics"]) if isinstance(row["metrics"], str) else row["metrics"]),
            }
            for row in telemetry
        ]
        matching = [row for row in decoded if row.get("event_id") == latest]
        assert any(
            row.get("status") == "PASS"
            and row.get("component") == "world_predictor"
            and row.get("mode") == "shadow"
            and row.get("sha256") == checkpoint_sha
            and row.get("optimizer_steps", 0) > 0
            and row.get("target_changed") is True
            and row.get("loss_after", float("inf")) < row.get("loss_before", float("-inf"))
            and row.get("decision") == "none"
            and row.get("native_body_parameters_modified") is False
            for row in matching
        ), matching
        assert "worker-jepa-lifecycle" not in repr(state)
        assert "worker-jepa-lifecycle" not in repr(telemetry)
    finally:
        runtime.close()

    # A new real Runtime instance must restore the same checkpoint and must
    # not dispatch the already-consumed T8 event again.
    reopened = Runtime(home, notify=lambda _message: None)
    try:
        original_policy = reopened.sleep.cycle.policy

        def fast_restart_policy():
            policy = dict(original_policy())
            policy["tick_seconds"] = 0.01
            policy["enabled"] = False
            return policy

        reopened.sleep.cycle.policy = fast_restart_policy
        reopened.sleep.resource_state = lambda: "NORMAL"
        assert _wait_until(lambda: (
            (reopened.store.state("v14.world_jepa.store_consumer", None)[0] or {})
            .get("active", {}).get("checkpoint_sha256") == checkpoint_sha
        ))
        time.sleep(0.5)
        restored, _ = reopened.store.state("v14.world_jepa.store_consumer", None)
        assert restored["active"]["checkpoint_sha256"] == checkpoint_sha
        assert restored["active"].get("fit_steps") == fit_steps
        assert not [
            item for item in reopened.sleep.scheduler.pending()
            if item.get("action") == "jepa_update"
        ]
    finally:
        reopened.close()


def test_receiver_utility_gate_requires_mean_and_all_negative_controls():
    metrics = {
        "b1_detail_holdout_mse": 0.10,
        "b1_detail_mean_baseline_mse": 0.20,
        "b1_detail_zero_latent_mse": 0.18,
        "b1_detail_shuffled_latent_mse": 0.17,
    }
    accepted = receiver_utility_gate(metrics, "B1_DETAIL")
    assert accepted["accepted"] is True
    assert accepted["reason"] == "HELDOUT_BEATS_MEAN_AND_NEGATIVE_CONTROLS"

    for key in (
        "b1_detail_mean_baseline_mse",
        "b1_detail_zero_latent_mse",
        "b1_detail_shuffled_latent_mse",
    ):
        failed = dict(metrics)
        failed[key] = metrics["b1_detail_holdout_mse"]
        result = receiver_utility_gate(failed, "B1_DETAIL")
        assert result["accepted"] is False
        assert result["reason"] == "HELDOUT_DID_NOT_BEAT_ALL_CONTROLS"

    invalid = dict(metrics, b1_detail_shuffled_latent_mse=float("nan"))
    assert receiver_utility_gate(invalid, "B1_DETAIL")["reason"] == "RECEIVER_METRICS_INVALID"


def test_receiver_readout_fails_closed_when_its_shuffled_latent_control_fails(tmp_path):
    home = tmp_path / "brain-receiver-utility-gate"
    store, session = _make_store(home)
    try:
        event_ids = _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        result = sleep._run_world_jepa(event_ids[-1], limit=256)
        assert result["learning"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, version = store.state("v14.world_jepa.store_consumer", None)
        active = state["active"]
        metrics = active["metrics"]
        metrics["b1_detail_shuffled_latent_mse"] = metrics["b1_detail_holdout_mse"]
        store.set_state("v14.world_jepa.store_consumer", state, expected=version)

        from v13.world_jepa_runtime import receiver_readout
        rejected = receiver_readout(
            store, "B1_DETAIL", [12.0, 0.0, 4.0, 0.5],
            world_model.ACTIONS[0], home=home,
        )
        assert rejected["status"] == "RECEIVER_UTILITY_REJECTED"
        assert rejected["receiver_utility"]["accepted"] is False
        assert rejected["decision_authority"] == "NONE"
        assert rejected["native_body_consumed"] is False
        assert rejected["native_body_weights_changed"] is False
        assert "prediction" not in rejected
    finally:
        store.close()

def test_planner_withholds_each_role_when_its_own_negative_control_fails(tmp_path):
    """The actual batched Planner consumer must honor every role's utility gate."""
    home = tmp_path / "brain-planner-receiver-utility"
    store, session = _make_store(home)
    try:
        event_ids = _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        trained = sleep._run_world_jepa(event_ids[-1], limit=256)
        assert trained["learning"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        original_state, version = store.state("v14.world_jepa.store_consumer", None)
        baseline_metrics = dict(original_state["active"]["metrics"])
        # Give each role an explicitly passing, finite fixture so the test
        # isolates the real consumer gate rather than depending on whether a
        # particular random training cohort happens to qualify every head.
        for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL"):
            prefix = role.lower()
            baseline_metrics[prefix + "_holdout_mse"] = 0.10
            baseline_metrics[prefix + "_mean_baseline_mse"] = 0.20
            baseline_metrics[prefix + "_zero_latent_mse"] = 0.18
            baseline_metrics[prefix + "_shuffled_latent_mse"] = 0.17
        active = dict(original_state["active"])
        active["metrics"] = dict(baseline_metrics)
        original_state = dict(original_state)
        original_state["active"] = active
        store.set_state("v14.world_jepa.store_consumer", original_state, expected=version)

        baseline = consume_world_planner_shadow(store, event_ids[-1], home=home)
        assert baseline["status"] == "SHADOW_PLANNER_READY"
        assert baseline["ranked_actions"]
        assert all(
            baseline["candidate_readouts"][action][role]["status"] == "SHADOW_READOUT_ONLY"
            for action in world_model.ACTIONS
            for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL")
        )

        for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL"):
            current, version = store.state("v14.world_jepa.store_consumer", None)
            active = dict(current["active"])
            metrics = dict(active["metrics"])
            prefix = role.lower()
            holdout_key = prefix + "_holdout_mse"
            shuffled_key = prefix + "_shuffled_latent_mse"
            metrics[shuffled_key] = metrics[holdout_key]
            active["metrics"] = metrics
            current = dict(current)
            current["active"] = active
            store.set_state("v14.world_jepa.store_consumer", current, expected=version)

            planner = consume_world_planner_shadow(store, event_ids[-1], home=home)
            assert planner["status"] == "SHADOW_PLANNER_UNAVAILABLE"
            assert planner["ranked_actions"] == []
            assert planner["decision_authority"] == "NONE"
            assert planner["dispatch"] is False
            assert planner["native_body_consumed"] is False
            for action in world_model.ACTIONS:
                readout = planner["candidate_readouts"][action][role]
                assert readout["status"] == "RECEIVER_UTILITY_REJECTED"
                assert readout["receiver_utility"]["accepted"] is False
                assert "prediction" not in readout
                assert readout["decision_authority"] == "NONE"
                assert readout["native_body_consumed"] is False
                assert readout["native_body_weights_changed"] is False
                for other in ("B1_DETAIL", "B2_GIST", "SELF_MODEL"):
                    if other != role:
                        assert planner["candidate_readouts"][action][other]["status"] == "SHADOW_READOUT_ONLY"
            persisted = read_world_planner_shadow(store, event_ids[-1])
            assert persisted["status"] == "SHADOW_PLANNER_UNAVAILABLE"

            # Restore all passing metrics; the same event/checkpoint must recover
            # the ready view rather than returning the previous rejected snapshot.
            current, version = store.state("v14.world_jepa.store_consumer", None)
            active = dict(current["active"])
            active["metrics"] = dict(baseline_metrics)
            current = dict(current)
            current["active"] = active
            store.set_state("v14.world_jepa.store_consumer", current, expected=version)
            restored = consume_world_planner_shadow(store, event_ids[-1], home=home)
            assert restored["status"] == "SHADOW_PLANNER_READY"
            assert read_world_planner_shadow(store, event_ids[-1])["status"] == "SHADOW_PLANNER_READY"
    finally:
        store.close()
