"""Production-Store A→B→A replay/retention experiment for the WorldJEPA runtime adapter.

This uses committed SQLite T8 ActionSelection/ActionOutcome rows and the same
consume_after_commit facade called by SleepRuntime. Data are synthetic; this is
not a Redmi or native GGUF/B1/B2 weight proof.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil

import numpy as np
import pytest

from v13 import (
    contracts,
    world_jepa,
    world_jepa_consumer,
    world_jepa_optimizer_audit,
    world_jepa_replay,
    world_jepa_drift,
    world_jepa_runtime,
    world_model,
)
from v13.store import Store
from v13.memory import Memory
from v13.world_jepa_store_authority import verify_committed_transition_page
from v13.world_jepa_planner import consume_world_planner_shadow

STATE_KEY = "v14.world_jepa.store_consumer"
PERMISSION_KEY = world_jepa_runtime.PERMISSION_KEY
DEFAULT_PERMISSIONS = dict(world_jepa_runtime.DEFAULT_PERMISSIONS)
DRIFT_CONFIG = {
    "enabled": True,
    "dual_lr": 0.03,
    "lambda_init": 1.0,
    "lambda_max": 100.0,
    "deadzone": 0.05,
}
ARMS = (
    ("uniform", "full", False, False),
    ("none", "full", False, False),
    ("uniform_budget", "full", False, False),
    ("session_contiguous", "full", False, False),
    ("uniform", "predictor_only", False, False),
    ("none", "predictor_only", False, False),
    ("uniform_budget", "predictor_only", False, False),
    ("session_contiguous", "predictor_only", False, False),
    ("uniform_budget", "full", True, False),
    ("uniform_budget", "predictor_only", True, False),
    ("uniform_budget", "predictor_only", True, True),
    ("session_contiguous", "full", True, True),
    ("on_demand_conflict", "full", True, True),
    ("on_demand_conflict", "predictor_only", True, True),
    ("on_demand_loss", "full", False, False),
    ("on_demand_loss", "full", False, True),
    ("on_demand_loss", "predictor_only", False, False),
    ("on_demand_loss", "predictor_only", False, True),
)
DATA_SEEDS = (13, 19, 43)
A1_COUNT = 256
SHIFT_COUNT = 256
A1_STEPS = 120
SHIFT_STEPS = 120


def test_prior_guard_reference_batch_validation_is_fail_closed_and_atomic():
    rng = np.random.default_rng(73)
    x = rng.normal(size=(8, 4))
    actions = np.eye(2, dtype=np.float64)[np.arange(8) % 2]
    x2 = 0.7 * x + 0.1 * rng.normal(size=(8, 4))
    model = world_jepa.WorldJEPA(seed=73, ensemble=1)
    model.fit(x, actions, x2, steps=2, log_every=1)
    before = world_jepa_consumer._parameter_snapshot(model)
    training_state = model._training_state
    fit_steps = model._fit_steps

    with pytest.raises(ValueError, match="Replay reference batch shape"):
        model.partial_fit(
            x, actions, x2, steps=1, log_every=1,
            allow_optimizer_bootstrap=True, train_encoder=True,
            replay_start=4, replay_cohort_ranges=((4, 6), (6, 8)),
            replay_reference_batches=(
                (x[:1], actions[:1], x2[:1]),
                (x[:2], actions[:2], x2[:2]),
            ),
        )

    after = world_jepa_consumer._parameter_snapshot(model)
    for group in ("enc", "tgt"):
        for key in before[group]:
            assert np.array_equal(before[group][key], after[group][key])
    for index, predictor in enumerate(before["preds"]):
        for key in predictor:
            assert np.array_equal(predictor[key], after["preds"][index][key])
    assert model._training_state is training_state
    assert model._fit_steps == fit_steps


def test_parameter_interpolation_scales_all_worldjepa_groups_without_resetting_optimizer():
    rng = np.random.default_rng(71)
    x = rng.normal(size=(64, 4))
    actions = rng.normal(size=(64, 2))
    x2 = 0.65 * x + 0.2 * rng.normal(size=(64, 4))
    model = world_jepa.WorldJEPA(seed=71, ensemble=1)
    model.fit(x, actions, x2, steps=8, log_every=4)

    before = world_jepa_consumer._parameter_snapshot(model)
    after = copy.deepcopy(before)
    for group in ("enc", "tgt"):
        for value in after[group].values():
            value[...] += 0.4
    for predictor in after["preds"]:
        for value in predictor.values():
            value[...] += 0.4
    optimizer_state = model._training_state

    world_jepa_consumer._apply_parameter_interpolation(model, before, after, 0.25)
    actual = world_jepa_consumer._parameter_snapshot(model)
    for group in ("enc", "tgt"):
        for key in before[group]:
            assert np.allclose(
                actual[group][key], before[group][key] + 0.1,
                rtol=0.0, atol=1e-12,
            )
    for index, predictor in enumerate(before["preds"]):
        for key in predictor:
            assert np.allclose(
                actual["preds"][index][key], predictor[key] + 0.1,
                rtol=0.0, atol=1e-12,
            )
    assert model._training_state is optimizer_state


def test_stable_drift_controller_calibrates_groups_and_updates_dual():
    params = {
        "encoder": {"eW": np.array([1.0, 2.0])},
        "predictor": {"pW": np.array([2.0, 1.0])},
        "inverse": {"iW": np.array([0.5])},
    }
    prepared = world_jepa_drift.prepare_task(
        world_jepa_drift.default_state(), DRIFT_CONFIG, params,
        has_prior_training=False,
    )
    for group in params.values():
        for value in group.values():
            value[0] += 0.1
    calibrated = world_jepa_drift.finish_task(
        prepared, params, steps=12,
        update_norms={name: [0.001] * 12 for name in params},
    )
    assert all(calibrated["groups"][name]["budget_sq"] > 0 for name in params)
    assert all(calibrated["groups"][name]["task_count"] == 1 for name in params)
    assert all(calibrated["groups"][name]["budget_method"] == "STABLE_TASK1_P75_ROLLING5" for name in params)
    assert all(math.isclose(calibrated["groups"][name]["budget_sq"], 0.1, rel_tol=0, abs_tol=1e-12) for name in params)
    assert all(calibrated["groups"][name]["dual_lambda"] == 0.0 for name in params)

    prepared = world_jepa_drift.prepare_task(
        calibrated, DRIFT_CONFIG, params, has_prior_training=True,
    )
    assert prepared["active"] == set(params)
    params["encoder"]["eW"][0] += 0.5
    gradients = {key: np.ones_like(value)
                 for group in params.values() for key, value in group.items()}
    controlled = world_jepa_drift.apply_pullback(params, gradients, prepared)
    assert controlled["eW"][0] > gradients["eW"][0]
    world_jepa_drift.update_dual(prepared, params)
    expected_lambda = 1.0 + 0.03 * (0.25 - (0.1 * 1.05 ** 2))
    assert math.isclose(prepared["lambdas"]["encoder"], expected_lambda, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(prepared["violation_mean"]["encoder"], 0.15, rel_tol=0, abs_tol=1e-12)
    persisted = world_jepa_drift.finish_task(prepared, params, steps=7)
    assert persisted["groups"]["encoder"]["controlled_steps"] == 7
    assert world_jepa_drift.validate_state(persisted) == persisted

    predictor_only = world_jepa_drift.prepare_task(
        persisted, DRIFT_CONFIG,
        {"encoder": {}, "predictor": params["predictor"], "inverse": {}},
        has_prior_training=True,
    )
    assert predictor_only["active"] == {"predictor"}
    assert predictor_only["lambdas"]["predictor"] == persisted["groups"]["predictor"]["dual_lambda"]
    disabled = world_jepa_drift.prepare_task(
        persisted, None, params, has_prior_training=True,
    )
    assert not disabled["active"]
    for invalid in (
        {"enabled": True, "budget_sq": 0},
        {"enabled": True, "deadzone": 0.8},
        {"enabled": True, "unknown": 1},
    ):
        try:
            world_jepa_drift.normalize_config(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid drift config accepted")


def test_adam_aware_replay_projection_constrains_the_actual_preconditioned_step():
    params = {"w": np.zeros(2, dtype=float)}
    projected = world_jepa.Adam(params, lr=0.1).step(
        {"w": np.array([-1.0, 2.0])}, constraint_gradients={"w": np.array([1.0, 0.0])}
    )
    assert projected["enabled"] is True and projected["projected"] is True
    assert projected["constraint_dot_before"] < 0.0
    assert abs(projected["constraint_dot_after"]) <= projected["constraint_tolerance"]
    assert np.allclose(params["w"], np.array([0.0, -0.1]), atol=1e-9)
    positive_params = {"w": np.zeros(2, dtype=float)}
    positive = world_jepa.Adam(positive_params, lr=0.1).step(
        {"w": np.array([1.0, 2.0])}, constraint_gradients={"w": np.array([1.0, 0.0])}
    )
    assert positive["projected"] is False and positive["constraint_dot_before"] > 0.0
    assert positive["projection_method"] == "ALREADY_FEASIBLE"
    assert positive["projection_candidates_examined"] == 0
    assert np.allclose(positive_params["w"], np.array([-0.1, -0.1]), atol=1e-9)
    zero_params = {"w": np.zeros(2, dtype=float)}
    zero = world_jepa.Adam(zero_params, lr=0.1).step(
        {"w": np.array([-1.0, 2.0])}, constraint_gradients={"w": np.zeros(2, dtype=float)}
    )
    assert zero["reference_zero"] is True and zero["projected"] is False
    assert zero["projection_method"] == "NO_ACTIVE_REFERENCE"
    assert zero["projection_candidates_examined"] == 0
    assert np.allclose(zero_params["w"], np.array([0.1, -0.1]), atol=1e-9)

def test_adam_per_session_gem_projection_satisfies_each_prior_cohort():
    params = {"w": np.zeros(2, dtype=float)}
    constraints = [
        {"w": np.array([1.0, 0.0])},
        {"w": np.array([1.0, 1.0])},
    ]
    report = world_jepa.Adam(params, lr=0.1).step(
        {"w": np.array([-1.0, 1.0])},
        constraint_gradients=constraints,
    )
    direction = -params["w"] / 0.1
    assert report["constraint_count"] == 2
    assert report["active_constraint_count"] == 2
    assert report["projected"] is True
    assert report["projection_sweeps"] >= 1
    assert report["max_constraint_violation"] <= report["constraint_tolerance"]
    assert all(float(np.dot(item["w"], direction)) >= -1e-10 for item in constraints)
    assert np.allclose(direction, np.array([0.0, 1.0]), atol=1e-8)


def test_adam_per_session_gem_active_set_handles_nearly_opposing_session_gradients():
    # The former 64-sweep Dykstra loop needs thousands of passes for this
    # narrow feasible cone. The exact <=8-cohort active-set solve is bounded.
    theta = 0.1
    constraints = [
        {"w": np.array([1.0, 0.0])},
        {"w": np.array([-np.cos(theta), np.sin(theta)])},
    ]
    params = {"w": np.zeros(2, dtype=float)}
    report = world_jepa.Adam(params, lr=0.1).step(
        {"w": np.array([1.0, -1.0])},
        constraint_gradients=constraints,
    )
    direction = -params["w"] / 0.1
    assert report["projection_method"] == "ACTIVE_SET_ENUMERATION"
    assert report["projection_candidates_examined"] == 4
    assert report["kkt_active_constraint_count"] == 2
    assert report["max_constraint_violation"] <= report["constraint_tolerance"]
    assert all(float(item["w"] @ direction) >= -report["constraint_tolerance"]
               for item in constraints)
    assert np.allclose(direction, np.zeros(2), atol=1e-8)


def test_session_contiguous_replay_is_deterministic_bounded_and_session_local():
    def row(index, session):
        return {
            "action_id": f"replay-{index:03d}",
            "source_sha256": hashlib.sha256(f"source-{index}".encode()).hexdigest(),
            "created": float(index),
            "session_id": session,
        }

    old_rows = (
        [row(index, "session-a") for index in range(8)]
        + [row(index + 8, "session-b") for index in range(8)]
        + [row(index + 16, None) for index in range(2)]
    )
    new_rows = [row(index + 18, "new-session") for index in range(4)]
    uniform = world_jepa_replay.select_replay_rows(
        "uniform_budget", new_rows, old_rows, budget=6, salt="fixed-cohort"
    )
    contiguous = world_jepa_replay.select_replay_rows(
        "session_contiguous", new_rows, old_rows, budget=6, salt="fixed-cohort"
    )
    repeated = world_jepa_replay.select_replay_rows(
        "session_contiguous", new_rows, old_rows, budget=6, salt="fixed-cohort"
    )
    assert len(uniform["rows"]) == len(contiguous["rows"]) == 6
    assert {item["action_id"] for item in uniform["rows"]} != {
        item["action_id"] for item in contiguous["rows"]
    }
    assert contiguous["budget_matched"] is True
    assert contiguous["session_count"] == 2
    assert contiguous["window_count"] == 2
    assert contiguous["manifest_sha256"] == repeated["manifest_sha256"]
    selected_ids = {item["action_id"] for item in contiguous["rows"]}
    assert selected_ids.isdisjoint({item["action_id"] for item in new_rows})
    assert len(selected_ids) == 6
    for window in contiguous["windows"]:
        group = sorted(
            [item for item in old_rows if item["session_id"] == window["session_id"]],
            key=lambda item: (item["created"], item["action_id"]),
        )
        expected = group[window["start_index"]:window["start_index"] + window["count"]]
        selected = [
            item for item in contiguous["rows"]
            if item["session_id"] == window["session_id"]
        ]
        assert [item["action_id"] for item in selected] == [
            item["action_id"] for item in expected
        ]

    # Legacy rows with no trusted session identity are never guessed into a
    # session window; the budget mismatch is explicit instead of silent.
    partial = world_jepa_replay.select_replay_rows(
        "session_contiguous", new_rows, old_rows, budget=18, salt="fixed-cohort"
    )
    assert len(partial["rows"]) == 16
    assert partial["budget_matched"] is False
    assert all(item["session_id"] is not None for item in partial["rows"])
    assert world_jepa_replay.select_replay_rows(
        "none", new_rows, old_rows, budget=6, salt="fixed-cohort"
    )["rows"] == []


def test_on_demand_conflict_replay_is_bounded_deterministic_and_budget_matched():
    def row(index, session):
        return {
            "action_id": f"ondemand-{index:03d}",
            "source_sha256": hashlib.sha256(f"ondemand-source-{index}".encode()).hexdigest(),
            "created": float(index),
            "session_id": session,
        }

    old_rows = (
        [row(index, "session-a") for index in range(8)]
        + [row(index + 8, "session-b") for index in range(8)]
        + [row(index + 16, "session-c") for index in range(8)]
        + [row(index + 24, "session-d") for index in range(8)]
        + [row(index + 32, None) for index in range(2)]
    )
    new_rows = [row(index + 40, "new-session") for index in range(4)]
    scores = {
        "session-a": 0.1,
        "session-b": 0.9,
        "session-c": 0.5,
        "session-d": 0.3,
    }
    selected = world_jepa_replay.select_replay_rows(
        "on_demand_conflict", new_rows, old_rows, budget=6,
        salt="fixed-on-demand", cohort_scores=scores,
    )
    repeated = world_jepa_replay.select_replay_rows(
        "on_demand_conflict", new_rows, old_rows, budget=6,
        salt="fixed-on-demand", cohort_scores=scores,
    )
    selected_sessions = {item["session_id"] for item in selected["rows"]}
    assert selected["budget_matched"] is True
    assert selected["budget_rows"] == selected["requested_budget_rows"] == 6
    assert selected["session_count"] == 3
    assert selected["scored_session_count"] == 4
    assert selected["legacy_rows_excluded"] == 2
    assert selected["manifest_sha256"] == repeated["manifest_sha256"]
    assert selected_sessions == {"session-b", "session-c", "session-d"}
    assert all(item["session_id"] is not None for item in selected["rows"])
    assert len({item["action_id"] for item in selected["rows"]}) == 6
    assert {item["action_id"] for item in selected["rows"]}.isdisjoint(
        {item["action_id"] for item in new_rows}
    )


def test_on_demand_loss_replay_selects_only_positive_forgetting_demand():
    def row(index, session):
        return {
            "action_id": f"loss-demand-{index:03d}",
            "source_sha256": hashlib.sha256(f"loss-source-{index}".encode()).hexdigest(),
            "created": float(index),
            "session_id": session,
        }

    old_rows = (
        [row(index, "retained") for index in range(8)]
        + [row(index + 8, "forgotten-a") for index in range(8)]
        + [row(index + 16, "forgotten-b") for index in range(8)]
        + [row(index + 24, None) for index in range(2)]
    )
    new_rows = [row(index + 26, "new-session") for index in range(4)]
    scores = {"retained": 0.0, "forgotten-a": 0.75, "forgotten-b": 0.25}
    selected = world_jepa_replay.select_replay_rows(
        "on_demand_loss", new_rows, old_rows, budget=6,
        salt="loss-demand-control", cohort_scores=scores,
    )
    repeated = world_jepa_replay.select_replay_rows(
        "on_demand_loss", new_rows, old_rows, budget=6,
        salt="loss-demand-control", cohort_scores=scores,
    )
    selected_sessions = {item["session_id"] for item in selected["rows"]}
    assert selected_sessions == {"forgotten-a", "forgotten-b"}
    assert selected["budget_rows"] == selected["requested_budget_rows"] == 6
    assert selected["budget_matched"] is True
    assert selected["manifest_sha256"] == repeated["manifest_sha256"]
    assert selected["legacy_rows_excluded"] == 2
    assert selected["scored_session_count"] == 3
    assert selected["unscored_session_count"] == 0
    assert len(selected["rows"]) == 6
    assert {item["action_id"] for item in selected["rows"]}.isdisjoint(
        {item["action_id"] for item in new_rows}
    )

    no_demand = world_jepa_replay.select_replay_rows(
        "on_demand_loss", new_rows, old_rows, budget=6,
        salt="loss-demand-control", cohort_scores={
            "retained": 0.0, "forgotten-a": 0.0, "forgotten-b": 0.0,
        },
    )
    assert no_demand["rows"] == []
    assert no_demand["budget_rows"] == 0
    assert no_demand["budget_matched"] is False

    try:
        world_jepa_replay.select_replay_rows(
            "on_demand_loss", new_rows, old_rows, budget=6,
            salt="loss-demand-control", cohort_scores={"forgotten-a": -0.1},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("negative loss-demand score accepted")


def test_retention_gate_allows_small_bounded_drift_but_rejects_larger_regression():
    before = {"session:a": {"rows": 20, "loss": 0.25}}
    within_budget = {"session:a": {"rows": 20, "loss": 0.252}}
    over_budget = {"session:a": {"rows": 20, "loss": 0.253}}
    accepted = world_jepa_consumer._retention_cohort_gate(before, within_budget)
    rejected = world_jepa_consumer._retention_cohort_gate(before, over_budget)
    assert accepted["accepted"] is True
    assert accepted["cohorts"]["session:a"]["tolerance"] == 0.0025
    assert rejected["accepted"] is False
    assert rejected["reason"] == "SESSION_RETENTION_REGRESSED"


def test_source_disjoint_guard_split_is_deterministic_and_keeps_duplicates_together():
    rows = []
    for session in ("guard-alpha", "guard-beta"):
        for index in range(40):
            rows.append({
                "action_id": f"{session}-{index:03d}",
                "source_id": f"source-{session}-{index:03d}",
                "source_sha256": hashlib.sha256(
                    f"guard-source-{session}-{index}".encode()
                ).hexdigest(),
                "session_id": session,
                "s": [float(index % 7), float(index % 5), 0.25, -0.5],
                "a": world_model.ACTIONS[index % len(world_model.ACTIONS)],
                "y": [float(index % 11) / 10.0, float(index % 3), float(index % 13) / 8.0],
            })
    # Different source IDs with identical transition content must stay in one
    # fold rather than leak the same example between fit and guard.
    rows[1]["s"] = list(rows[0]["s"])
    rows[1]["a"] = rows[0]["a"]
    rows[1]["y"] = list(rows[0]["y"])

    first = world_jepa_consumer._source_disjoint_guard_split(rows, salt="guard-seed")
    second = world_jepa_consumer._source_disjoint_guard_split(rows, salt="guard-seed")
    assert first is not None and second is not None
    assert first["manifest"]["manifest_sha256"] == second["manifest"]["manifest_sha256"]
    assert first["manifest"]["source_disjoint"] is True
    assert first["manifest"]["content_disjoint"] is True
    assert len(first["fit_rows"]) + len(first["guard_rows"]) == len(rows)

    fit_ids = {row["action_id"] for row in first["fit_rows"]}
    guard_ids = {row["action_id"] for row in first["guard_rows"]}
    fit_sources = {row["source_id"] for row in first["fit_rows"]}
    guard_sources = {row["source_id"] for row in first["guard_rows"]}
    fit_source_hashes = {row["source_sha256"] for row in first["fit_rows"]}
    guard_source_hashes = {row["source_sha256"] for row in first["guard_rows"]}
    content = lambda row: hashlib.sha256(json.dumps(
        {"s": row["s"], "a": row["a"], "y": row["y"]},
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    assert fit_ids.isdisjoint(guard_ids)
    assert fit_sources.isdisjoint(guard_sources)
    assert fit_source_hashes.isdisjoint(guard_source_hashes)
    assert {content(row) for row in first["fit_rows"]}.isdisjoint(
        {content(row) for row in first["guard_rows"]}
    )
    for session in ("guard-alpha", "guard-beta"):
        assert sum(row["session_id"] == session for row in first["fit_rows"]) >= 2
        assert sum(row["session_id"] == session for row in first["guard_rows"]) >= 2
    assert world_jepa_consumer._source_disjoint_guard_split(rows[:3], salt="small") is None


def _set_permissions(store, *, steps, replay_mode, encoder_mode="full",
                     replay_projection=False, learning_enabled=True, optimizer_permission=True):
    payload = {
        "learning_enabled": learning_enabled is True,
        "optimizer_permission": optimizer_permission is True,
        "steps": steps,
        "replay_mode": replay_mode,
        "encoder_mode": encoder_mode,
        "replay_projection": replay_projection,
    }
    _, version = store.state(PERMISSION_KEY, DEFAULT_PERMISSIONS)
    store.set_state(PERMISSION_KEY, payload, expected=version)


def _add_phase(store, *, seed, phase, domain, count):
    session_id = store.new_session()
    source_hashes = {}
    action_ids = []
    event_ids = []
    actions = tuple(world_model.ACTIONS)

    for index in range(count):
        prefix = f"synthetic-v14-aba-{phase}-{seed}-{index:04d}"
        source = prefix + ("x" * (index % 29))
        event = store.event(session_id, source)
        source_ref = event["source_ref"]
        generation = event["brain_generation_id"]
        source_hashes[source_ref["sha256"]] = phase

        action_index = index % len(actions)
        route = actions[action_index]
        selection = contracts.packet(
            "ActionSelection",
            "C2_CONTROL",
            event["event_id"],
            generation,
            [source_ref],
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
            event["event_id"],
            generation,
            forecast={
                "input_chars": len(source),
                "resource_state": "NORMAL",
            },
        )

        if domain == "A":
            duration = 0.15 + action_index * 0.65 + (index % 13) * 0.02
            characters = 9 + action_index * 24 + (index % 23) * 0.75
        else:
            # Same observed state/action schema, changed dynamics: the action
            # ordering is reversed so replay must trade off adaptation/retention.
            duration = 0.35 + (len(actions) - 1 - action_index) * 0.45
            duration += (index % 13) * 0.02
            characters = 12 + (len(actions) - 1 - action_index) * 16
            characters += (index % 23) * 0.75

        if index == count - 1:
            status = "FINAL"
        elif index % 31 == 0:
            status = "OUTCOME_UNKNOWN"
        elif index % 7 == 0:
            status = "FAILED"
        else:
            status = "FINAL"

        store.finish_action(
            action_id,
            status,
            actual={
                "action_duration_s": float(duration),
                "characters": float(characters),
            },
        )
        action_ids.append(action_id)
        event_ids.append(event["event_id"])

    return {
        "phase": phase,
        "domain": domain,
        "session_id": session_id,
        "source_hashes": source_hashes,
        "action_ids": action_ids,
        "event_ids": event_ids,
        "last_event_id": event_ids[-1],
    }

def _sync_data_preserving_arm_state(master_home, arm_home):
    arm_store = Store(arm_home)
    saved_state, _ = arm_store.state(STATE_KEY, None)
    saved_permissions, _ = arm_store.state(PERMISSION_KEY, DEFAULT_PERMISSIONS)
    assert type(saved_state) is dict and saved_state.get("active") is not None
    arm_store.close()

    data_dir = arm_home / "data"
    shutil.rmtree(data_dir)
    shutil.copytree(master_home / "data", data_dir)

    arm_store = Store(arm_home)
    _, state_version = arm_store.state(STATE_KEY, None)
    arm_store.set_state(STATE_KEY, copy.deepcopy(saved_state), expected=state_version)
    _, permission_version = arm_store.state(PERMISSION_KEY, DEFAULT_PERMISSIONS)
    arm_store.set_state(
        PERMISSION_KEY,
        copy.deepcopy(saved_permissions),
        expected=permission_version,
    )
    return arm_store


def _metrics(result):
    value = result.get("metrics")
    return value if type(value) is dict else result


def _active_state(store):
    value, _ = store.state(STATE_KEY, None)
    assert type(value) is dict and type(value.get("active")) is dict
    return value


def _run_phase(store, home, *, steps, replay_mode, encoder_mode="full", drift_control=None,
               replay_projection=False):
    _set_permissions(
        store, steps=steps, replay_mode=replay_mode, encoder_mode=encoder_mode,
        replay_projection=replay_projection,
    )
    state_before = store.state(STATE_KEY, None)[0]
    after_seq = int(state_before.get("scan_cursor", 0)) if type(state_before) is dict else 0
    verified, rejected, next_cursor, scanned, censored, has_more = (
        verify_committed_transition_page(store, after_seq=after_seq, limit=256)
    )
    assert len(verified) > 0 and next_cursor > after_seq and censored > 0
    before = _active_state(store) if state_before else None
    before_sha = before["active"]["checkpoint_sha256"] if before else None

    result = world_jepa_runtime.consume_after_commit(
        store, home=home, limit=256, drift_control=drift_control,
    )
    assert result.get("runtime_adapter_called") is True
    assert result.get("learning_enabled") is True
    assert result.get("optimizer_permission") is True
    assert result.get("decision_authority") == "NONE"
    assert result.get("native_body_consumed") is False
    assert result.get("native_body_weights_changed") is False
    assert result.get("status") in {
        "UPDATED_EXPERIMENTAL_WORLD_JEPA",
        "UTILITY_GATE_REJECTED",
    }, f"unexpected WorldJEPA result: {result!r}"

    metrics = _metrics(result)
    drift_metrics = metrics.get("drift_control")
    projection_metrics = metrics.get("gradient_projection")
    assert type(projection_metrics) is dict
    assert projection_metrics.get("requested") is replay_projection
    assert projection_metrics.get("enabled") is (replay_projection and metrics.get("replay_projection_enabled") is True)
    if replay_projection:
        assert projection_metrics.get("steps") == metrics.get("optimizer_steps_added")
        assert projection_metrics.get("constraint_count") == metrics.get("replay_constraint_session_count")
        assert projection_metrics.get("post_constraint_violation_steps") == 0
        if metrics.get("replay_projection_enabled") is True:
            assert projection_metrics.get("enabled") is True
            assert projection_metrics.get("active_constraint_count", 0) >= 1
            assert projection_metrics.get("replay_target_anchor") == "prior_ema_snapshot"
            assert metrics.get("replay_projection_fallback_reason") is None
        else:
            assert projection_metrics.get("enabled") is False
            assert projection_metrics.get("active_constraint_count", 0) == 0
            assert metrics.get("replay_projection_fallback_reason") in {
                "NO_PRIOR_CHECKPOINT", "NO_ELIGIBLE_REPLAY_ROWS"
            }
    assert type(drift_metrics) is dict
    assert drift_metrics.get("enabled") is (drift_control is not None)
    if drift_control is not None and before is not None:
        assert sum(item["controlled_steps"] for item in drift_metrics["groups"].values()) > 0
    assert result.get("new_receipts", metrics.get("new_train_rows", 0)) > 0
    if "train_holdout_source_sha256_disjoint" in metrics:
        assert metrics["train_holdout_source_sha256_disjoint"] is True
    assert metrics.get("replay_mode") == replay_mode
    assert metrics.get("encoder_mode") == encoder_mode
    if before is not None:
        assert metrics.get("guard_split_source_disjoint") is True
        assert metrics.get("guard_split_content_disjoint") is True
        assert metrics.get("retention_relative_tolerance") == 0.01
        assert metrics.get("backtracking_selection_fold") == "source_disjoint_training_guard"
        assert metrics.get("holdout_used_for_backtracking") is False
        trace = metrics.get("backtracking_trace")
        assert type(trace) is list and trace
        assert all("old_guard_cohort_gate" in item for item in trace)
        if metrics.get("current_guard_split_enabled"):
            assert all("new_guard_cohort_gate" in item for item in trace)
            assert metrics.get("current_guard_selection_fold") == "source_disjoint_current_training_guard"
            assert metrics.get("current_guard_gate_accepted") is True
        assert all(
            "holdout_loss_after" not in item and "old_holdout_loss_after" not in item
            for item in trace
        )
    parameter_delta = float(metrics.get("parameter_delta_norm", 0.0))
    encoder_delta = float(metrics.get("encoder_parameter_delta_norm", 0.0))
    predictor_delta = float(metrics.get("predictor_parameter_delta_norm", 0.0))
    ema_delta = float(metrics.get("ema_target_delta_norm", 0.0))
    assert math.isfinite(parameter_delta) and parameter_delta > 0.0
    assert math.isfinite(encoder_delta) and encoder_delta >= 0.0
    assert math.isfinite(predictor_delta) and predictor_delta > 0.0
    assert math.isfinite(ema_delta) and ema_delta >= 0.0
    if encoder_mode == "full":
        assert encoder_delta > 0.0 and ema_delta > 0.0
    else:
        assert encoder_delta == 0.0 and ema_delta == 0.0
    fit_before = metrics.get("fit_steps_before")
    fit_after = metrics.get("fit_steps_after")
    assert type(fit_before) is int and type(fit_after) is int and fit_after > fit_before
    assert result.get("utility_gate_accepted") is (result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA")

    after = _active_state(store)
    after_sha = after["active"]["checkpoint_sha256"]
    if result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
        assert after_sha != before_sha
        pending_ids = {row["action_id"] for row in after["pending_rows"]}
        expected_pending_ids = set(metrics.get("new_guard_action_ids", []))
        assert pending_ids == expected_pending_ids
        assert pending_ids.isdisjoint(set(after["active"]["processed_ids"]))
        assert pending_ids.isdisjoint({
            row["action_id"] for row in after["active"]["experience_rows"]
        })
        if expected_pending_ids:
            assert metrics.get("current_guard_split_source_disjoint") is True
            assert metrics.get("current_guard_split_content_disjoint") is True
            assert metrics.get("current_guard_gate_accepted") is True
        assert metrics.get("optimizer_moments_persisted") is True
        if metrics.get("prior_selected_update_scale") is not None:
            assert float(metrics["selected_update_scale"]) <= float(metrics["update_scale_cap"])
            assert float(metrics["update_scale_cap"]) <= 0.25
        checkpoint = home / "world_jepa" / after["active"]["checkpoint"]
        audit = world_jepa_optimizer_audit.audit_checkpoint(
            checkpoint,
            after["active"]["source_sha256"],
            after["active"]["checkpoint_sha256"],
        )
        assert audit.get("optimizer_state_sha256")
        assert audit.get("optimizer_state_present") is True
    else:
        assert after_sha == before_sha
        assert after["pending_rows"]

    replay_ids = set(metrics.get("fit_action_ids", [])) - set(
        metrics.get("new_train_action_ids", [])
    )
    assert len(replay_ids) == metrics.get("replay_rows", 0)
    if before is not None:
        prior_train_ids = set(before["active"]["train_ids"])
        prior_holdout_ids = set(before["active"]["holdout_ids"])
        assert replay_ids <= prior_train_ids
        assert replay_ids.isdisjoint(prior_holdout_ids)
    else:
        assert not replay_ids

    if replay_mode == "uniform" and before is not None:
        assert metrics.get("replay_rows", 0) > 0
    elif replay_mode == "none":
        assert metrics.get("replay_rows", 0) == 0
    elif replay_mode in {"uniform_budget", "session_contiguous", "on_demand_conflict"}:
        assert metrics.get("replay_budget_matched") is True
        assert metrics.get("replay_rows") == min(
            metrics.get("replay_requested_budget_rows", 0),
            metrics.get("replay_candidate_rows", 0),
        )
        if replay_mode in {"session_contiguous", "on_demand_conflict"} and before is not None:
            assert metrics.get("replay_session_count", 0) > 0
            assert metrics.get("replay_window_count", 0) > 0
        if replay_mode == "on_demand_conflict" and before is not None:
            assert metrics.get("replay_conflict_probe_fold") == "prior_guard"
            assert type(metrics.get("replay_conflict_probe_action_ids_sha256")) is str
            assert metrics.get("replay_conflict_probe_action_ids_sha256") == metrics.get(
                "prior_guard_action_ids_sha256"
            )
        if (replay_mode in {"on_demand_conflict", "on_demand_loss"}
                and before is not None
                and metrics.get("replay_projection_requested") is True):
            assert metrics.get("replay_projection_reference_fold") == "prior_guard"
            assert type(metrics.get("replay_projection_reference_action_ids_sha256")) is str
            assert metrics.get("replay_projection_constraint_source") == "prior_guard"
            assert metrics.get("replay_projection_reference_batch_count") == metrics.get(
                "replay_constraint_session_count"
            )
            assert metrics.get("replay_projection_reference_rows_total", 0) >= (
                2 * metrics.get("replay_projection_reference_batch_count", 0)
            )
        if replay_mode == "uniform_budget":
            assert metrics.get("replay_window_count", 0) == 0
    elif replay_mode == "on_demand_loss":
        assert metrics.get("replay_rows", 0) <= metrics.get("replay_requested_budget_rows", 0)
        assert type(metrics.get("replay_loss_demand_scores_sha256")) is str
        assert metrics.get("replay_loss_demand_probe_steps", 0) <= 8
        if before is not None:
            assert metrics.get("replay_loss_demand_probe_rows", 0) > 0
        if metrics.get("replay_loss_demand_positive_session_count", 0) == 0:
            assert metrics.get("replay_rows", 0) == 0

    assert type(metrics.get("fit_array_bytes")) is int and metrics["fit_array_bytes"] > 0
    assert type(metrics.get("replay_array_bytes")) is int
    assert metrics["replay_array_bytes"] >= 0
    assert metrics.get("optimizer_steps_added") == fit_after - fit_before

    return {
        "status": result["status"],
        "checkpoint_before": before_sha,
        "checkpoint_after": after_sha,
        # Preserve exact content-addressed checkpoint evidence from the consumer.
        "checkpoint_sha_before": metrics.get("checkpoint_sha_before"),
        "checkpoint_sha_after": metrics.get("checkpoint_sha_after"),
        "fit_steps_before": metrics.get("fit_steps_before"),
        "fit_steps_after": metrics.get("fit_steps_after"),
        "new_receipts": result.get("new_receipts", len(verified)),
        "censored_skipped": result.get("censored_skipped", censored),
        "scanned_rows": scanned,
        "rejected_receipts": rejected,
        "has_more": has_more,
        "fit_rows": metrics.get("fit_rows"),
        "new_train_rows": metrics.get("new_train_rows"),
        "new_fit_rows": metrics.get("new_fit_rows"),
        "new_guard_rows": metrics.get("new_guard_rows"),
        "new_guard_action_ids": metrics.get("new_guard_action_ids", []),
        "new_guard_cohort_gate": metrics.get("current_guard_cohort_gate"),
        "current_guard_gate_accepted": metrics.get("current_guard_gate_accepted"),
        "replay_candidate_rows": metrics.get("replay_candidate_rows"),
        "replay_mode": replay_mode,
        "replay_rows": metrics.get("replay_rows"),
        "replay_projection_requested": metrics.get("replay_projection_requested"),
        "replay_projection_enabled": metrics.get("replay_projection_enabled"),
        "replay_projection_fallback_reason": metrics.get("replay_projection_fallback_reason"),
        "replay_budget_rows": metrics.get("replay_budget_rows"),
        "replay_budget_matched": metrics.get("replay_budget_matched"),
        "replay_session_count": metrics.get("replay_session_count"),
        "replay_window_count": metrics.get("replay_window_count"),
        "replay_manifest_sha256": metrics.get("replay_manifest_sha256"),
        "replay_loss_demand_probe_rows": metrics.get("replay_loss_demand_probe_rows"),
        "replay_loss_demand_probe_steps": metrics.get("replay_loss_demand_probe_steps"),
        "replay_loss_demand_scored_session_count": metrics.get("replay_loss_demand_scored_session_count"),
        "replay_loss_demand_unscored_session_count": metrics.get("replay_loss_demand_unscored_session_count"),
        "replay_loss_demand_positive_session_count": metrics.get("replay_loss_demand_positive_session_count"),
        "replay_loss_demand_max_score": metrics.get("replay_loss_demand_max_score"),
        "replay_loss_demand_scores_sha256": metrics.get("replay_loss_demand_scores_sha256"),
        "fit_array_bytes": metrics.get("fit_array_bytes"),
        "replay_array_bytes": metrics.get("replay_array_bytes"),
        "optimizer_steps_added": metrics.get("optimizer_steps_added"),
        "optimizer_moments_persisted": metrics.get("optimizer_moments_persisted"),
        "optimizer_state_bootstrapped": metrics.get("optimizer_state_bootstrapped"),
        "update_scale": metrics.get("update_scale"),
        "selected_update_scale": metrics.get("selected_update_scale"),
        "update_scale_cap": metrics.get("update_scale_cap"),
        "prior_selected_update_scale": metrics.get("prior_selected_update_scale"),
        "backtracking_trace": metrics.get("backtracking_trace"),
        "holdout_improved": metrics.get("holdout_improved"),
        "utility_gate_accepted": result.get("utility_gate_accepted"),
        "guard_gate_accepted": metrics.get("guard_gate_accepted"),
        "old_guard_cohort_gate": metrics.get("old_guard_cohort_gate"),
        "backtracking_selection_fold": metrics.get("backtracking_selection_fold"),
        "holdout_used_for_backtracking": metrics.get("holdout_used_for_backtracking"),
        "retention_relative_tolerance": metrics.get("retention_relative_tolerance"),
        "old_holdout_retention_tolerance": metrics.get("old_holdout_retention_tolerance"),
        "holdout_loss_before": metrics.get("holdout_loss_before"),
        "holdout_loss_after": metrics.get("holdout_loss_after"),
        "holdout_loss_delta": metrics.get("holdout_loss_delta"),
        "negative_controls_separated": metrics.get("negative_controls_separated"),
        "old_holdout_retained": metrics.get("old_holdout_retained"),
        "old_holdout_cohort_retained": metrics.get("old_holdout_cohort_retained"),
        "retention_gate_accepted": metrics.get("retention_gate_accepted"),
        "old_holdout_loss_before": metrics.get("old_holdout_loss_before"),
        "old_holdout_loss_after": metrics.get("old_holdout_loss_after"),
        "old_holdout_retention_delta": metrics.get("old_holdout_retention_delta"),
        "old_holdout_cohort_gate": metrics.get("old_holdout_cohort_gate"),
        "encoder_mode": encoder_mode,
        "encoder_parameter_delta_norm": metrics.get("encoder_parameter_delta_norm"),
        "predictor_parameter_delta_norm": metrics.get("predictor_parameter_delta_norm"),
        "parameter_delta_norm": metrics.get("parameter_delta_norm"),
        "ema_target_delta_norm": metrics.get("ema_target_delta_norm"),
        "drift_control": drift_metrics,
        "gradient_projection": projection_metrics,
    }


def _cohort_holdout_metrics(store, phase_by_sha):
    state = _active_state(store)
    rows_by_id = {
        row["action_id"]: row for row in state["active"]["experience_rows"]
    }
    for row in state.get("pending_rows", []):
        rows_by_id[row["action_id"]] = row
    rows = sorted(rows_by_id.values(), key=lambda row: row["action_id"])

    split = world_jepa_consumer._source_disjoint_split(rows)
    by_action_id = {row["action_id"]: row for row in rows}
    train_rows = [by_action_id[action_id] for action_id in split["train_action_ids"]]
    holdout_rows = [by_action_id[action_id] for action_id in split["holdout_action_ids"]]
    train_source_ids = {row["source_id"] for row in train_rows}
    holdout_source_ids = {row["source_id"] for row in holdout_rows}
    train_source_hashes = {row["source_sha256"] for row in train_rows}
    holdout_source_hashes = {row["source_sha256"] for row in holdout_rows}
    assert train_source_ids.isdisjoint(holdout_source_ids)
    assert train_source_hashes.isdisjoint(holdout_source_hashes)
    assert split["manifest"]["source_disjoint"] is True
    assert split["manifest"]["source_sha256_disjoint"] is True

    learner = getattr(store, "_v14_world_jepa_consumer")
    model = learner._load_model(state["active"])
    report = {}
    for phase in ("A1", "B", "A2"):
        cohort = [
            row for row in holdout_rows
            if phase_by_sha.get(row["source_sha256"]) == phase
        ]
        assert len(cohort) >= 8
        x, actions, target = world_jepa_consumer._arrays(cohort)
        actual = float(model.prediction_loss(x, actions, target))
        shuffled = float(model.prediction_loss(
            x, np.roll(actions, 1, axis=0), target
        ))
        zero = float(model.prediction_loss(
            x, np.zeros_like(actions), target
        ))
        assert all(math.isfinite(value) for value in (actual, shuffled, zero))
        report[phase] = {
            "holdout_rows": len(cohort),
            "actual_loss": actual,
            "shuffled_action_loss": shuffled,
            "zero_action_loss": zero,
        }
    report["_split_manifest"] = split["manifest"]
    return report


def _assert_planner_is_shadow_only(store, home, event_id):
    first = consume_world_planner_shadow(store, event_id, home=home)
    second = consume_world_planner_shadow(store, event_id, home=home)
    assert first["status"] in {"SHADOW_PLANNER_READY", "SHADOW_PLANNER_UNAVAILABLE"}
    assert first.get("decision_authority") == "NONE"
    assert first.get("dispatch") is False
    assert first.get("native_body_consumed") is False
    assert first.get("native_body_weights_changed") is False
    assert first.get("persisted") is True
    assert second.get("idempotent") is True

    active = _active_state(store)["active"]
    readouts = first.get("candidate_readouts")
    assert type(readouts) is dict
    assert set(readouts) == set(world_model.ACTIONS)
    receiver_statuses = {role: set() for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL")}
    for action, action_readouts in readouts.items():
        assert {"B1_DETAIL", "B2_GIST", "SELF_MODEL"} <= set(action_readouts)
        for role in receiver_statuses:
            item = action_readouts[role]
            utility = world_jepa_consumer.receiver_utility_gate(active.get("metrics"), role)
            expected = "SHADOW_READOUT_ONLY" if utility["accepted"] else "RECEIVER_UTILITY_REJECTED"
            assert item.get("status") == expected
            assert item.get("receiver_utility", {}).get("accepted") is utility["accepted"]
            assert item.get("checkpoint_sha256") == active["checkpoint_sha256"]
            assert item.get("source_sha256") == active["source_sha256"]
            assert item.get("decision_authority") == "NONE"
            assert item.get("native_body_consumed") is False
            assert item.get("native_body_weights_changed") is False
            if utility["accepted"]:
                assert type(item.get("prediction")) is dict
            else:
                assert "prediction" not in item
            receiver_statuses[role].add(item["status"])

    memory = first.get("memory_recall", {})
    assert memory.get("status") in {
        "MEMORY_RECALL_SHADOW", "NO_RANKED_ACTION"
    }
    for item in memory.get("items", []):
        assert item.get("source_sha256")
        assert item.get("outcome_sha256")
        assert "source_text" not in item
        assert "content" not in item
    return {
        "status": first["status"],
        "ranked_actions": len(first.get("ranked_actions", [])),
        "receiver_statuses": {role: sorted(values) for role, values in receiver_statuses.items()},
        "memory_status": memory.get("status"),
        "memory_items": len(memory.get("items", [])),
    }

def test_consumer_falls_back_when_loss_demand_has_no_eligible_replay_rows(tmp_path, monkeypatch):
    home = tmp_path / "no-loss-demand"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        _add_phase(store, seed=71, phase="A1", domain="A", count=128)
        _set_permissions(
            store, steps=24, replay_mode="uniform", encoder_mode="full",
            replay_projection=False,
        )
        first = world_jepa_runtime.consume_after_commit(
            store, home=home, limit=256, drift_control=DRIFT_CONFIG,
        )
        assert first["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        before = _active_state(store)["active"]["checkpoint_sha256"]

        _add_phase(store, seed=72, phase="A2", domain="A", count=128)

        def no_positive_demand(
            model, new_rows, old_rows, *, train_encoder, salt, steps,
            cancel_check=None,
        ):
            sessions = sorted({
                row["session_id"] for row in old_rows
                if type(row.get("session_id")) is str and row["session_id"]
            })
            return {
                "scores": {session: 0.0 for session in sessions},
                "scored_session_count": len(sessions),
                "unscored_session_count": 0,
                "legacy_rows_excluded": sum(
                    1 for row in old_rows if not row.get("session_id")
                ),
                "probe_rows": 0,
                "probe_steps": 0,
            }

        # Deterministic negative control: the production selector receives
        # verified prior sessions but no positive loss-growth demand.
        monkeypatch.setattr(
            world_jepa_consumer, "_session_loss_demand_scores", no_positive_demand,
        )
        _set_permissions(
            store, steps=16, replay_mode="on_demand_loss", encoder_mode="full",
            replay_projection=True,
        )
        result = world_jepa_runtime.consume_after_commit(
            store, home=home, limit=256, drift_control=DRIFT_CONFIG,
        )
        metrics = _metrics(result)
        assert result["status"] in {
            "UPDATED_EXPERIMENTAL_WORLD_JEPA", "UTILITY_GATE_REJECTED",
        }
        assert result["status"] != "INSUFFICIENT_REPLAY_FOR_PROJECTION"
        assert metrics.get("replay_projection_requested") is True
        assert metrics.get("replay_projection_enabled") is False
        assert metrics.get("replay_projection_fallback_reason") == "NO_ELIGIBLE_REPLAY_ROWS"
        assert metrics.get("replay_rows") == 0
        projection = metrics.get("gradient_projection")
        assert type(projection) is dict
        assert projection.get("requested") is True
        assert projection.get("enabled") is False
        assert projection.get("active_constraint_count", 0) == 0
        assert result.get("native_body_weights_changed") is False

        after = _active_state(store)["active"]["checkpoint_sha256"]
        if result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
            assert after != before
            assert metrics.get("parameter_delta_norm", 0.0) > 0.0
        else:
            # The independent utility/retention gate may still reject the
            # no-replay candidate; rejection must leave the active checkpoint
            # byte-identical rather than turning the fallback into promotion.
            assert after == before
    finally:
        store.close()


def test_runtime_store_a_b_a_replay_retention_and_receiver_loop(tmp_path):
    reports = []
    for data_seed in DATA_SEEDS:
        master_home = tmp_path / f"master-{data_seed}"
        (master_home / "data" / "db").mkdir(parents=True)
        (master_home / "data" / "blobs").mkdir(parents=True)
        master = Store(master_home)

        a1 = _add_phase(
            master, seed=data_seed, phase="A1", domain="A", count=A1_COUNT
        )

        # The real runtime facade stays closed until both independent local
        # permissions are explicitly present in this disposable Store.
        off = world_jepa_runtime.consume_after_commit(
            master, home=master_home, limit=256
        )
        assert off["status"] == "OFF"
        _set_permissions(
            master, steps=A1_STEPS, replay_mode="uniform",
            learning_enabled=True, optimizer_permission=False,
        )
        pending = world_jepa_runtime.consume_after_commit(
            master, home=master_home, limit=256
        )
        assert pending["status"] == "PENDING_OPTIMIZER_PERMISSION"

        _set_permissions(
            master, steps=A1_STEPS, replay_mode="uniform",
            learning_enabled=True, optimizer_permission=True,
        )
        a1_result = world_jepa_runtime.consume_after_commit(
            master, home=master_home, limit=256, drift_control=DRIFT_CONFIG
        )
        assert a1_result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        assert a1_result["runtime_adapter_called"] is True
        assert a1_result["native_body_weights_changed"] is False
        a1_state = _active_state(master)
        assert all(
            type(row.get("session_id")) is str and row["session_id"] == a1["session_id"]
            for row in a1_state["active"]["experience_rows"]
        )
        a1_sha = a1_state["active"]["checkpoint_sha256"]
        a1_model = world_jepa_runtime._consumer(
            master, master_home, learning_enabled=True
        )._load_model(a1_state["active"])
        a1_drift = a1_model._training_state["drift"]
        assert all(
            a1_drift["groups"][name]["budget_sq"] > 0
            and a1_drift["groups"][name]["task_count"] == 1
            for name in ("encoder", "predictor", "inverse")
        )
        a1_audit = world_jepa_optimizer_audit.audit_checkpoint(
            master_home / "world_jepa" / a1_state["active"]["checkpoint"],
            a1_state["active"]["source_sha256"],
            a1_sha,
        )
        assert a1_audit.get("optimizer_state_present") is True
        master.close()

        arms = {}
        for replay_mode, encoder_mode, stable, projection in ARMS:
            arm_key = f"{replay_mode}-{encoder_mode}" + ("-stable" if stable else "")
            if projection:
                arm_key += "-agem"
            arm_home = tmp_path / f"arm-{data_seed}-{arm_key}"
            shutil.copytree(master_home, arm_home)
            arms[arm_key] = {
                "home": arm_home,
                "store": Store(arm_home),
                "replay_mode": replay_mode,
                "encoder_mode": encoder_mode,
                "stable": stable,
                "replay_projection": projection,
                "drift_control": DRIFT_CONFIG if stable else None,
                "phases": {"A1": {
                    "status": a1_result["status"],
                    "checkpoint_sha256": a1_sha,
                }},
            }

        master = Store(master_home)
        b_phase = _add_phase(
            master, seed=data_seed, phase="B", domain="B", count=SHIFT_COUNT
        )
        master.close()
        for arm in arms.values():
            arm["store"].close()
            arm["store"] = _sync_data_preserving_arm_state(
                master_home, arm["home"]
            )
            arm["phases"]["B"] = _run_phase(
                arm["store"], arm["home"],
                steps=SHIFT_STEPS, replay_mode=arm["replay_mode"],
                encoder_mode=arm["encoder_mode"],
                drift_control=arm["drift_control"],
                replay_projection=arm["replay_projection"],
            )
            arm["store"].close()
            arm["store"] = Store(arm["home"])
            restored = world_jepa_runtime._consumer(
                arm["store"], arm["home"], learning_enabled=True
            ).restore()
            assert restored["status"] == "RESTORED"

        master = Store(master_home)
        a2_phase = _add_phase(
            master, seed=data_seed, phase="A2", domain="A", count=SHIFT_COUNT
        )
        master.close()
        phase_by_sha = (
            a1["source_hashes"] | b_phase["source_hashes"] |
            a2_phase["source_hashes"]
        )

        for arm in arms.values():
            arm["store"].close()
            arm["store"] = _sync_data_preserving_arm_state(
                master_home, arm["home"]
            )
            arm["phases"]["A2"] = _run_phase(
                arm["store"], arm["home"],
                steps=SHIFT_STEPS, replay_mode=arm["replay_mode"],
                encoder_mode=arm["encoder_mode"],
                drift_control=arm["drift_control"],
                replay_projection=arm["replay_projection"],
            )
            arm["holdout"] = _cohort_holdout_metrics(
                arm["store"], phase_by_sha
            )
            arm["planner"] = _assert_planner_is_shadow_only(
                arm["store"], arm["home"], a2_phase["last_event_id"]
            )

            state = _active_state(arm["store"])
            before_rollback_sha = state["active"]["checkpoint_sha256"]
            previous = state.get("previous")
            if previous is not None:
                expected_rollback_sha = previous["checkpoint_sha256"]
                learner = getattr(arm["store"], "_v14_world_jepa_consumer")
                rollback = learner.rollback()
                assert rollback["status"] == "ROLLED_BACK"
                restored_state = _active_state(arm["store"])
                assert (
                    restored_state["active"]["checkpoint_sha256"]
                    == expected_rollback_sha
                )
                assert before_rollback_sha != expected_rollback_sha
                arm["rollback"] = {
                    "status": rollback["status"],
                    "readback_exact": True,
                    "restored_sha256": expected_rollback_sha,
                }
                arm["store"].close()
                arm["store"] = Store(arm["home"])
                replay = world_jepa_runtime.consume_after_commit(
                    arm["store"], home=arm["home"], limit=256
                )
                if replay["status"] == "INSUFFICIENT_SOURCE_DISJOINT_GUARD_COHORT":
                    replay_state = _active_state(arm["store"])
                    assert replay_state["active"]["checkpoint_sha256"] == expected_rollback_sha
                    assert replay_state["pending_rows"]
                    assert replay["pending_rows"] == len(replay_state["pending_rows"])
                    assert replay.get("new_train_rows", 0) > 0
                    assert replay.get("native_body_weights_changed") is False
                    arm["rollback"]["replay_deferred_without_checkpoint_change"] = True
                else:
                    assert replay["status"] in {
                        "UPDATED_EXPERIMENTAL_WORLD_JEPA",
                        "UTILITY_GATE_REJECTED",
                    }
                    arm["rollback"]["replay_deferred_without_checkpoint_change"] = False
                arm["rollback"]["replay_status"] = replay["status"]
            else:
                arm["rollback"] = {
                    "status": "NO_PREVIOUS_CHECKPOINT",
                    "readback_exact": True,
                    "restored_sha256": before_rollback_sha,
                    "replay_status": "NOT_APPLICABLE",
                }

            reports.append({
                "data_seed": data_seed,
                "replay_mode": arm["replay_mode"],
                "encoder_mode": arm["encoder_mode"],
                "stable_drift_control": arm["stable"],
                "replay_projection": arm["replay_projection"],
                "A1_checkpoint_sha256": a1_sha,
                "B": arm["phases"]["B"],
                "A2": arm["phases"]["A2"],
                "cohort_holdout": arm["holdout"],
                "planner": arm["planner"],
                "rollback": arm["rollback"],
            })
            arm["store"].close()

    assert len(reports) == len(DATA_SEEDS) * len(ARMS)
    # Persist synthetic per-seed/per-arm metrics even when a strict assertion fails.
    # CI uploads this small report on both success and failure so algorithmic
    # rejection can be diagnosed without weakening the retention/utility gates.
    diagnostic_path = Path(os.environ.get(
        "V14_JEPA_DIAGNOSTIC_PATH", "v14-jepa-aba-diagnostics.json"
    ))
    diagnostic_path.write_text(
        json.dumps({
            "schema": "v14.world_jepa.aba-diagnostic/1",
            "data_seeds": list(DATA_SEEDS),
            "arms": [list(arm) for arm in ARMS],
            "reports": reports,
        }, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    report_by_arm = {
        (item["data_seed"], item["encoder_mode"], item["replay_mode"],
         item["stable_drift_control"], item["replay_projection"]): item
        for item in reports
    }
    for data_seed in DATA_SEEDS:
        seed_reports = [item for item in reports if item["data_seed"] == data_seed]
        assert len(seed_reports) == len(ARMS)
        for encoder_mode in ("full", "predictor_only"):
            mode_reports = [
                item for item in seed_reports if item["encoder_mode"] == encoder_mode
            ]
            expected_arms = [arm for arm in ARMS if arm[1] == encoder_mode]
            assert len(mode_reports) == len(expected_arms)
            projected_reports = [
                item for item in mode_reports if item["replay_projection"] is True
            ]
            unprojected_reports = [
                item for item in mode_reports if item["replay_projection"] is False
            ]
            assert len(projected_reports) == sum(1 for arm in expected_arms if arm[3] is True)
            assert len(unprojected_reports) == sum(1 for arm in expected_arms if arm[3] is False)
            expected_arm_keys = {
                (arm[0], arm[2], arm[3]) for arm in expected_arms
            }
            actual_arm_keys = {
                (item["replay_mode"], item["stable_drift_control"], item["replay_projection"])
                for item in mode_reports
            }
            assert actual_arm_keys == expected_arm_keys
            loss_reports = [
                item for item in mode_reports if item["replay_mode"] == "on_demand_loss"
            ]
            assert len(loss_reports) == 2
            projected_loss = next(
                item for item in loss_reports if item["replay_projection"] is True
            )
            unprojected_loss = next(
                item for item in loss_reports if item["replay_projection"] is False
            )
            projected = projected_loss
            diagnostic = []
            for phase_name in ("B", "A2"):
                phase = projected[phase_name]
                trace = phase.get("backtracking_trace", [])
                compact_trace = []
                for attempt in trace:
                    cohorts = attempt.get("old_guard_cohort_gate", {}).get("cohorts", {})
                    new_cohorts = attempt.get("new_guard_cohort_gate", {}).get("cohorts", {})
                    compact_trace.append({
                        "scale": attempt.get("update_scale"),
                        "guard_accepted": attempt.get("guard_accepted"),
                        "new_guard_accepted": attempt.get("new_guard_cohort_gate", {}).get("accepted"),
                        "new_guard_max_delta": max(
                            (float(value.get("delta", 0.0)) for value in new_cohorts.values()),
                            default=None,
                        ),
                        "max_delta": max(
                            (float(value.get("delta", 0.0)) for value in cohorts.values()),
                            default=None,
                        ),
                        "max_tolerance": max(
                            (float(value.get("tolerance", 0.0)) for value in cohorts.values()),
                            default=None,
                        ),
                    })
                diagnostic.append({
                    "phase": phase_name,
                    "status": phase.get("status"),
                    "selected_scale": phase.get("selected_update_scale"),
                    "holdout_delta": phase.get("old_holdout_retention_delta"),
                    "trace": compact_trace,
                })
            print("WORLDJEPA_LOSS_DEMAND_SEED_DIAGNOSTIC", data_seed, encoder_mode, diagnostic)

            accepted_a2 = []
            accepted_loss_a2 = []
            for report in mode_reports:
                a2 = report["A2"]
                if (report["replay_mode"] == "on_demand_loss"
                        and a2["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"):
                    accepted_loss_a2.append(a2)
                if a2["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
                    accepted_a2.append(a2)
                    assert a2["utility_gate_accepted"] is True
                    assert a2["old_holdout_cohort_gate"]["accepted"] is True
                    assert a2["negative_controls_separated"] is True
                    assert a2["predictor_parameter_delta_norm"] > 0.0
                    assert a2["optimizer_moments_persisted"] is True
                    assert a2["checkpoint_sha_before"] != a2["checkpoint_sha_after"]
                    assert a2["update_scale"] is not None
                    assert a2["selected_update_scale"] == a2["update_scale"]
                    assert a2["holdout_used_for_backtracking"] is False
                    if encoder_mode == "predictor_only":
                        assert a2["encoder_parameter_delta_norm"] == 0.0
                        assert a2["ema_target_delta_norm"] == 0.0
                    else:
                        assert a2["encoder_parameter_delta_norm"] > 0.0
                        assert a2["ema_target_delta_norm"] > 0.0
                    if report["replay_projection"] is True:
                        assert a2["gradient_projection"]["projected_steps"] > 0
                    else:
                        assert a2["gradient_projection"]["projected_steps"] == 0
                else:
                    # The final holdout is not a retry selector. A candidate
                    # that misses current-task utility remains uncommitted.
                    assert a2["status"] == "UTILITY_GATE_REJECTED"
                    assert a2["utility_gate_accepted"] is False
                    assert a2["checkpoint_sha_before"] == a2["checkpoint_sha_after"]
                    assert a2["holdout_used_for_backtracking"] is False
            assert accepted_a2, (
                f"no accepted A2 update across replay arms for {encoder_mode} seed {data_seed}"
            )
            if encoder_mode == "predictor_only":
                # Predictor-only is the positive control for loss-demand replay:
                # it must retain a useful A2 update for every tested seed.
                assert accepted_loss_a2, (
                    f"on-demand loss produced no accepted predictor-only A2 update "
                    f"for seed {data_seed}"
                )
                if projected_loss["A2"]["status"] == "UTILITY_GATE_REJECTED":
                    # The projected arm may correctly reject a seed even when
                    # the matched unprojected loss-demand arm accepts. Keep the
                    # final utility gate authoritative; require the safe
                    # unprojected fallback and byte-identical rollback.
                    assert unprojected_loss["A2"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
                    assert projected_loss["A2"]["checkpoint_sha_before"] == projected_loss["A2"]["checkpoint_sha_after"]
                    assert projected_loss["A2"]["utility_gate_accepted"] is False
                    assert projected_loss["A2"]["holdout_used_for_backtracking"] is False
                else:
                    assert projected_loss["A2"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
            elif (projected_loss["A2"]["status"] == "UTILITY_GATE_REJECTED"
                  and unprojected_loss["A2"]["status"] == "UTILITY_GATE_REJECTED"):
                # Do not force a full-encoder update when the independent final
                # holdout rejects both matched loss-demand candidates. The other
                # replay arms must still produce an accepted A2 update for this
                # seed; rejected candidates must leave the checkpoint untouched.
                for item in loss_reports:
                    a2 = item["A2"]
                    assert a2["utility_gate_accepted"] is False
                    assert a2["holdout_improved"] is False
                    assert a2["checkpoint_sha_before"] == a2["checkpoint_sha_after"]
                    assert a2["holdout_used_for_backtracking"] is False
            elif projected_loss["A2"]["status"] == "UTILITY_GATE_REJECTED":
                assert unprojected_loss["A2"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
            elif unprojected_loss["A2"]["status"] == "UTILITY_GATE_REJECTED":
                assert projected_loss["A2"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        for report in mode_reports:
            for phase in (report["B"], report["A2"]):
                if phase["status"] == "UTILITY_GATE_REJECTED":
                    assert phase["checkpoint_after"] == phase["checkpoint_before"]
                    assert phase["utility_gate_accepted"] is False
                    assert phase["holdout_used_for_backtracking"] is False

    for encoder_mode in ("full", "predictor_only"):
        accepted_loss = [
            item for item in reports
            if item["encoder_mode"] == encoder_mode
            and item["replay_mode"] == "on_demand_loss"
            and item["A2"]["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        ]
        assert accepted_loss, f"on-demand loss never accepted an A2 update for {encoder_mode}"
    print("WORLDJEPA_STORE_A_B_A_REPLAY_RETENTION " + __import__("json").dumps(
        reports, sort_keys=True, allow_nan=False
    ))



def test_per_session_retention_gate_rejects_mixed_regression_even_if_mean_improves():
    before = {
        "session:alpha": {"rows": 12, "loss": 0.50},
        "session:beta": {"rows": 12, "loss": 0.50},
    }
    after = {
        "session:alpha": {"rows": 12, "loss": 0.20},
        "session:beta": {"rows": 12, "loss": 0.70},
    }
    gate = world_jepa_consumer._retention_cohort_gate(before, after)
    assert gate["accepted"] is False
    assert gate["reason"] == "SESSION_RETENTION_REGRESSED"
    assert gate["cohorts"]["session:alpha"]["retained"] is True
    assert gate["cohorts"]["session:beta"]["retained"] is False


def test_per_session_retention_gate_fails_closed_when_cohort_budget_is_exceeded():
    gate = world_jepa_consumer._retention_cohort_gate({}, {}, overflow=True)
    assert gate["accepted"] is False
    assert gate["reason"] == "RETENTION_COHORT_LIMIT_EXCEEDED"

def _memory_forget_source(store, source_id, event_id):
    memory = object.__new__(Memory)
    memory.s = store
    return memory._forget_source(source_id, event_id)


def test_memory_forget_fails_closed_for_source_used_by_active_world_jepa(tmp_path):
    home = tmp_path / "world-jepa-forget-active"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        phase = _add_phase(
            store, seed=13, phase="FORGET-ACTIVE", domain="A", count=256
        )
        _set_permissions(
            store, steps=A1_STEPS, replay_mode="uniform",
            learning_enabled=True, optimizer_permission=True,
        )
        result = world_jepa_runtime.consume_after_commit(
            store, home=home, limit=256
        )
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        active = _active_state(store)["active"]
        source_id = active["experience_rows"][0]["source_id"]
        before = store.one(
            "SELECT deleted FROM sources WHERE id=?", (source_id,)
        )
        assert before is not None and before["deleted"] == 0

        with pytest.raises(ValueError, match="WorldJEPA"):
            _memory_forget_source(store, source_id, phase["last_event_id"])

        after = store.one(
            "SELECT deleted FROM sources WHERE id=?", (source_id,)
        )
        assert after is not None and after["deleted"] == 0
        assert _active_state(store)["active"]["checkpoint_sha256"] == active["checkpoint_sha256"]
    finally:
        store.close()


def test_memory_forget_detects_world_jepa_source_after_replay_row_eviction(tmp_path):
    home = tmp_path / "world-jepa-forget-evicted"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        phase = _add_phase(
            store, seed=13, phase="FORGET-EVICTED", domain="A", count=256
        )
        _set_permissions(
            store, steps=A1_STEPS, replay_mode="uniform",
            learning_enabled=True, optimizer_permission=True,
        )
        result = world_jepa_runtime.consume_after_commit(
            store, home=home, limit=256
        )
        assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"

        state, version = store.state(STATE_KEY, None)
        active = state["active"]
        target = active["experience_rows"][0]
        source_id = target["source_id"]
        action_id = target["action_id"]
        active["experience_rows"] = [
            row for row in active["experience_rows"]
            if row["action_id"] != action_id
        ]
        active["train_ids"] = [
            item for item in active["train_ids"] if item != action_id
        ]
        active["holdout_ids"] = [
            item for item in active["holdout_ids"] if item != action_id
        ]
        store.set_state(STATE_KEY, state, expected=version)

        with pytest.raises(ValueError, match="evicted replay rows"):
            _memory_forget_source(store, source_id, phase["last_event_id"])

        after = store.one(
            "SELECT deleted FROM sources WHERE id=?", (source_id,)
        )
        assert after is not None and after["deleted"] == 0
    finally:
        store.close()


def test_memory_forget_discards_untrained_pending_world_jepa_source(tmp_path):
    home = tmp_path / "world-jepa-forget-pending"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        phase = _add_phase(
            store, seed=227, phase="FORGET-PENDING", domain="A", count=1
        )
        _set_permissions(
            store, steps=8, replay_mode="uniform",
            learning_enabled=True, optimizer_permission=True,
        )
        result = world_jepa_runtime.consume_after_commit(
            store, home=home, limit=256
        )
        assert result["status"] == "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT"
        state, _ = store.state(STATE_KEY, None)
        assert len(state["pending_rows"]) == 1
        source_id = state["pending_rows"][0]["source_id"]

        _memory_forget_source(store, source_id, phase["last_event_id"])

        state, _ = store.state(STATE_KEY, None)
        assert state["pending_rows"] == []
        source = store.one(
            "SELECT deleted FROM sources WHERE id=?", (source_id,)
        )
        assert source is not None and source["deleted"] == 1
    finally:
        store.close()

