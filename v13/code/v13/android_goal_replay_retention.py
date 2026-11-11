"""Bounded goal -> persisted synthetic Android outcomes -> WorldJEPA replay comparison.

Integration entrypoint for the already callable Android goal demonstration (#1755)
and its existing replay-ablation implementation (#1752). This is deliberately
NOT a new learner or a trusted T8/native Android transition adapter.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .android_control_sim import SimulatedAndroidWorld
from .android_goal_learning_demo import run_demo
from .android_sim_jepa_probe import replay_ablation


def run_goal_replay(home, *, first=0, count=18, seed=17, steps=5):
    """Execute actual simulator tasks, reopen persisted receipts and measure replay.

    No real Android dispatch, native permissions, trusted T8 writes, body weight
    updates or active model promotion. The comparison fits actual NumPy JEPA
    weights from committed synthetic receipts with ID/content-disjoint old test.
    """
    if (type(seed) is not int or not 0 <= seed <= 2**63-1
            or type(steps) is not int or not 1 <= steps <= 100):
        raise ValueError("invalid replay comparison budget")
    goal = run_demo(home, first=first, count=count, seed=seed, learn=False)
    if (goal["status"] != "SOFTWARE_SYNTHETIC_ONLY"
            or goal["native_android_executed"] is not False
            or goal["registered_t8_training_corpus_modified"] is not False):
        raise ValueError("refusing non-synthetic Android goal result")
    world = SimulatedAndroidWorld(home)
    try:
        replay = replay_ablation(world, seed=seed, steps=steps)
        if (replay["scope"] != "SYNTHETIC_UI_ONLY_NO_T8_SOURCE"
                or replay["source_ids_disjoint"] is not True
                or replay["both_models_changed_numeric_weights"] is not True
                or replay["native_android_executed"] is not False):
            raise ValueError("invalid replay provenance or fit")
        receipts = world.receipt_count()
        if receipts != goal["action_receipt_count"]:
            raise ValueError("source cursor changed between task and replay")
    finally:
        world.close()
    # The report intentionally does not contain user/simulated note text.
    return {
        "schema": "v13.android.goal_replay_retention/1",
        "status": "SHADOW_SYNTHETIC_REPLAY_ONLY",
        "goal": goal,
        "replay": replay,
        "replay_better": replay["replay_better_on_this_cohort"],
        "registered_t8_training_corpus_modified": False,
        "active_model_promoted": False,
        "native_android_executed": False,
        "android_device_verified": False,
        "body_weights_modified": False,
        "voice_adapter_weights_modified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Synthetic Android goal + WorldJEPA replay only")
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--first", type=int, default=0)
    parser.add_argument("--count", type=int, default=18)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--simulation-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run_goal_replay(args.home, first=args.first, count=args.count,
                                    seed=args.seed, steps=args.steps),
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
