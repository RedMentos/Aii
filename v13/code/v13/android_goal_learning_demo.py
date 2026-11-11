"""Runnable synthetic V13 Android goal -> action -> observation -> JEPA demo.

This is a *software-only* product path for exercising the joint action/learning
contract. It cannot touch Android, cannot authenticate operator approvals and
does not add simulated events to real T8 training data. Native dispatch stays OFF.
The C5-like controller below is a finite deterministic baseline, NOT a JEF model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .android_control import AndroidControlBroker, ControlDenied
from .android_control_sim import DEMO_PACKAGE, SimulatedAndroidWorld
from .android_sim_jepa_probe import trial
from .android_operator_world import synthetic_operator_action

MAX_STEPS_PER_NOTE = 6
MAX_DEMO_NOTES = 48


def _next_action(snapshot, target):
    """Deterministic perception-dependent control baseline; no model inference."""
    if snapshot.get("kind") != "SIMULATED_UI_ONLY":
        raise ValueError("refuse non-synthetic Android observation")
    if snapshot.get("native_android_control") is not False:
        raise ValueError("native Android state cannot enter synthetic controller")
    if snapshot["screen"] == "HOME":
        return "launch_app", {"package": DEMO_PACKAGE}
    if snapshot["screen"] == "NOTES":
        if target in snapshot["notes"]:
            return None
        return "tap", {"x": 200, "y": 150}
    if snapshot["screen"] == "EDITOR":
        if snapshot["draft"] == "":
            return "type_text", {"text": target}
        if snapshot["draft"] == target:
            return "tap", {"x": 200, "y": 350}
    raise ValueError("unexpected simulated app state; no action")


def _synthetic_action(broker, world, capability, args):
    """Core operator proposal/approval -> synthetic companion -> world receipt.

    Fixture approval is not Android permission or real user consent.
    """
    return synthetic_operator_action(broker, world, capability, args)


def run_demo(home, *, first=0, count=18, seed=17, learn=True):
    """Execute a bounded Notes task, reopen its state and optionally fit JEPA.

    Each note is created by state-dependent actions and the broker's dry-run
    envelope. All receipts persist in a separate SQLite simulator database.
    Only synthetic numerical features feed the JEPA probe. No real T8 import.
    """
    if (type(first) is not int or type(count) is not int
            or first < 0 or not 1 <= count <= MAX_DEMO_NOTES
            or first + count > 64 or type(seed) is not int or seed < 0
            or type(learn) is not bool):
        raise ValueError("invalid bounded synthetic task budget")
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    broker = AndroidControlBroker(home / "android_demo_broker.sqlite")
    world = SimulatedAndroidWorld(home)
    completed = []
    try:
        broker.start()
        for i in range(first, first + count):
            target = f"SYNTHETIC-NOTE-{i:03d}"
            for _ in range(MAX_STEPS_PER_NOTE):
                obs = world.view()
                action = _next_action(obs, target)
                if action is None:
                    completed.append(i)
                    break
                _synthetic_action(broker, world, *action)
            else:
                raise ValueError("task exceeded bounded action count")
            # Include a real persisted simulator observation receipt after task.
            _synthetic_action(broker, world, "observe_ui", {})
        if len(completed) != count:
            raise ValueError("some synthetic tasks were not completed")
        final = world.view()
        if (final["screen"] != "NOTES"
                or not all(f"SYNTHETIC-NOTE-{i:03d}" in final["notes"]
                           for i in range(first, first + count))):
            raise ValueError("synthetic Notes task did not reach target state")
        final_sha = final["state_sha256"]
        action_count = world.receipt_count()
    finally:
        world.close()
        broker.close()

    # Fresh-process-equivalent readback from the durable simulation database.
    restored = SimulatedAndroidWorld(home)
    try:
        state = restored.view()
        if (state["state_sha256"] != final_sha
                or restored.receipt_count() != action_count):
            raise ValueError("synthetic Android state/replay receipt restart mismatch")
        learning = {"status": "OFF"}
        if learn:
            learning = trial(
                restored, seed=seed, steps=3,
                checkpoint=restored.root / "android_goal_shadow_jepa.npz")
            if (learning["scope"] != "SYNTHETIC_UI_ONLY_NO_T8_SOURCE"
                    or learning["active_model_promoted"] is not False
                    or learning["registered_t8_training_corpus_modified"] is not False
                    or learning["readback"]["inference_reload_exact_loss"] is not True):
                raise ValueError("invalid synthetic JEPA provenance/readback")
        return {
            "schema": "v13.android.goal_learning_demo/1",
            "status": "SOFTWARE_SYNTHETIC_ONLY",
            "controller": "finite_perception_dependent_baseline_NOT_JEF",
            "behavior_review": "CONTEXTUAL_ADVISORY_ON_EACH_SYNTHETIC_ACTION",
            "tasks_completed_this_run": len(completed),
            "total_persisted_notes": len(state["notes"]),
            "action_receipt_count": action_count,
            "restart_state_digest_equal": True,
            "learning": learning,
            "native_android_executed": False,
            "registered_t8_training_corpus_modified": False,
            "external_tool_authority": False,
            "b1_b2_c3_weights_modified": False,
        }
    finally:
        restored.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="V13 finite Android GOAL→JEPA simulation; NEVER operates Android")
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--first", type=int, default=0)
    parser.add_argument("--count", type=int, default=18)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--no-learn", action="store_true")
    parser.add_argument("--simulation-only", action="store_true", required=True,
                        help="Explicitly acknowledge the demonstration is NOT Android OS control")
    args = parser.parse_args(argv)
    result = run_demo(args.home, first=args.first, count=args.count,
                      seed=args.seed, learn=not args.no_learn)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
