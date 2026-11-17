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
    """Stable state/action-group disjoint split, independent of stream ordering."""
    train, holdout, ids = [], [], set()
    # Action-ID disjointness alone leaks repeated states into both cohorts.
    # Group the identical observed state/action pair before splitting; this
    # remains an offline evaluation and never changes live T8 admission.
    for row in rows:
        aid = row.get("action_id")
        if type(aid) is not str or not aid or aid in ids:
            raise ValueError("Missing or duplicate T8 action ID")
        ids.add(aid)
        # Validate through the production numeric encoder before hashing:
        # no untrusted NaN, shape mismatch or unknown action is admitted.
        x, action, _ = OnlineWorld.encode(row)
        import struct
        group = struct.pack("!i4d", action, *(float(v) for v in x[:4]))
        (holdout if hashlib.sha256(group).digest()[0] % 5 == 0
         else train).append(row)
    # Deterministic update order for reproducible ablation under reordered
    # T8 feeds. This is NOT a temporal cohort; no trusted timestamp is
    # available in this interface.
    train.sort(key=lambda row: row["action_id"])
    holdout.sort(key=lambda row: row["action_id"])
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
    # Count independent state/action groups, not repeated event IDs.
    # Repeated transitions cannot manufacture a statistically useful holdout.
    def independent_groups(cohort):
        import struct
        return len({struct.pack("!i4d", action, *(float(v) for v in x[:4]))
                    for x, action, _ in (OnlineWorld.encode(row) for row in cohort)})
    train_groups = independent_groups(train)
    holdout_groups = independent_groups(holdout)
    if train_groups < 8 or holdout_groups < 3:
        return {"status": "INSUFFICIENT_INDEPENDENT_T8_GROUPS",
                "train": len(train), "holdout": len(holdout),
                "train_groups": train_groups, "holdout_groups": holdout_groups}
    # Keep training evidence group-balanced too: repeated receipts from the
    # same observed state/action must not multiply optimizer updates. Conflicting
    # outcomes remain visible in the group's mean, rather than arbitrarily
    # selecting the first receipt. This is offline evaluation only.
    import struct
    grouped_training = {}
    for row in train:
        state, action, target = OnlineWorld.encode(row)
        key = struct.pack("!i4d", action, *(float(v) for v in state[:4]))
        if key not in grouped_training:
            grouped_training[key] = [state, action, [0.0] * len(target), 0]
        item = grouped_training[key]
        item[2] = [a + float(b) for a, b in zip(item[2], target)]
        item[3] += 1
    training = [(state, action, [v / count for v in totals])
                for _, (state, action, totals, count) in sorted(grouped_training.items())]
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
    # Evaluation unit is a distinct state/action group, not an event row.
    # A duplicated T8 receipt must not alter the reported generalization
    # score. Within-group repetitions are averaged before the group mean.
    import struct
    def group_mse(samples, predict, *, outcome_only=True):
        groups = {}
        for state, action, target in samples:
            key = struct.pack("!i4d", action, *(float(v) for v in state[:4]))
            predicted = predict(state, action)
            indices = range(4, 7) if outcome_only else range(7)
            error = sum((float(predicted[j])-float(target[j]))**2
                        for j in indices) / len(indices)
            total, count = groups.get(key, (0.0, 0))
            groups[key] = (total + error, count + 1)
        return sum(total/count for total, count in groups.values()) / len(groups)
    def action_mean_predict(state, action):
        mean = action_means.get(action, global_mean)
        return list(state[:4]) + list(mean[4:])
    balanced_frozen_outcome = group_mse(testing, action_mean_predict)
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
    # Training-only nearest-state comparator: a non-gradient learner can
    # exploit state-dependent outcomes too. Never treat beating only an
    # action mean as proof of learned transition utility.
    # Index the immutable training cohort once. The former implementation
    # rebuilt an action-filtered list for every holdout row, adding repeated
    # allocations and scans on the memory-constrained Android target.
    by_action = {}
    for sample in training:
        by_action.setdefault(sample[1], []).append(sample)

    def nearest_state_outcome_mse(samples):
        errors = []
        for state, action, target in samples:
            pool = by_action.get(action) or training
            nearest = min(pool, key=lambda r: sum(
                (float(r[0][j]) - float(state[j])) ** 2 for j in range(4)))
            errors.extend((float(nearest[2][j]) - float(target[j])) ** 2
                          for j in range(4, 7))
        return sum(errors) / len(errors)
    nearest_state_baseline = nearest_state_outcome_mse(testing)
    def nearest_predict(state, action):
        pool = by_action.get(action) or training
        return min(pool, key=lambda r: sum(
            (float(r[0][j]) - float(state[j])) ** 2 for j in range(4)))[2]
    balanced_nearest_outcome = group_mse(testing, nearest_predict)
    # Independent early retention cohort: never observed or replayed.
    early_testing = testing[:max(1, len(testing)//2)]
    result = {"status": "SYNTHETIC_OR_T8_OFFLINE_ONLY",
              "train": len(train), "holdout": len(holdout),
              "train_groups": train_groups, "holdout_groups": holdout_groups,
              "frozen_action_mean_baseline_mse": frozen_baseline,
              "frozen_outcome_baseline_mse": frozen_outcome_baseline,
              "nearest_state_outcome_baseline_mse": nearest_state_baseline,
              "group_balanced_frozen_outcome_baseline_mse": balanced_frozen_outcome,
              "group_balanced_nearest_outcome_baseline_mse": balanced_nearest_outcome,
              "retention_cohort_temporal": False,
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
                balanced_before = group_mse(testing, model.predict)
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
                balanced_after = group_mse(testing, model.predict)
                old_after = model.error(old)
                early_holdout_after_later = model.error(early_testing)
                model.checkpoint()
                restored = OnlinePredictor(7, len(world_model.ACTIONS),
                                           directory, lr=lr, replay=replay)
                restart_error = restored.error(testing)
                outcome_restart = outcome_mse(restored, testing)
                balanced_restart = group_mse(testing, restored.predict)
                if not math.isclose(balanced_after, balanced_restart,
                                    rel_tol=1e-10, abs_tol=1e-10):
                    raise AssertionError("Restart changed balanced outcome holdout")
                if not math.isclose(after, restart_error,
                                    rel_tol=1e-10, abs_tol=1e-10):
                    raise AssertionError("Predictor restart changed holdout")
                if not math.isclose(outcome_after, outcome_restart, rel_tol=1e-10, abs_tol=1e-10):
                    raise AssertionError("Restart changed outcome holdout")
                result[name] = {
                    "group_balanced_outcome_before_mse": balanced_before,
                    "group_balanced_outcome_after_mse": balanced_after,
                    "group_balanced_outcome_restart_mse": balanced_restart,
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
    # Claim gate uses independent groups. Row-weighted metrics remain
    # diagnostic for historical comparisons, never acceptance evidence.
    result["utility_proven"] = (
        result["replay"]["group_balanced_outcome_after_mse"] <
        result["replay"]["group_balanced_outcome_before_mse"]
        and result["replay"]["group_balanced_outcome_after_mse"] <
        balanced_frozen_outcome
        and result["replay"]["group_balanced_outcome_after_mse"] <
        balanced_nearest_outcome)
    result["predictor_beats_frozen_baseline"] = (
        result["replay"]["group_balanced_outcome_after_mse"] <
        balanced_frozen_outcome)
    return result


def evaluate_runtime(runtime, *, limit=2048):
    """Read the real provenance-checked T8 consumer; never train live weights."""
    return evaluate_rows(world_model.transitions(runtime.store, limit=limit))
