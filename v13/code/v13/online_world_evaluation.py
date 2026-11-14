"""Disjoint trusted-T8 evaluation of the existing persistent local predictor.

Opt-in offline experiment only. Does not train a GGUF, EMA encoder, or native
Android runtime. Input rows must already have passed world_model.transitions
provenance validation; this function never reads or uploads private episodes.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from .online_world import OnlineWorld
from .continuous_predictor import OnlinePredictor
from . import world_model


def evaluate_disjoint(train_rows, holdout_rows, *, lr=0.02, replay=128):
    """Compare replay/no-replay against an untrained baseline on unseen T8 IDs.

    Both groups are copied into independent temporary predictor homes. Neither
    holdout labels nor identifiers enter a training checkpoint or replay pool.
    """
    train = list(train_rows)
    holdout = list(holdout_rows)
    if not train or not holdout:
        raise ValueError("Nonempty train and holdout required")
    ids_train = [r["action_id"] for r in train]
    ids_holdout = [r["action_id"] for r in holdout]
    if (any(type(i) is not str or not i for i in ids_train + ids_holdout)
            or len(set(ids_train + ids_holdout)) != len(ids_train) + len(ids_holdout)):
        raise ValueError("Duplicate or overlapping trusted T8 action identifiers")
    training = [OnlineWorld.encode(r) for r in train]
    testing = [OnlineWorld.encode(r) for r in holdout]
    with TemporaryDirectory(prefix="v13-jepa-eval-") as root:
        outcomes = {}
        for label, rehearsals in (("replay_off", 0), ("replay_on", 2)):
            home = Path(root) / label
            model = OnlinePredictor(7, len(world_model.ACTIONS), home, lr=lr, replay=replay)
            baseline = model.error(testing)
            for x, a, y in training:
                model.observe(x, a, y, rehearsals=rehearsals)
            after = model.error(testing)
            model.checkpoint(processed_ids=ids_train[-world_model.MAX_ROWS:])
            restarted = OnlinePredictor(7, len(world_model.ACTIONS), home, lr=lr, replay=replay)
            restart_loss = restarted.error(testing)
            if not np.isclose(after, restart_loss, rtol=1e-12, atol=1e-12):
                raise AssertionError("Predictor checkpoint changed heldout loss")
            outcomes[label] = {
                "holdout_mse_before": baseline,
                "holdout_mse_after": after,
                "holdout_mse_delta": after - baseline,
                "restart_holdout_mse": restart_loss,
                "trained": model.seen,
                "optimizer_steps": model.updates,
                "checkpoint_cursor_count": len(restarted.checkpoint_processed or []),
            }
    return {"status": "SYNTHETIC_OR_OFFLINE_LOCAL_PREDICTOR_NOT_FULL_JEPA",
            "train_count": len(train), "holdout_count": len(holdout),
            "disjoint_action_ids": True, "ablations": outcomes}
