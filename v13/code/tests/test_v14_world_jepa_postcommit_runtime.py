"""Normal Runtime -> idle Sleep scheduler -> persistent WorldJEPA/Planner integration.

All transitions are synthetic fixtures written through the real SQLite Store.
No native GGUF body, Android device, or Redmi behavior is claimed.
"""
from v13 import contracts, world_model
from v13.runtime import Runtime
from v13.scheduler import EventScheduler
from v13.sleep import SleepRuntime
from v13.store import Store
from v13.world_jepa_consumer import WorldJEPAStoreConsumer
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


def _runtime(store, home):
    runtime = object.__new__(Runtime)
    runtime.store = store
    runtime.home = home
    return runtime


def test_runtime_postcommit_requires_observed_outcome_and_keeps_gates_default_off(tmp_path):
    store, session = _make_store(tmp_path / "brain-default-off")
    try:
        runtime = _runtime(store, tmp_path / "brain-default-off")
        cancelled = _add_transitions(store, session, 0, 1, {0: "CANCELLED"})[0]
        skipped = runtime.v14_jepa_postcommit(cancelled)
        assert skipped["status"] == "CENSORED_OUTCOME_SKIPPED"
        assert store.state("v14.world_jepa.store_consumer", None)[0] is None

        observed = _add_transitions(store, session, 1, 1)[0]
        result = runtime.v14_jepa_postcommit(observed)
        assert result["status"] == "POSTCOMMIT_PROCESSED"
        assert result["learning"]["status"] == "OFF"
        assert result["planner"]["status"] == "NO_CHECKPOINT"
        assert result["decision_authority"] == "NONE"
        assert result["native_body_consumed"] is False
        assert result["native_body_weights_changed"] is False
        assert store.state(PERMISSION_KEY, None)[0] is None
        assert store.state("v14.world_jepa.store_consumer", None)[0] is None

        missing = store.event(session, "no committed action outcome")
        rejected = runtime.v14_jepa_postcommit(missing["event_id"])
        assert rejected["status"] == "NO_COMMITTED_OUTCOME"
    finally:
        store.close()


def test_sleep_scheduler_queues_only_authorized_or_checkpointed_observed_outcomes(tmp_path):
    store, session = _make_store(tmp_path / "brain-scheduler")
    try:
        runtime = _runtime(store, tmp_path / "brain-scheduler")
        sleep = object.__new__(SleepRuntime)
        sleep.r = runtime
        sleep.scheduler = EventScheduler(store, {})
        event_id = _add_transitions(store, session, 0, 1)[0]

        assert sleep.schedule_world_jepa(event_id) is None
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 40, "replay_mode": "uniform",
        })
        scheduled_id = sleep.schedule_world_jepa(event_id)
        assert type(scheduled_id) is str and scheduled_id
        pending = sleep.scheduler.pending()
        scheduled = next(item for item in pending if item["id"] == scheduled_id)
        assert scheduled["kind"] == "IDLE"
        assert scheduled["action"] == "jepa_update"
        assert scheduled["payload"] == {"event_id": event_id}
        assert sleep.schedule_world_jepa(event_id) is None

        censored = _add_transitions(store, session, 1, 1, {1: "OUTCOME_UNKNOWN"})[0]
        assert sleep.schedule_world_jepa(censored) is None
    finally:
        store.close()


def test_sleep_jepa_job_runs_postcommit_consumer_and_persists_scheduler_completion(tmp_path):
    store, _ = _make_store(tmp_path / "brain-scheduler-job")
    try:
        class FakeRuntime:
            def v14_jepa_postcommit(self, event_id, limit=64):
                return {
                    "status": "POSTCOMMIT_PROCESSED",
                    "event_id": event_id,
                    "learning": {"status": "OFF"},
                    "planner": {"status": "NO_CHECKPOINT"},
                }

        sleep = object.__new__(SleepRuntime)
        sleep.r = FakeRuntime()
        sleep.scheduler = EventScheduler(store, {})
        from v13.scheduler import ACTIONS
        ACTIONS.add("jepa_update")  # SleepRuntime.__init__ registers this fixed action in production.
        posted = sleep.scheduler.post(
            "IDLE", action="jepa_update", payload={"event_id": "evt-committed"},
            dedup="test-jepa-job",
        )
        dispatched = sleep.scheduler.next(idle=True, resource_state="NORMAL", quiet=False)
        assert dispatched is not None and dispatched["id"] == posted
        result = sleep.job(dispatched)
        assert result["status"] == "POSTCOMMIT_PROCESSED"
        history = sleep.scheduler.report()["history"]
        assert any(item["id"] == posted and item["status"] == "DONE" for item in history)
    finally:
        store.close()


def test_runtime_postcommit_updates_world_jepa_ema_replay_and_planner_with_restart_rollback(tmp_path):
    home = tmp_path / "brain-runtime-jepa"
    store, session = _make_store(home)
    try:
        first_events = _add_transitions(store, session, 0, 256)
        store.set_state(PERMISSION_KEY, {
            "learning_enabled": True, "optimizer_permission": True,
            "steps": 120, "replay_mode": "uniform",
        })
        runtime = _runtime(store, home)
        first = runtime.v14_jepa_postcommit(first_events[-1], limit=256)
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
        second = runtime.v14_jepa_postcommit(second_events[-1], limit=256)
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
    store, session = _make_store(tmp_path / "brain-censored-planner")
    try:
        event_id = _add_transitions(store, session, 0, 1, {0: "CANCELLED"})[0]
        rejected = consume_world_planner_shadow(store, event_id, home=tmp_path / "brain-censored-planner")
        assert rejected["status"] == "NO_COMMITTED_OUTCOME"
        assert store.state("v14.world_jepa.planner_shadow:" + event_id, None)[0] is None
    finally:
        store.close()
