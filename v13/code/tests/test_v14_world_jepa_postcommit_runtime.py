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


def _trace_world_jepa_consumer_calls(trace):
    from v13 import world_jepa_planner, world_jepa_runtime, world_jepa_temporal

    patches = []
    for module, name, label in (
        (world_jepa_runtime, "consume_after_commit", "base"),
        (world_jepa_temporal, "consume_temporal_after_commit", "temporal"),
        (world_jepa_planner, "consume_world_planner_shadow", "planner"),
    ):
        original = getattr(module, name)

        def wrapped(*args, _original=original, _label=label, **kwargs):
            trace.append(_label + ":START")
            try:
                result = _original(*args, **kwargs)
            except Exception as exc:
                trace.append(_label + ":RAISED:" + type(exc).__name__ + ":" + str(exc)[:240])
                raise
            status = result.get("status") if isinstance(result, dict) else type(result).__name__
            trace.append(_label + ":" + str(status))
            return result

        setattr(module, name, wrapped)
        patches.append((module, name, original))

    def restore():
        for module, name, original in patches:
            setattr(module, name, original)

    return restore

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


def _add_temporal_cohort(store, label, start, session_count):
    """Build independent four-event sessions for strict temporal holdouts."""
    event_ids = []
    for offset in range(session_count):
        session = store.new_session(f"{label}-{offset:03d}")
        event_ids.extend(_add_transitions(store, session, start + offset * 4, 4))
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


