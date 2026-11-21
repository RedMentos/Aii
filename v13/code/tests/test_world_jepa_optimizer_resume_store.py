"""Production Store-backed optimizer-resume vs reset control.

This exercises the deployable V13 WorldJEPA consumer, its real SQLite
ActionOutcome/T8 authority and private checkpoint format. The data are
synthetic test experiences; this is not Redmi, native GGUF, or user-data proof.
"""
import copy
import math
import shutil

from v13 import contracts, world_jepa_optimizer_audit as optimizer_audit, world_model
from v13.store import Store
from v13.world_jepa_consumer import WorldJEPAStoreConsumer

STATE_KEY = "v14.world_jepa.store_consumer"


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 production optimizer-resume ablation")
    return store, session


def _add_transitions(store, session, start, count):
    action_ids = []
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        source = f"synthetic-user-content-{index:04d}" + ("x" * (index % 29))
        event = store.event(session, source)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        action_index = index % len(actions)
        route = actions[action_index]
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
            forecast={"input_chars": len(source), "resource_state": "NORMAL"},
        )
        store.finish_action(
            action_id,
            "FAILED" if index % 5 == 0 else "FINAL",
            {
                "action_duration_s": 0.15 + action_index * 0.65 + (index % 13) * 0.02,
                "characters": 9 + action_index * 24 + (index % 23) * 0.75,
            },
        )
        action_ids.append(action_id)
    return action_ids


class _CapturingConsumer(WorldJEPAStoreConsumer):
    def __init__(self, *args, **kwargs):
        self.loaded_model = None
        self.optimizer_before = None
        super().__init__(*args, **kwargs)

    def _load_model(self, record):
        model = super()._load_model(record)
        self.before_model = copy.deepcopy(model)
        self.before_audit = optimizer_audit.audit_model(model)
        self.loaded_model = model
        self.optimizer_before = self.before_audit["optimizer_main_step"]
        return model


class _ResetMomentsConsumer(_CapturingConsumer):
    """Matched control: retain model/EMA weights but discard saved optimizer state."""

    def _load_model(self, record):
        model = super()._load_model(record)
        del model._training_state
        return model


def _metrics(result):
    return result.get("metrics", result)


def _assert_candidate_metrics(result):
    assert result["status"] in {
        "UPDATED_EXPERIMENTAL_WORLD_JEPA",
        "UTILITY_GATE_REJECTED",
    }, result
    metrics = _metrics(result)
    for key in (
        "holdout_loss_before", "holdout_loss_after",
        "shuffled_action_holdout_loss", "zero_action_holdout_loss",
        "parameter_delta_norm", "ema_target_delta_norm",
        "fit_steps_before", "fit_steps_after",
    ):
        assert key in metrics, (key, result)
    for key in (
        "holdout_loss_before", "holdout_loss_after",
        "shuffled_action_holdout_loss", "zero_action_holdout_loss",
        "parameter_delta_norm", "ema_target_delta_norm",
    ):
        assert math.isfinite(float(metrics[key])), (key, metrics[key])
    assert metrics["parameter_delta_norm"] > 0
    assert metrics["ema_target_delta_norm"] > 0
    assert metrics["fit_steps_after"] > metrics["fit_steps_before"]
    if result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
        assert metrics["holdout_improved"] is True
        assert metrics["negative_controls_separated"] is True
        assert metrics["old_holdout_retained"] is True
        assert metrics["optimizer_moments_persisted"] is True
    else:
        # The production utility/retention gate must reject a candidate that
        # fails any of the measured controls; it must not publish its checkpoint.
        assert result["utility_gate_accepted"] is False
        assert not (
            result["holdout_improved"]
            and result["negative_controls_separated"]
            and result["old_holdout_retained"]
        )


