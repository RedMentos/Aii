"""Dry-run broker -> fake UI -> durable simulated note, no Android OS action."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_control_sim import SimulatedAndroidWorld, DEMO_PACKAGE


def _action(broker, capability, args, *, approve=True, execute=True):
    proposal = broker.propose(capability, args)
    if approve:
        broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    if execute:
        return broker.execute(proposal.action_id)
    return proposal


@pytest.fixture
def env(tmp_path):
    broker = AndroidControlBroker(tmp_path / "broker.sqlite")
    broker.start()
    world = SimulatedAndroidWorld(tmp_path)
    yield broker, world, tmp_path
    world.close()
    broker.close()


def test_end_to_end_approved_actions_create_durable_note_without_os(env):
    broker, world, home = env
    goal = "remember tiny visual task"
    assert world.view()["screen"] == "HOME"
    for cap, arg in (
        ("launch_app", {"package": DEMO_PACKAGE}),
        ("tap", {"x": 200, "y": 150}),
        ("type_text", {"text": goal}),
        ("tap", {"x": 200, "y": 350}),
    ):
        receipt = world.apply(_action(broker, cap, arg))
        assert receipt["native_android_executed"] is False
        assert receipt["simulation_applied"] is True
        assert receipt["model_calls"] == 0
    screen = world.view()
    assert screen["kind"] == "SIMULATED_UI_ONLY"
    assert screen["screen"] == "NOTES"
    assert screen["notes"] == [goal]
    assert screen["native_android_control"] is False
    assert world.receipt_count() == 4
    # Restore exactly the same synthetic device from SQLite without
    # reconstructing its timeline in volatile Python memory.
    world.close()
    world = SimulatedAndroidWorld(home)
    assert world.view()["notes"] == [goal]
    assert world.receipt_count() == 4
    world.close()
    # Fixture world already closed; the broker still has its own audit.
    assert len([r for r in broker.events() if r[1] == "dry_run"]) == 4


def test_broker_approval_and_stop_remain_independent_of_simulation(env):
    broker, world, home = env
    proposal = broker.propose("launch_app", {"package": DEMO_PACKAGE})
    with pytest.raises(ControlDenied):
        broker.execute(proposal.action_id)
    with pytest.raises(ControlDenied):
        broker.approve(proposal.action_id, confirmed_by_local_ui=True) if False else broker.execute(proposal.action_id)
    assert world.view()["screen"] == "HOME"
    broker.stop()
    with pytest.raises(ControlDenied):
        broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    assert world.receipt_count() == 0
    assert world.view()["native_android_control"] is False


def test_replayed_or_forged_envelopes_never_mutate_fake_world(env):
    broker, world, home = env
    delivered = _action(broker, "launch_app", {"package": DEMO_PACKAGE})
    world.apply(delivered)
    sha = world.view()["state_sha256"]
    with pytest.raises(ControlDenied, match="replayed"):
        world.apply(delivered)
    with pytest.raises(ControlDenied):
        broker.execute(delivered["action_id"])
    for changed in (
        {**delivered, "status": "EXECUTED_NATIVE"},
        {**delivered, "args": {"package": "com.bank.security"}},
        {**delivered, "action_id": "../bad"},
        {**delivered, "capability": "shell"},
        {**delivered, "extra": True},
    ):
        with pytest.raises(ControlDenied):
            world.apply(changed)
    assert world.view()["state_sha256"] == sha
    assert world.receipt_count() == 1


def test_unsupported_real_packages_never_launch_from_dry_run(env):
    broker, world, home = env
    delivered = _action(broker, "launch_app", {"package": "com.example.bank"})
    with pytest.raises(ControlDenied, match="demo app only"):
        world.apply(delivered)
    assert world.view()["screen"] == "HOME"
    assert world.receipt_count() == 0


def test_failed_ui_action_does_not_persist_or_advance_receipt(env):
    broker, world, home = env
    text = _action(broker, "type_text", {"text": "secret"})
    snapshot = world.view()["state_sha256"]
    with pytest.raises(ControlDenied, match="not focused"):
        world.apply(text)
    assert world.view()["state_sha256"] == snapshot
    assert world.receipt_count() == 0
    back = _action(broker, "back", {})
    assert world.apply(back)["simulation_applied"] is True
    assert world.receipt_count() == 1


def test_multiple_world_instances_cannot_apply_same_receipt_twice(env):
    broker, world, home = env
    envelope = _action(broker, "launch_app", {"package": DEMO_PACKAGE})
    second_world = SimulatedAndroidWorld(home)

    def attempt(obj):
        try:
            obj.apply(envelope)
            return "APPLIED"
        except ControlDenied:
            return "DENIED"

    with ThreadPoolExecutor(max_workers=8) as workers:
        outcomes = list(workers.map(attempt, [world, second_world] * 10))
    assert outcomes.count("APPLIED") == 1
    assert outcomes.count("DENIED") == 19
    assert world.receipt_count() == 1
    assert second_world.view()["app"] == DEMO_PACKAGE
    second_world.close()


def test_corrupt_persisted_snapshot_fails_closed_after_restart(env):
    broker, world, home = env
    world.apply(_action(broker, "launch_app", {"package": DEMO_PACKAGE}))
    world.close()
    db = home / "android_control_sim" / "state.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE snapshot SET payload=? WHERE id=1",
                     ('{"bad":"data"}',))
    with pytest.raises(ValueError):
        SimulatedAndroidWorld(home)


def test_do_not_fake_native_companion_when_dry_run_false(env):
    broker, world, home = env
    p = broker.propose("tap", {"x": 150, "y": 150})
    broker.approve(p.action_id, confirmed_by_local_ui=True)
    with pytest.raises(ControlDenied, match="live Android"):
        broker.execute(p.action_id, dry_run=False)
    assert world.receipt_count() == 0
