"""Offline two-phase retention probe for the existing T8 numeric predictor.

This measures forgetting on an *earlier* disjoint cohort after training a later
cohort. It never reads phone data or enables runtime weight updates.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from .online_world import OnlineWorld
from .continuous_predictor import OnlinePredictor
from . import world_model


def evaluate_retention(old_rows, new_rows, old_holdout_rows, new_holdout_rows,
                       *, replay=128, lr=0.02):
    groups = [list(g) for g in (old_rows, new_rows, old_holdout_rows, new_holdout_rows)]
    if any(not group for group in groups):
        raise ValueError("All four cohorts must be nonempty")
    identifiers = [row["action_id"] for group in groups for row in group]
    if any(type(key) is not str or not key for key in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("Overlapping or invalid T8 action identifiers")
    old_train, new_train, old_test, new_test = [
        [OnlineWorld.encode(row) for row in group] for group in groups
    ]
    outcomes = {}
    with TemporaryDirectory(prefix="v13-retention-") as root:
        for label, rehearsals in (("replay_off", 0), ("replay_on", 2)):
            home = Path(root) / label
            model = OnlinePredictor(7, len(world_model.ACTIONS), home, lr=lr, replay=replay)
            baseline_old = model.error(old_test)
            baseline_new = model.error(new_test)
            for x, action, y in old_train:
                model.observe(x, action, y, rehearsals=rehearsals)
            old_after_first = model.error(old_test)
            new_after_first = model.error(new_test)
            for x, action, y in new_train:
                model.observe(x, action, y, rehearsals=rehearsals)
            old_after_second = model.error(old_test)
            new_after_second = model.error(new_test)
            model.checkpoint(processed_ids=[row["action_id"] for row in old_rows + new_rows][-world_model.MAX_ROWS:])
            restarted = OnlinePredictor(7, len(world_model.ACTIONS), home, lr=lr, replay=replay)
            if abs(restarted.error(old_test) - old_after_second) > 1e-12 or abs(restarted.error(new_test) - new_after_second) > 1e-12:
                raise AssertionError("Retention changed after checkpoint restart")
            outcomes[label] = {
                "old_holdout_before": baseline_old,
                "new_holdout_before": baseline_new,
                "old_holdout_after_phase1": old_after_first,
                "new_holdout_after_phase1": new_after_first,
                "old_holdout_after_phase2": old_after_second,
                "new_holdout_after_phase2": new_after_second,
                "old_forgetting_delta": old_after_second - old_after_first,
                "new_learning_delta": new_after_second - new_after_first,
                "optimizer_steps": model.updates,
                "checkpoint_cursor_count": len(restarted.checkpoint_processed or []),
                "restart_verified": True,
            }
    return {"status": "OFFLINE_LOCAL_PREDICTOR_NOT_JEPA_OR_ANDROID",
            "old_train_count": len(old_train), "new_train_count": len(new_train),
            "old_holdout_count": len(old_test), "new_holdout_count": len(new_test),
            "ablations": outcomes}