def test_production_checkpoint_resumes_adam_and_reset_control_is_distinct(tmp_path):
    persistent_home = tmp_path / "persistent"
    control_home = tmp_path / "reset-control"
    store, session = _make_store(persistent_home)
    control_store = None
    try:
        _add_transitions(store, session, 0, 256)
        consumer = WorldJEPAStoreConsumer(
            store, persistent_home / "world_jepa",
            learning_enabled=True, seed=13, ensemble=2,
        )
        first = consumer.update(limit=256, steps=120, optimizer_permission=True)
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA", first
        first_metrics = first["metrics"]
        first_sha = first["checkpoint_sha256"]
        assert first_metrics["optimizer_moments_persisted"] is True
        assert first_metrics["optimizer_state_bootstrapped"] is False
        assert first_metrics["train_holdout_source_sha256_disjoint"] is True
        assert first_metrics["negative_controls_separated"] is True

        first_record = store.state(STATE_KEY, None)[0]["active"]
        first_audit = optimizer_audit.audit_checkpoint(
            persistent_home / "world_jepa" / first_record["checkpoint"],
            first_record["source_sha256"], first_sha,
        )
        assert first_audit["checkpoint_verified"] is True
        assert first_audit["optimizer_state_present"] is True
        assert first_audit["optimizer_main_step"] == 120
        assert first_audit["optimizer_bootstrap_steps"] == [60]

        # Clone the exact SQLite database, source blobs and private checkpoint.
        # Both arms therefore start from identical model/EMA/Adam bytes.
        store.close()
        store = None
        control_home.mkdir(parents=True)
        shutil.copytree(persistent_home / "data", control_home / "data")
        shutil.copytree(persistent_home / "world_jepa", control_home / "world_jepa")
        store = Store(persistent_home)
        control_store = Store(control_home)

        # Add one new cohort once, then clone its exact Store rows/blobs into
        # the control arm so only optimizer-state handling differs.
        _add_transitions(store, session, 256, 64)
        store.close()
        store = None
        control_store.close()
        control_store = None
        shutil.rmtree(control_home / "data")
        shutil.copytree(persistent_home / "data", control_home / "data")
        store = Store(persistent_home)
        control_store = Store(control_home)

        persistent_state, _ = store.state(STATE_KEY, None)
        reset_state, _ = control_store.state(STATE_KEY, None)
        assert persistent_state["active"]["checkpoint_sha256"] == first_sha
        assert reset_state["active"]["checkpoint_sha256"] == first_sha
        assert persistent_state["active"]["checkpoint_sha256"] == reset_state["active"]["checkpoint_sha256"]

        persistent = _CapturingConsumer(
            store, persistent_home / "world_jepa",
            learning_enabled=True, seed=13, ensemble=2,
        )
        reset = _ResetMomentsConsumer(
            control_store, control_home / "world_jepa",
            learning_enabled=True, seed=13, ensemble=2,
        )
        persistent_result = persistent.update(
            limit=320, steps=120, optimizer_permission=True, replay_mode="uniform"
        )
        reset_result = reset.update(
            limit=320, steps=120, optimizer_permission=True, replay_mode="uniform"
        )

        _assert_candidate_metrics(persistent_result)
        _assert_candidate_metrics(reset_result)
        assert persistent.optimizer_before == 120
        assert reset.optimizer_before == 120

        persistent_audit = optimizer_audit.audit_model(persistent.loaded_model)
        reset_audit = optimizer_audit.audit_model(reset.loaded_model)
        persistent_delta = optimizer_audit.compare_models(
            persistent.before_model, persistent.loaded_model
        )
        reset_delta = optimizer_audit.compare_models(
            reset.before_model, reset.loaded_model
        )
        assert persistent.before_audit["parameter_sha256"] == reset.before_audit["parameter_sha256"]
        assert persistent.before_audit["ema_target_sha256"] == reset.before_audit["ema_target_sha256"]
        assert persistent.before_audit["optimizer_state_sha256"] == reset.before_audit["optimizer_state_sha256"]
        assert persistent_audit["optimizer_origin"] == "FRESH"
        assert persistent_audit["optimizer_main_step"] == 240
        assert persistent_audit["optimizer_bootstrap_steps"] == [120]
        assert reset_audit["optimizer_origin"] == "BOOTSTRAPPED_FROM_INFERENCE_ONLY"
        assert reset_audit["optimizer_main_step"] == 120
        assert reset_audit["optimizer_bootstrap_steps"] == [60]
        for delta in (persistent_delta, reset_delta):
            assert delta["parameter_delta_norm"] > 0
            assert delta["ema_target_delta_norm"] > 0
            assert delta["optimizer_moment_delta_norm"] > 0
        assert persistent_audit["optimizer_state_sha256"] != persistent.before_audit["optimizer_state_sha256"]
        assert reset_audit["optimizer_state_sha256"] != reset.before_audit["optimizer_state_sha256"]

        # Both arms saw the same new T8 cohort and equal gradient-step budgets.
        # The test records utility/retention outcomes; it does not assume that
        # persistent moments must win or relax the production acceptance gate.
        for result in (persistent_result, reset_result):
            metrics = _metrics(result)
            assert metrics["fit_steps_before"] == 120
            assert metrics["fit_steps_after"] == 240
            assert metrics["replay_mode"] == "uniform"
            assert metrics["replay_rows"] > 0
            assert metrics["old_holdout_loss_before"] is not None
            assert math.isfinite(float(metrics["old_holdout_retention_delta"]))

        for active_store, result in ((store, persistent_result), (control_store, reset_result)):
            state, _ = active_store.state(STATE_KEY, None)
            if result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
                assert state["active"]["checkpoint_sha256"] != first_sha
                assert state["active"]["metrics"]["optimizer_moments_persisted"] is True
            else:
                assert state["active"]["checkpoint_sha256"] == first_sha
    finally:
        if store is not None:
            store.close()
        if control_store is not None:
            control_store.close()