def test_sleep_jepa_job_requeues_when_only_temporal_page_has_more_rows(tmp_path):
    home = tmp_path / "brain-temporal-continuation"
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
            "learning": {"status": "NO_NEW_TRANSITIONS", "has_more": False},
            "temporal": {
                "status": "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA",
                "has_more": True,
            },
            "planner": {"status": "NO_CHECKPOINT"},
        }
        posted = sleep.scheduler.post(
            "IDLE", action="jepa_update", payload={"event_id": event_id},
            dedup="v14-world-jepa",
        )
        dispatched = sleep.scheduler.next(idle=True, resource_state="NORMAL", quiet=False)
        assert dispatched is not None and dispatched["id"] == posted
        result = sleep.job(dispatched)
        assert result["learning"]["has_more"] is False
        assert result["temporal"]["has_more"] is True
        assert result["learning_status"] == "NO_NEW_TRANSITIONS"
        assert result["temporal_status"] == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA"
        assert result["planner_status"] == "NO_CHECKPOINT"
        assert result["learning_has_more"] is False
        assert result["temporal_has_more"] is True
        assert result["continuation_reason"] == "TEMPORAL_PAGE"
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
        first_events = _add_temporal_cohort(store, "first", 0, 64)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        trace = []
        restore_trace = _trace_world_jepa_consumer_calls(trace)
        first = sleep._run_world_jepa(first_events[-1], limit=256)
        assert first["status"] == "POSTCOMMIT_PROCESSED", {
            "error": first.get("error"), "trace": trace,
            "learning": first.get("learning", {}).get("status"),
            "temporal": first.get("temporal", {}).get("status"),
            "planner": first.get("planner", {}).get("status"),
        }
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

        second_events = _add_temporal_cohort(store, "second", 256, 8)
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
        if 'restore_trace' in locals():
            restore_trace()
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
        event_ids = _add_temporal_cohort(store, "events", 0, 64)
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
        first_events = _add_temporal_cohort(store, "first", 0, 64)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        sleep = _sleep(store, home)
        trace = []
        restore_trace = _trace_world_jepa_consumer_calls(trace)
        first = sleep._run_world_jepa(first_events[-1], limit=256)
        assert "learning" in first, {
            "error": first.get("error"), "trace": trace,
            "learning": first.get("learning", {}).get("status"),
            "temporal": first.get("temporal", {}).get("status"),
            "planner": first.get("planner", {}).get("status"),
        }
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
        if 'restore_trace' in locals():
            restore_trace()
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
        def action_is_final(event_id=turn_event_id):
            row = runtime.store.one(
                "SELECT status,outcome FROM actions WHERE event_id=?", (event_id,)
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

        # Feed the learner 32 source-bound outcomes produced by the real Runtime
        # worker, spread over eight independent sessions. Do not move the learner
        # cursor past these actions: they must be part of the trained cohort.
        runtime_action_ids = []
        runtime_session_ids = []
        for session_index in range(8):
            if session_index:
                runtime.session = runtime.store.new_session(
                    f"real-runtime-jepa-{session_index:02d}"
                )
            runtime_session_ids.append(runtime.session)
            for turn_index in range(4):
                if session_index == 0 and turn_index == 0:
                    event_id = turn_event_id
                else:
                    event_id = runtime.submit(
                        f"Copy exactly: runtime-jepa-{session_index:02d}-{turn_index:02d}"
                    )
                assert _wait_until(lambda event_id=event_id: action_is_final(event_id))
                assert _wait_until(runtime.idle)
                action = runtime.store.one(
                    "SELECT id,rowid AS scan_seq,status,outcome FROM actions WHERE event_id=?",
                    (event_id,),
                )
                assert action is not None and action["status"] == "FINAL" and action["outcome"] is not None
                runtime_action_ids.append(action["id"])
        assert len(runtime_action_ids) == 32 and len(set(runtime_action_ids)) == 32

        # Prove the Runtime-produced rows have the full T8 source / CorollaryCopy /
        # ActionOutcome chain before they enter JEPA training.
        from v13.world_jepa_store_authority import verify_committed_transitions
        verified_runtime, rejected_runtime = verify_committed_transitions(
            runtime.store, limit=256
        )
        verified_runtime_ids = {item.action_id for item in verified_runtime}
        assert set(runtime_action_ids) <= verified_runtime_ids, {
            "runtime_actions": len(runtime_action_ids),
            "verified_runtime_actions": len(verified_runtime_ids),
            "rejected": rejected_runtime,
        }

        # Add source-disjoint sessions covering every action route. These supply
        # balanced training/holdout support and the negative controls; the actual
        # Runtime outcomes remain in the same persisted learning cohort.
        _add_temporal_cohort(runtime.store, "synthetic-postcommit", 0, 48)
        latest = runtime.store.one(
            "SELECT event_id FROM actions WHERE outcome IS NOT NULL "
            "AND status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED') "
            "ORDER BY created DESC,id DESC LIMIT 1"
        )["event_id"]
        target_scan_seq = runtime.store.one(
            "SELECT rowid AS scan_seq FROM actions WHERE event_id=?", (latest,)
        )["scan_seq"]
        # Install the observer before opening the local lab gates. The real
        # Runtime worker polls SleepRuntime while idle; enabling first can let
        # an unobserved update consume the cohort before this test captures it.
        original_run = runtime.sleep._run_world_jepa
        captured_runs = {}

        def capture_run(event_id, limit=64):
            result = original_run(event_id, limit=256)
            captured_runs.setdefault(event_id, []).append(result)
            return result

        runtime.sleep._run_world_jepa = capture_run
        runtime.sleep.last_tick = -1e18
        runtime.store.set_state(PERMISSION_KEY, {
            "learning_enabled": True,
            "optimizer_permission": True,
            "steps": 120,
            "replay_mode": "uniform",
        })
        runtime.wake.set()

        def learned_and_planned():
            state, _ = runtime.store.state("v14.world_jepa.store_consumer", None)
            temporal_state, _ = runtime.store.state("v14.world_jepa.temporal_consumer", None)
            cursor, _ = runtime.store.state("v14.world_jepa.sleep_cursor", None)
            active = state.get("active") if type(state) is dict else None
            temporal_active = temporal_state.get("active") if type(temporal_state) is dict else None
            runs = captured_runs.get(latest, [])
            learned = any(
                type(item) is dict
                and item.get("learning", {}).get("status") == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
                and item.get("temporal", {}).get("status") == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA"
                and item.get("scan_complete") is True
                and item.get("learning_scan_reached_target") is True
                and item.get("temporal_scan_reached_target") is True
                for item in runs
            )
            return (
                learned
                and type(active) is dict
                and type(temporal_active) is dict
                and type(cursor) is dict
                and cursor.get("last_learning_event_id") == latest
                and cursor.get("last_planner_event_id") == latest
            )

        ready = _wait_until(learned_and_planned)
        state, _ = runtime.store.state("v14.world_jepa.store_consumer", None)
        temporal_state, _ = runtime.store.state("v14.world_jepa.temporal_consumer", None)
        cursor, _ = runtime.store.state("v14.world_jepa.sleep_cursor", None)
        runs = captured_runs.get(latest, [])
        summaries = [{
            "status": item.get("learning", {}).get("status"),
            "temporal_status": item.get("temporal", {}).get("status"),
            "verified_receipts": item.get("learning", {}).get("verified_receipts"),
            "temporal_verified_receipts": item.get("temporal", {}).get("verified_receipts"),
            "rejected_receipts": item.get("learning", {}).get("rejected_receipts"),
            "scanned_rows": item.get("learning", {}).get("scanned_rows"),
            "learning_scan_cursor": item.get("learning", {}).get("scan_cursor"),
            "temporal_scan_cursor": item.get("temporal", {}).get("scan_cursor"),
            "target_scan_seq": item.get("target_scan_seq"),
            "scan_complete": item.get("scan_complete"),
            "learning_scan_reached_target": item.get("learning_scan_reached_target"),
            "temporal_scan_reached_target": item.get("temporal_scan_reached_target"),
            "has_more": item.get("learning", {}).get("has_more"),
            "temporal_has_more": item.get("temporal", {}).get("has_more"),
            "pending_rows": item.get("learning", {}).get("pending_rows"),
            "planner_status": item.get("planner", {}).get("status"),
        } for item in runs]
        assert ready, {
            "runs_for_latest": summaries,
            "store_scan_cursor": state.get("scan_cursor") if type(state) is dict else None,
            "sleep_cursor": cursor,
            "target_scan_seq": target_scan_seq,
            "runtime_action_count": len(runtime_action_ids),
        }
        active = state["active"]
        checkpoint_sha = active["checkpoint_sha256"]
        fit_steps = active.get("fit_steps")
        assert type(checkpoint_sha) is str and len(checkpoint_sha) == 64
        worker_result = next(
            item for item in runs
            if item.get("learning", {}).get("status") == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
            and item.get("temporal", {}).get("status") == "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA"
        )
        learning = worker_result.get("learning", {})
        metrics = learning.get("metrics", {})
        temporal = worker_result.get("temporal", {})
        temporal_metrics = temporal.get("metrics", {})
        temporal_checkpoint_sha = temporal.get("checkpoint_sha256")
        assert worker_result.get("event_id") == latest
        assert metrics.get("parameter_delta_norm", 0) > 0
        assert metrics.get("ema_target_delta_norm", 0) > 0
        assert metrics.get("holdout_loss_after", float("inf")) < metrics.get("holdout_loss_before", float("-inf"))
        assert metrics.get("train_holdout_source_disjoint") is True
        assert metrics.get("negative_controls_separated") is True
        assert metrics.get("retention_gate_accepted") is True

        # The temporal JEPA update must be numeric, persistent and source-disjoint;
        # the same checkpoint must include real Runtime ActionOutcome rows.
        assert temporal.get("checkpoint_committed") is True
        assert temporal.get("optimizer_state_persisted") is True
        assert temporal.get("native_body_weights_changed") is False
        assert temporal.get("decision_authority") == "NONE"
        assert type(temporal_checkpoint_sha) is str and len(temporal_checkpoint_sha) == 64
        assert temporal_state["active"]["checkpoint_sha256"] == temporal_checkpoint_sha
        assert temporal_state["scan_cursor"] >= target_scan_seq
        assert temporal_metrics.get("parameter_delta_norm", 0) > 0
        assert temporal_metrics.get("encoder_delta_norm", 0) > 0
        assert temporal_metrics.get("predictor_delta_norm", 0) > 0
        assert temporal_metrics.get("ema_target_delta_norm", 0) > 0
        assert temporal_metrics.get("holdout_mse_after", float("inf")) < temporal_metrics.get("holdout_mse_before", float("-inf"))
        assert temporal_metrics.get("shuffled_action_mse", float("-inf")) > temporal_metrics.get("holdout_mse_after", float("inf"))
        assert temporal_metrics.get("shuffled_target_mse", float("-inf")) > temporal_metrics.get("holdout_mse_after", float("inf"))
        assert temporal_metrics.get("source_disjoint") is True
        assert temporal_metrics.get("retention_pass") is True
        assert temporal_metrics.get("optimizer_steps", 0) > 0
        assert temporal_metrics.get("steps_this_update", 0) > 0
        temporal_rows = {
            row["action_id"] for row in temporal_state["active"]["experience_rows"]
        }
        assert set(runtime_action_ids) <= temporal_rows
        from v13.world_jepa_temporal import build_temporal_windows, _split_windows
        reconstructed_windows = build_temporal_windows(
            runtime.store, temporal_state["active"]["experience_rows"]
        )
        reconstructed_train, reconstructed_holdout, reconstructed_split = _split_windows(
            reconstructed_windows
        )
        train_window_ids = {window["window_id"] for window in reconstructed_train}
        holdout_window_ids = {window["window_id"] for window in reconstructed_holdout}
        assert train_window_ids == set(temporal_state["active"]["train_window_ids"])
        assert holdout_window_ids == set(temporal_state["active"]["holdout_window_ids"])
        assert train_window_ids.isdisjoint(holdout_window_ids)
        fit_target_action_ids = {
            window["action_ids"][-1] for window in reconstructed_train
        }
        assert set(runtime_action_ids) & fit_target_action_ids, {
            "runtime_action_count": len(runtime_action_ids),
            "fit_runtime_target_count": len(set(runtime_action_ids) & fit_target_action_ids),
            "train_sessions": temporal_metrics.get("train_session_count"),
            "holdout_sessions": temporal_metrics.get("holdout_session_count"),
        }
        assert reconstructed_split["source_disjoint"] is True

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
        temporal_telemetry = runtime.store.rows(
            "SELECT event_id,metrics FROM telemetry WHERE kind='v14_world_jepa_temporal_postcommit' ORDER BY id"
        )
        decoded_temporal = [
            {
                "event_id": row["event_id"],
                **(json.loads(row["metrics"]) if isinstance(row["metrics"], str) else row["metrics"]),
            }
            for row in temporal_telemetry
        ]
        matching_temporal = [row for row in decoded_temporal if row.get("event_id") == latest]
        assert any(
            row.get("status") == "PASS"
            and row.get("component") == "world_predictor"
            and row.get("mode") == "shadow"
            and row.get("sha256") == temporal_checkpoint_sha
            and row.get("optimizer_steps", 0) > 0
            and row.get("target_changed") is True
            and row.get("loss_after", float("inf")) < row.get("loss_before", float("-inf"))
            and row.get("decision") == "none"
            and row.get("native_body_parameters_modified") is False
            for row in matching_temporal
        ), matching_temporal
        assert "worker-jepa-lifecycle" not in repr(state)
        assert "worker-jepa-lifecycle" not in repr(temporal_state)
        assert "runtime-jepa-" not in repr(temporal_state)
        assert "worker-jepa-lifecycle" not in repr(telemetry)
        assert "worker-jepa-lifecycle" not in repr(temporal_telemetry)

        # The numeric episodic recall must reach the actual B1/B2 prompt consumer.
        # The fake runner isolates prompt delivery; all recalled T8 rows and
        # SourceRefs below are read from the real Runtime SQLite Store.
        receiver_text = "The verified action history is ready. Estimate the next action duration."
        receiver_event = runtime.store.event(runtime.session, receiver_text)
        seen_queries = {}
        original_pool_get = runtime.pool.get

        class CaptureReceiverRunner:
            def __init__(self, role):
                self.role = role
                self.last_metrics = {"status": "FINAL", "duration_s": 0.0}

            def generate(self, messages, cancel, deadline, max_tokens, schema):
                query = json.loads(messages[1]["content"])
                seen_queries[self.role] = query
                return iter([json.dumps({
                    "summary": "A source-quoted next-action estimate.",
                    "quotes": ["verified action history"],
                    "uncertainty": "low",
                    "needs_reentry": False,
                })])

        runtime.pool.get = lambda role: CaptureReceiverRunner(role)
        _, temporal_recall_state_version = runtime.store.state("v14.world_jepa.temporal_consumer", None)
        try:
            receiver_specs = (
                ("B1_DETAIL", 2, "DURATION+OUTPUT_CHARS"),
                ("B2_GIST", 3, "P_FINAL_NOT_CORRECTNESS"),
            )
            for role, expected_history, expected_target in receiver_specs:
                delivered = runtime.cognition.offer(
                    role, receiver_event, 0, time.monotonic() + 30.0
                )
                query = seen_queries[role]
                body_state = query.get("body_state")
                assert type(body_state) is dict, (role, query.keys())
                temporal_view = body_state.get("world_jepa_temporal")
                assert type(temporal_view) is dict, (role, body_state)
                assert temporal_view.get("status") == "SHADOW_READOUT_ONLY"
                assert temporal_view.get("history_length") == expected_history
                assert temporal_view.get("target") == expected_target
                assert temporal_view.get("rows")
                episodic_view = temporal_view.get("episodic")
                assert type(episodic_view) is list and 1 <= len(episodic_view) <= 2
                assert all(
                    type(row) is list and len(row) == 6
                    and row[0] in world_model.ACTIONS
                    and type(row[1]) in (int, float)
                    and type(row[2]) in (int, float)
                    and type(row[3]) is bool
                    and type(row[4]) is int
                    and type(row[5]) is str and len(row[5]) == 8
                    for row in episodic_view
                )
                assert "runtime-jepa-" not in repr(episodic_view)
                assert "synthetic-postcommit-source-" not in repr(episodic_view)

                query_row = runtime.store.one(
                    "SELECT payload FROM packets WHERE kind='QueryPacket' AND event_id=? "
                    "ORDER BY rowid DESC LIMIT 1",
                    (receiver_event["event_id"],),
                )
                assert query_row is not None
                query_packet = json.loads(query_row["payload"])
                body_state_ref = query_packet["bodyview"]["body_state_ref"]
                assert body_state_ref in query_packet["provenance"]
                body_state_raw = runtime.store.read_source(body_state_ref)
                assert "runtime-jepa-" not in body_state_raw
                assert "synthetic-postcommit-source-" not in body_state_raw
                body_state_payload = json.loads(body_state_raw)
                receiver_audit = body_state_payload["temporal_world_jepa_audit"]
                episodic_audit = receiver_audit["episodic_recall"]
                assert episodic_audit["status"] in {
                    "EPISODIC_RECALL_SHADOW", "EPISODIC_RECALL_PARTIAL",
                }
                assert episodic_audit["train_split_only"] is True
                assert episodic_audit["heldout_used"] is False
                assert episodic_audit["source_disjoint_from_query"] is True
                assert episodic_audit["text_disclosed"] is False
                assert episodic_audit["decision_authority"] == "NONE"
                assert episodic_audit["native_memory_consumed"] is False
                assert episodic_audit["native_body_consumed"] is False
                assert episodic_audit["native_body_weights_changed"] is False
                query_history_ids = set(episodic_audit["query_history_action_ids"])
                query_history_sources = set(episodic_audit["query_history_source_sha256s"])
                holdout_ids = set(temporal_state["active"]["holdout_window_ids"])
                train_ids = set(temporal_state["active"]["train_window_ids"])
                audit_items = episodic_audit["items"]
                assert audit_items
                assert len(audit_items) >= len(episodic_view)
                for item in audit_items:
                    assert item["window_id"] in train_ids
                    assert item["window_id"] not in holdout_ids
                    assert len(item["window_action_ids"]) == expected_history + 1
                    assert not query_history_ids.intersection(item["window_action_ids"])
                    assert not query_history_sources.intersection(item["window_source_sha256s"])
                    assert item["source_sha256"] == item["source_ref"]["sha256"]
                    assert item["source_ref"] == item["window_source_refs"][-1]
                    assert len(item["window_source_refs"]) == expected_history + 1
                    for source_ref in item["window_source_refs"]:
                        assert type(runtime.store.read_source(source_ref)) is str
                assert len(delivered["evidence_refs"]) == 1
                assert runtime.store.read_source(delivered["evidence_refs"][0]) == "verified action history"
            _, temporal_recall_state_version_after = runtime.store.state("v14.world_jepa.temporal_consumer", None)
            assert temporal_recall_state_version_after == temporal_recall_state_version
        finally:
            runtime.pool.get = original_pool_get
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
            and (reopened.store.state("v14.world_jepa.temporal_consumer", None)[0] or {})
            .get("active", {}).get("checkpoint_sha256") == temporal_checkpoint_sha
        ))
        time.sleep(0.5)
        restored, _ = reopened.store.state("v14.world_jepa.store_consumer", None)
        restored_temporal, _ = reopened.store.state("v14.world_jepa.temporal_consumer", None)
        assert restored["active"]["checkpoint_sha256"] == checkpoint_sha
        assert restored["active"].get("fit_steps") == fit_steps
        assert restored_temporal["active"]["checkpoint_sha256"] == temporal_checkpoint_sha
        assert restored_temporal["active"].get("fit_steps") == temporal_metrics.get("optimizer_steps")
        assert restored_temporal["scan_cursor"] >= target_scan_seq
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
        event_ids = _add_temporal_cohort(store, "events", 0, 64)
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
        event_ids = _add_temporal_cohort(store, "events", 0, 64)
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


def test_temporal_episodic_recall_fails_closed_without_checkpoint(tmp_path):
    home = tmp_path / "temporal-episodic-no-checkpoint"
    store, session = _make_store(home)
    try:
        from v13.world_jepa_temporal import TemporalWorldJEPAStoreConsumer

        learner = TemporalWorldJEPAStoreConsumer(store)
        result = learner.episodic_recall(
            session, history_length=2, limit=len(world_model.ACTIONS), nonblocking=True,
        )
        assert result["status"] == "NO_CHECKPOINT"
        assert result["items"] == []
        assert result["decision_authority"] == "NONE"
        assert result["native_memory_consumed"] is False
    finally:
        store.close()
