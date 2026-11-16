"""Offline, source-bound OnlineWorld retention/ablation evaluator.

Only committed T8 transitions from world_model.transitions() may enter this
consumer. No active Runtime predictor, cursor, Age gate or GGUF is modified.
This is an evaluator of the local numeric predictor, not full JEPA.
"""
import hashlib
import math
import tempfile
import time
import tracemalloc
from pathlib import Path

from . import world_model
from .continuous_predictor import OnlinePredictor
from .online_world import OnlineWorld


def partition(rows):
    """Stable action-ID disjoint split, independent of stream ordering."""
    train, holdout, ids = [], [], set()
    for row in rows:
        aid = row.get("action_id")
        if type(aid) is not str or not aid or aid in ids:
            raise ValueError("Missing or duplicate T8 action ID")
        ids.add(aid)
        (holdout if hashlib.sha256(aid.encode()).digest()[0] % 5 == 0
         else train).append(row)
    return train, holdout


def evaluate_rows(rows, *, lr=0.02, replay=128):
    """Return measured holdout utility, replay ablation and restart proof.

    Rows must originate from the trusted T8 admission consumer, not model
    guesses. A separate temporary predictor is trained for each ablation.
    No holdout label is used in observe() or rehearsal reservoir.
    """
    train, holdout = partition(rows)
    if len(train) < 8 or len(holdout) < 3:
        return {"status": "INSUFFICIENT_DISJOINT_T8",
                "train": len(train), "holdout": len(holdout)}
    training = [OnlineWorld.encode(row) for row in train]
    testing = [OnlineWorld.encode(row) for row in holdout]
    result = {"status": "SYNTHETIC_OR_T8_OFFLINE_ONLY",
              "train": len(train), "holdout": len(holdout),
              "holdout_ids_sha256": hashlib.sha256(
                  "\n".join(sorted(r["action_id"] for r in holdout)).encode()
              ).hexdigest()}
    tracemalloc.start()
    start = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="v13-t8-eval-") as home:
            for name, rehearsals in (("no_replay", 0), ("replay", 2)):
                directory = Path(home) / name
                model = OnlinePredictor(7, len(world_model.ACTIONS),
                                        directory, lr=lr, replay=replay)
                before = model.error(testing)
                old = training[:max(1, len(training)//4)]
                old_before = model.error(old)
                for x, action, y in training:
                    model.observe(x, action, y, rehearsals=rehearsals)
                after = model.error(testing)
                old_after = model.error(old)
                model.checkpoint()
                restored = OnlinePredictor(7, len(world_model.ACTIONS),
                                           directory, lr=lr, replay=replay)
                restart_error = restored.error(testing)
                if not math.isclose(after, restart_error,
                                    rel_tol=1e-10, abs_tol=1e-10):
                    raise AssertionError("Predictor restart changed holdout")
                result[name] = {
                    "before_mse": before, "after_mse": after,
                    "delta_mse": after-before,
                    "early_train_mse_before": old_before,
                    "early_train_mse_after": old_after,
                    "early_train_delta_mse": old_after-old_before,
                    "restart_mse": restart_error,
                    "numeric_updates": model.updates}
        result["elapsed_s"] = time.monotonic()-start
        result["python_peak_bytes"] = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    result["replay_minus_no_replay_holdout_mse"] = (
        result["replay"]["after_mse"]-result["no_replay"]["after_mse"])
    result["utility_proven"] = (
        result["replay"]["after_mse"] < result["replay"]["before_mse"])
    return result


def evaluate_runtime(runtime, *, limit=2048):
    """Read the real provenance-checked T8 consumer; never train live weights."""
    return evaluate_rows(world_model.transitions(runtime.store, limit=limit))
