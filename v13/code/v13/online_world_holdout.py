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
    # Frozen action-conditioned mean baseline: fit only on train transitions.
    # Unlike the untrained predictor, this is a meaningful independent
    # comparator and never sees holdout targets or replay samples.
    action_targets = {}
    for _, action, target in training:
        action_targets.setdefault(action, []).append(target)
    global_targets = [target for _, _, target in training]
    def mean_target(targets):
        return [sum(t[j] for t in targets) / len(targets)
                for j in range(len(targets[0]))]
    global_mean = mean_target(global_targets)
    action_means = {action: mean_target(targets)
                    for action, targets in action_targets.items()}
    def baseline_mse(samples):
        # OnlineWorld targets are [unchanged state(4), outcome(3)].
        # A fair no-learning comparator copies the observed state exactly
        # and estimates only the unknown outcome from training action means.
        # Otherwise the baseline is penalized for ignoring information
        # already present in every predictor input.
        errors = []
        for state, action, target in samples:
            mean = action_means.get(action, global_mean)
            prediction = list(state[:4]) + list(mean[4:])
            errors.extend((float(a)-float(b))**2
                          for a, b in zip(prediction, target))
        return sum(errors) / len(errors)
    frozen_baseline = baseline_mse(testing)
    # Only the last three coordinates are unknown action outcomes.
    # The first four are the unchanged state already supplied as input.
    def outcome_mse(model, samples):
        errors = []
        for state, action, target in samples:
            prediction = model.predict(state, action)
            errors.extend((float(prediction[j])-float(target[j]))**2
                          for j in range(4, 7))
        return sum(errors) / len(errors)
    frozen_outcome_baseline = frozen_baseline * 7 / 3
    # Independent early retention cohort: never observed or replayed.
    early_testing = testing[:max(1, len(testing)//2)]
    result = {"status": "SYNTHETIC_OR_T8_OFFLINE_ONLY",
              "train": len(train), "holdout": len(holdout),
              "frozen_action_mean_baseline_mse": frozen_baseline,
              "frozen_outcome_baseline_mse": frozen_outcome_baseline,
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
                outcome_before = outcome_mse(model, testing)
                old = training[:max(1, len(training)//4)]
                old_before = model.error(old)
                early_count = max(1, len(training)//4)
                for x, action, y in training[:early_count]:
                    model.observe(x, action, y, rehearsals=rehearsals)
                early_after_initial_learning = model.error(old)
                early_holdout_after_initial = model.error(early_testing)
                for x, action, y in training[early_count:]:
                    model.observe(x, action, y, rehearsals=rehearsals)
                after = model.error(testing)
                outcome_after = outcome_mse(model, testing)
                old_after = model.error(old)
                early_holdout_after_later = model.error(early_testing)
                model.checkpoint()
                restored = OnlinePredictor(7, len(world_model.ACTIONS),
                                           directory, lr=lr, replay=replay)
                restart_error = restored.error(testing)
                outcome_restart = outcome_mse(restored, testing)
                if not math.isclose(after, restart_error,
                                    rel_tol=1e-10, abs_tol=1e-10):
                    raise AssertionError("Predictor restart changed holdout")
                if not math.isclose(outcome_after, outcome_restart, rel_tol=1e-10, abs_tol=1e-10):
                    raise AssertionError("Restart changed outcome holdout")
                result[name] = {
                    "outcome_before_mse": outcome_before,
                    "outcome_after_mse": outcome_after,
                    "outcome_restart_mse": outcome_restart,
                    "before_mse": before, "after_mse": after,
                    "delta_mse": after-before,
                    "early_train_mse_before": old_before,
                    "early_train_mse_after": old_after,
                    "early_train_delta_mse": old_after-old_before,
                    "early_after_initial_learning_mse": early_after_initial_learning,
                    "early_forgetting_mse": old_after-early_after_initial_learning,
                    "early_holdout_mse_after_initial": early_holdout_after_initial,
                    "early_holdout_mse_after_later": early_holdout_after_later,
                    "early_holdout_retention_delta_mse": (
                        early_holdout_after_later-early_holdout_after_initial),
                    "restart_mse": restart_error,
                    "numeric_updates": model.updates}
        result["elapsed_s"] = time.monotonic()-start
        result["python_peak_bytes"] = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    result["replay_minus_no_replay_holdout_mse"] = (
        result["replay"]["after_mse"]-result["no_replay"]["after_mse"])
    # Diagnostic only: a positive value means later updates degraded the
    # previously learned early cohort. This is not a held-out retention proof.
    result["replay_minus_no_replay_early_forgetting_mse"] = (
        result["replay"]["early_forgetting_mse"] -
        result["no_replay"]["early_forgetting_mse"])
    result["replay_minus_no_replay_early_holdout_retention_delta_mse"] = (
        result["replay"]["early_holdout_retention_delta_mse"] -
        result["no_replay"]["early_holdout_retention_delta_mse"])
    result["utility_proven"] = (
        result["replay"]["outcome_after_mse"] < result["replay"]["outcome_before_mse"]
        and result["replay"]["outcome_after_mse"] < frozen_outcome_baseline)
    result["predictor_beats_frozen_baseline"] = (
        result["replay"]["outcome_after_mse"] < frozen_outcome_baseline)
    return result


def evaluate_runtime(runtime, *, limit=2048):
    """Read the real provenance-checked T8 consumer; never train live weights."""
    return evaluate_rows(world_model.transitions(runtime.store, limit=limit))
