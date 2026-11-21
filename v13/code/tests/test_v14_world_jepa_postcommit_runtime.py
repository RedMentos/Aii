"""SleepRuntime idle scheduler -> persistent WorldJEPA/Planner integration.

All transitions are synthetic fixtures written through the real SQLite Store.
No native GGUF body, Android device, or Redmi behavior is claimed.
"""
from types import SimpleNamespace
import queue
import threading
from pathlib import Path
from unittest.mock import patch

from v13 import contracts, world_model, world_jepa
from v13.scheduler import EventScheduler
from v13.sleep import SleepRuntime
from v13.store import Store
from v13.world_jepa_consumer import WorldJEPAStoreConsumer
from v13.world_jepa_planner import consume_world_planner_shadow, read_world_planner_shadow
from v13.world_jepa_runtime import PERMISSION_KEY, consume_after_commit


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
    sleep.r = SimpleNamespace(store=store, home=home)
    sleep.scheduler = EventScheduler(store, {})
    return sleep


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
        assert first["status"] == "POSTCOMMIT_PROCESSED"
        assert first["learning"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        first_metrics = first["learning"]["metrics"]
        assert first_metrics["parameter_delta_norm"] > 0
        assert first_metrics["ema_target_delta_norm"] > 0
        assert first_metrics["holdout_improved"] is True
        assert first_metrics["negative_controls_separated"] is True
        assert first_metrics["retention_gate_accepted"] is True
        assert first["planner"]["status"] == "SHADOW_PLANNER_READY"
        assert first["planner"]["persisted"] is True
        assert first["planner"]["decision_authority"] == "NONE"
        assert first["planner"]["dispatch"] is False
        assert first["planner"]["native_body_consumed"] is False
        assert first["planner"]["native_body_weights_changed"] is False
        assert first["planner"]["representation"] == "NUMERIC_ROLE_READOUTS_NOT_NATIVE_BODY_LATENT"
        assert all(
            first["planner"]["candidate_readouts"][action][role]["status"] == "SHADOW_READOUT_ONLY"
            for action in world_model.ACTIONS
            for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL")
        )
        assert first["planner"]["memory_recall"]["status"] == "MEMORY_RECALL_SHADOW"
        first_sha = first["learning"]["checkpoint_sha256"]
        assert first["planner"]["checkpoint_sha256"] == first_sha
        assert read_world_planner_shadow(store, first_events[-1])["status"] == "SHADOW_PLANNER_READY"

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
        second_sha = second["learning"]["checkpoint_sha256"]
        assert second_sha != first_sha
        assert second["planner"]["status"] == "SHADOW_PLANNER_READY"

        restarted = WorldJEPAStoreConsumer(store, home / "world_jepa", learning_enabled=True)
        restored = restarted.restore()
        assert restored["status"] == "RESTORED"
        assert restored["checkpoint_sha256"] == second_sha
        rolled_back = restarted.rollback()
        assert rolled_back["status"] == "ROLLED_BACK"
        assert rolled_back["checkpoint_sha256"] == first_sha
        assert read_world_planner_shadow(store, second_events[-1])["status"] == "STALE_CHECKPOINT"
        assert read_world_planner_shadow(store, first_events[-1])["status"] == "SHADOW_PLANNER_READY"

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


def test_runtime_idle_tick_enqueues_world_jepa_into_normal_sleep_queue(tmp_path):
    home = tmp_path / "brain-runtime-queue"
    store, session = _make_store(home)
    try:
        event_id = _add_transitions(store, session, 0, 1)[0]
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        runtime = SimpleNamespace(
            store=store, home=home, cfg={},
            idle=lambda: True,
            guard=SimpleNamespace(update=lambda resources: "NORMAL"),
            resources=lambda: {},
            jobs=queue.Queue(maxsize=8),
            lock=threading.RLock(),
            wake=threading.Event(),
            cancel_event=threading.Event(),
            notice=lambda message: None,
        )
        sleep.r = runtime
        sleep.cycle = SimpleNamespace(policy=lambda: {
            "tick_seconds": 1.0, "enabled": False, "quiet_hours": None,
        })
        sleep.last_tick = -1e18
        sleep.last_resource = None
        sleep.monotonic = lambda: 1000.0
        sleep.clock = lambda: 1000.0
        with patch("v13.lab_native_cycle.maybe_schedule", return_value=None):
            queued = sleep.tick(force=True)
        assert queued and queued["action"] == "jepa_update"
        kind, payload, _, _ = runtime.jobs.get_nowait()
        assert kind == "sleep"
        assert payload["action"] == "jepa_update"
        assert payload["payload"] == {"event_id": event_id}
        runtime_source = (Path(__file__).resolve().parents[1] / "v13" / "runtime.py").read_text()
        assert "try:self.sleep.tick()" in runtime_source
        assert "elif kind=='sleep':self.sleep.job(payload)" in runtime_source
    finally:
        store.close()


def test_learning_gate_reenable_retries_shadowed_t8_event(tmp_path):
    home = tmp_path / "brain-jepa-gate-reenable"
    store, session = _make_store(home)
    try:
        first_events = _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        first = sleep._run_world_jepa(first_events[-1], limit=256)
        assert first["learning"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        first_cursor, _ = store.state("v14.world_jepa.sleep_cursor", None)
        assert first_cursor["last_learning_event_id"] == first_events[-1]

        store.set_state(PERMISSION_KEY, {
            "learning_enabled": False, "optimizer_permission": False,
            "steps": 40, "replay_mode": "uniform",
        })
        later_events = _add_transitions(store, session, 256, 64)
        shadow = sleep._run_world_jepa(later_events[-1], limit=256)
        assert shadow["learning"]["status"] == "OFF"
        shadow_cursor, _ = store.state("v14.world_jepa.sleep_cursor", None)
        assert shadow_cursor["last_event_id"] == later_events[-1]
        assert shadow_cursor["last_learning_event_id"] == first_events[-1]

        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        scheduled = sleep.schedule_world_jepa(later_events[-1])
        assert type(scheduled) is str and scheduled
        dispatched = sleep.scheduler.next(idle=True, resource_state="NORMAL", quiet=False)
        assert dispatched is not None and dispatched["id"] == scheduled
        result = sleep.job(dispatched)
        assert result["learning"]["learning_enabled"] is True
        assert result["learning"]["optimizer_permission"] is True
        assert result["learning"]["status"] not in {"OFF", "PENDING_OPTIMIZER_PERMISSION", "CANCELLED", "ERROR"}
        cursor, _ = store.state("v14.world_jepa.sleep_cursor", None)
        assert cursor["last_learning_event_id"] == later_events[-1]
    finally:
        store.close()


def test_cancelled_store_backed_world_jepa_fit_is_atomic_and_retryable(tmp_path):
    home = tmp_path / "brain-jepa-cancel"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        cancel_event = threading.Event()
        original = world_jepa.loss_grads

        def cancel_after_one_gradient(*args, **kwargs):
            result = original(*args, **kwargs)
            cancel_event.set()
            return result

        with patch("v13.world_jepa.loss_grads", side_effect=cancel_after_one_gradient):
            result = consume_after_commit(
                store, home, limit=256, cancel_event=cancel_event
            )
        assert result["status"] == "CANCELLED"
        state, _ = store.state("v14.world_jepa.store_consumer", None)
        assert state is None or state["scan_cursor"] == 0
        assert state is None or state["active"] is None
        assert not list((home / "world_jepa").glob("jepa-*.npz"))
    finally:
        store.close()
