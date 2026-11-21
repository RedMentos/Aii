"""Production-Store A→B→A replay/retention experiment for the WorldJEPA runtime adapter.

This uses committed SQLite T8 ActionSelection/ActionOutcome rows and the same
consume_after_commit facade called by SleepRuntime. Data are synthetic; this is
not a Redmi or native GGUF/B1/B2 weight proof.
"""
from __future__ import annotations

import copy
import math
import shutil

import numpy as np

from v13 import (
    contracts,
    world_jepa_consumer,
    world_jepa_optimizer_audit,
    world_jepa_runtime,
    world_model,
)
from v13.store import Store
from v13.world_jepa_store_authority import verify_committed_transition_page
from v13.world_jepa_planner import consume_world_planner_shadow

STATE_KEY = "v14.world_jepa.store_consumer"
PERMISSION_KEY = world_jepa_runtime.PERMISSION_KEY
DEFAULT_PERMISSIONS = dict(world_jepa_runtime.DEFAULT_PERMISSIONS)
ARMS = ("uniform", "none")
DATA_SEEDS = (13, 19, 43)
A1_COUNT = 256
SHIFT_COUNT = 96
A1_STEPS = 120
SHIFT_STEPS = 40


def _set_permissions(store, *, steps, replay_mode, learning_enabled=True,
                     optimizer_permission=True):
    payload = {
        "learning_enabled": learning_enabled is True,
        "optimizer_permission": optimizer_permission is True,
        "steps": steps,
        "replay_mode": replay_mode,
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
        source_hashes[source_ref["sha256"]] = phase

        action_index = index % len(actions)
        route = actions[action_index]
        selection = contracts.packet(
            "ActionSelection",
            "A5_SOURCE",
            event["event_id"],
            event["generation"],
            [source_ref],
            selected={
                "action_id": route,
                "action_type": "TEXT_REPORT",
                "score": 0.0,
                "permission_class": "LOCAL_ONLY",
                "focal_support": [],
            },
            route_hint=route,
            stage="COMMIT",
        )
        store.add_packet(selection)
        action_id = store.start_action(
            event["event_id"],
            event["generation"],
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


def _run_phase(store, home, *, steps, replay_mode):
    _set_permissions(store, steps=steps, replay_mode=replay_mode)
    state_before = store.state(STATE_KEY, None)[0]
    after_seq = int(state_before.get("scan_cursor", 0)) if type(state_before) is dict else 0
    verified, rejected, next_cursor, scanned, censored, has_more = (
        verify_committed_transition_page(store, after_seq=after_seq, limit=256)
    )
    assert len(verified) > 0 and next_cursor > after_seq and censored > 0
    before = _active_state(store) if state_before else None
    before_sha = before["active"]["checkpoint_sha256"] if before else None

    result = world_jepa_runtime.consume_after_commit(
        store, home=home, limit=256
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
    }

    metrics = _metrics(result)
    assert result.get("new_receipts", metrics.get("new_train_rows", 0)) > 0
    if "train_holdout_source_sha256_disjoint" in metrics:
        assert metrics["train_holdout_source_sha256_disjoint"] is True
    assert metrics.get("replay_mode") == replay_mode
    assert math.isfinite(float(metrics.get("parameter_delta_norm", 0.0)))
    assert math.isfinite(float(metrics.get("ema_target_delta_norm", 0.0)))

    after = _active_state(store)
    after_sha = after["active"]["checkpoint_sha256"]
    if result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA":
        assert after_sha != before_sha
        assert after["pending_rows"] == []
        assert metrics.get("optimizer_moments_persisted") is True
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

    if before is not None:
        if replay_mode == "uniform":
            assert metrics.get("replay_rows", 0) > 0
        else:
            assert metrics.get("replay_rows", 0) == 0

    return {
        "status": result["status"],
        "checkpoint_before": before_sha,
        "checkpoint_after": after_sha,
        "fit_steps_before": metrics.get("fit_steps_before"),
        "fit_steps_after": metrics.get("fit_steps_after"),
        "new_receipts": result.get("new_receipts", len(verified)),
        "censored_skipped": result.get("censored_skipped", censored),
        "scanned_rows": scanned,
        "rejected_receipts": rejected,
        "has_more": has_more,
        "fit_rows": metrics.get("fit_rows"),
        "replay_rows": metrics.get("replay_rows"),
        "holdout_improved": metrics.get("holdout_improved"),
        "negative_controls_separated": metrics.get("negative_controls_separated"),
        "old_holdout_retained": metrics.get("old_holdout_retained"),
        "parameter_delta_norm": metrics.get("parameter_delta_norm"),
        "ema_target_delta_norm": metrics.get("ema_target_delta_norm"),
    }


def _cohort_holdout_metrics(store, phase_by_sha):
    state = _active_state(store)
    rows_by_id = {
        row["action_id"]: row for row in state["active"]["experience_rows"]
    }
    for row in state.get("pending_rows", []):
        rows_by_id[row["action_id"]] = row
    rows = sorted(rows_by_id.values(), key=lambda row: row["action_id"])

    _, holdout_rows, split = world_jepa_consumer._source_disjoint_split(rows)
    assert set(split["train_source_sha256"]).isdisjoint(
        set(split["holdout_source_sha256"])
    )

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

    readouts = first.get("candidate_readouts", {})
    if readouts:
        assert set(readouts) == set(world_model.ACTIONS)
        for action in readouts.values():
            assert {"B1_DETAIL", "B2_GIST", "SELF_MODEL"} <= set(action)

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
        "memory_status": memory.get("status"),
        "memory_items": len(memory.get("items", [])),
    }


def test_runtime_store_a_b_a_replay_retention_and_receiver_loop(tmp_path):
    reports = []
    for data_seed in DATA_SEEDS:
        master_home = tmp_path / f"master-{data_seed}"
        master_home.mkdir()
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
            master, home=master_home, limit=256
        )
        assert a1_result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        assert a1_result["runtime_adapter_called"] is True
        assert a1_result["native_body_weights_changed"] is False
        a1_state = _active_state(master)
        a1_sha = a1_state["active"]["checkpoint_sha256"]
        a1_audit = world_jepa_optimizer_audit.audit_checkpoint(
            master_home / "world_jepa" / a1_state["active"]["checkpoint"],
            a1_state["active"]["source_sha256"],
            a1_sha,
        )
        assert a1_audit.get("optimizer_state_present") is True
        master.close()

        arms = {}
        for replay_mode in ARMS:
            arm_home = tmp_path / f"arm-{data_seed}-{replay_mode}"
            shutil.copytree(master_home, arm_home)
            arms[replay_mode] = {
                "home": arm_home,
                "store": Store(arm_home),
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
        for replay_mode, arm in arms.items():
            arm["store"].close()
            arm["store"] = _sync_data_preserving_arm_state(
                master_home, arm["home"]
            )
            arm["phases"]["B"] = _run_phase(
                arm["store"], arm["home"],
                steps=SHIFT_STEPS, replay_mode=replay_mode,
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

        for replay_mode, arm in arms.items():
            arm["store"].close()
            arm["store"] = _sync_data_preserving_arm_state(
                master_home, arm["home"]
            )
            arm["phases"]["A2"] = _run_phase(
                arm["store"], arm["home"],
                steps=SHIFT_STEPS, replay_mode=replay_mode,
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
                assert replay["status"] in {
                    "UPDATED_EXPERIMENTAL_WORLD_JEPA",
                    "UTILITY_GATE_REJECTED",
                }
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
                "replay_mode": replay_mode,
                "A1_checkpoint_sha256": a1_sha,
                "B": arm["phases"]["B"],
                "A2": arm["phases"]["A2"],
                "cohort_holdout": arm["holdout"],
                "planner": arm["planner"],
                "rollback": arm["rollback"],
            })
            arm["store"].close()

    assert len(reports) == len(DATA_SEEDS) * len(ARMS)
    print("WORLDJEPA_STORE_A_B_A_REPLAY_RETENTION " + __import__("json").dumps(
        reports, sort_keys=True, allow_nan=False
    ))
