"""Tiny WorldJEPA weight-learning probe using ONLY synthetic UI-world receipts.

This never runs on live Android observations or modifies B1/B2/C3/GGUF weights.
It trains numeric JEPA encoder/predictor/EMA weights on real committed simulator
transitions, enforces disjoint input/action holdouts, and reports before/after
heldout loss (not a guaranteed improvement). NumPy is imported only on use.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

from .android_control_sim import CAPABILITY_ORDER

MIN_TRAIN = 8
MIN_HELDOUT = 4
SHA256_HEX = re.compile(r"[0-9a-f]{64}\Z")
ACTION_ID = re.compile(r"[0-9a-f]{32}\Z")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _validate(rows):
    if type(rows) is not list or not 12 <= len(rows) <= 2048:
        raise ValueError("at least 12 bounded synthetic UI transitions required")
    unique, ids = {}, set()
    for row in rows:
        if type(row) is not dict or set(row) != {
            "action_id", "scope", "x", "a", "x2", "before_sha256", "after_sha256"
        }:
            raise ValueError("invalid simulator transition receipt")
        aid = row["action_id"]
        if (row["scope"] != "SYNTHETIC_UI_ONLY"
                or type(aid) is not str or not ACTION_ID.fullmatch(aid)
                or aid in ids
                or type(row["a"]) is not int or not 0 <= row["a"] < len(CAPABILITY_ORDER)
                or any(type(v) is not str or not SHA256_HEX.fullmatch(v) for v in (
                    row["before_sha256"], row["after_sha256"]
                ))):
            raise ValueError("not a unique grounded synthetic transition")
        ids.add(aid)
        for name in ("x", "x2"):
            values = row[name]
            if (type(values) is not list or len(values) != 4
                    or any(type(x) is not float or not math.isfinite(x)
                           or not 0.0 <= x <= 1.0 for x in values)):
                raise ValueError("nonfinite or invalid simulator feature vector")
        # Equal state+action inputs cannot straddle train/heldout even if
        # their action IDs or target states differ.
        key = hashlib.sha256(_canonical([row["x"], row["a"]])).hexdigest()
        if key not in unique:
            unique[key] = row
    return unique


def _groups(rows):
    """Deterministic stratified exact-hash split, strictly disjoint by x+action."""
    unique = _validate(rows)
    by_action = {i: [] for i in range(len(CAPABILITY_ORDER))}
    for key, row in sorted(unique.items()):
        by_action[row["a"]].append((key, row))
    train, holdout = [], []
    for action, items in by_action.items():
        if len(items) >= 4:
            boundary = max(1, len(items)//5)
            holdout.extend(items[:boundary])
            train.extend(items[boundary:])
        else:
            train.extend(items)
    if len(train) < MIN_TRAIN or len(holdout) < MIN_HELDOUT:
        raise ValueError("not enough disjoint synthetic train/heldout support")
    if set(k for k,_ in train) & set(k for k,_ in holdout):
        raise ValueError("synthetic holdout contains training inputs")
    return train, holdout


def _arrays(groups):
    import numpy as np
    x = np.array([row["x"] for _, row in groups], dtype=np.float64)
    action = np.zeros((len(groups), len(CAPABILITY_ORDER)), dtype=np.float64)
    for i, (_, row) in enumerate(groups):
        action[i, row["a"]] = 1.0
    target = np.array([row["x2"] for _, row in groups], dtype=np.float64)
    return x, action, target


def trial(world, *, seed=17, steps=8, limit=2048, checkpoint=None):
    """Measure actual tiny model-weight delta, then optional inference export."""
    if type(seed) is not int or not 0 <= seed <= 2**63-1:
        raise ValueError("invalid synthetic JEPA seed")
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("synthetic JEPA fit budget must be 1..100")
    if type(limit) is not int or not 12 <= limit <= 2048:
        raise ValueError("synthetic JEPA source limit must be 12..2048")
    from .world_jepa import WorldJEPA
    import numpy as np
    rows = world.transitions(limit=limit)
    train, heldout = _groups(rows)
    source_sha = hashlib.sha256(_canonical([
        [key, row["action_id"], row["before_sha256"],
         row["after_sha256"], row["x2"]]
        for key, row in train + heldout
    ])).hexdigest()
    x, a, y = _arrays(train)
    hx, ha, hy = _arrays(heldout)
    model = WorldJEPA(seed=seed, ensemble=2)
    # Baseline is after a small *actual* fit, not an untrained prediction
    # whose target encoder would still be undefined.
    model.fit(x, a, y, steps=3, log_every=1)
    old = model.enc["W1"].copy()
    before = model.prediction_loss(hx, ha, hy)
    model.partial_fit(x, a, y, steps=steps, log_every=max(1, steps//3))
    after = model.prediction_loss(hx, ha, hy)
    moved = not np.array_equal(old, model.enc["W1"])
    if not np.isfinite(before) or not np.isfinite(after) or not moved:
        raise ValueError("synthetic JEPA did not produce finite real updates")
    result = {
        "kind": "SYNTHETIC_UI_JEPA_PROBE",
        "scope": "SYNTHETIC_UI_ONLY_NO_T8_SOURCE",
        "train_rows": len(train), "holdout_rows": len(heldout),
        "verified_input_disjointness": True,
        "source_sha256": source_sha, "seed": seed,
        "fit_steps": int(model._fit_steps),
        "encoder_weights_changed": moved,
        "heldout_loss_before": float(before),
        "heldout_loss_after": float(after),
        "heldout_delta": float(after-before),
        "guaranteed_holdout_improvement": False,
        "native_android_executed": False,
        "b1_b2_c3_gguf_weights_modified": False,
        "registered_t8_training_corpus_modified": False,
        "active_model_promoted": False,
    }
    if checkpoint is not None:
        from .world_jepa_shadow_checkpoint import save, load
        saved = save(model, checkpoint, source_sha)
        replay = load(checkpoint, source_sha, saved["sha256"])
        restarted = replay.prediction_loss(hx, ha, hy)
        if not np.isclose(restarted, after, rtol=1e-9, atol=1e-12):
            raise ValueError("synthetic JEPA inference checkpoint changed holdout loss")
        result["readback"] = {
            "checkpoint_sha256": saved["sha256"],
            "inference_reload_exact_loss": True,
            "optimizer_trajectory_reproduced": False,
        }
    return result



def replay_ablation(world, *, seed=17, steps=5, limit=2048):
    """Measure old-cohort forgetting with and without bounded synthetic replay.

    Two models start from identical old-cohort weights; one sees only new
    observations, the other also replays part of old training data. The old
    evaluation cohort remains unseen by both. This comparison is NOT a
    guaranteed improvement, a causal AGI demonstration, or a live T8 test.
    """
    if type(seed) is not int or not 0 <= seed <= 2**63-1:
        raise ValueError("invalid synthetic JEPA seed")
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("synthetic replay step budget must be 1..100")
    if type(limit) is not int or not 24 <= limit <= 2048:
        raise ValueError("synthetic replay source limit must be 24..2048")
    import numpy as np
    from .world_jepa import WorldJEPA
    unique = list(_validate(world.transitions(limit=limit)).items())
    split = (len(unique) * 2) // 3
    old, recent = unique[:split], unique[split:]
    old_test = [item for i,item in enumerate(old) if i % 5 == 0]
    old_train = [item for i,item in enumerate(old) if i % 5 != 0]
    if len(old_test) < 4 or len(old_train) < 8 or len(recent) < 8:
        raise ValueError("not enough disjoint old/new synthetic replay data")
    all_inputs = [key for key,_ in old_train+old_test+recent]
    if len(all_inputs) != len(set(all_inputs)):
        raise ValueError("synthetic replay/holdout identity overlap")
    x, a, y = _arrays(old_train)
    nx, na, ny = _arrays(recent)
    hx, ha, hy = _arrays(old_test)
    # Strictly deterministic initial seed and identical initial data.
    without = WorldJEPA(seed=seed, ensemble=2).fit(
        x, a, y, steps=4, log_every=1)
    with_replay = WorldJEPA(seed=seed, ensemble=2).fit(
        x, a, y, steps=4, log_every=1)
    before = without.prediction_loss(hx, ha, hy)
    if not np.isclose(before, with_replay.prediction_loss(hx,ha,hy),
                      atol=1e-12, rtol=0):
        raise ValueError("replay control groups did not share starting weights")
    replay = old_train[::2]
    rx, ra, ry = _arrays(replay)
    prior_without = without.enc["W1"].copy()
    prior_with = with_replay.enc["W1"].copy()
    without.partial_fit(nx, na, ny, steps=steps, log_every=max(1,steps//3))
    with_replay.partial_fit(
        np.concatenate((nx,rx)), np.concatenate((na,ra)),
        np.concatenate((ny,ry)), steps=steps, log_every=max(1,steps//3))
    plain = without.prediction_loss(hx, ha, hy)
    replayed = with_replay.prediction_loss(hx, ha, hy)
    if (not np.all(np.isfinite([before,plain,replayed]))
            or np.array_equal(prior_without, without.enc["W1"])
            or np.array_equal(prior_with, with_replay.enc["W1"])):
        raise ValueError("synthetic replay ablation failed numeric weight update")
    source_sha = hashlib.sha256(_canonical([
        [key,row["action_id"],row["before_sha256"],
         row["after_sha256"],row["x2"]] for key,row in unique
    ])).hexdigest()
    return {
        "kind": "SYNTHETIC_UI_REPLAY_ABLATION",
        "scope": "SYNTHETIC_UI_ONLY_NO_T8_SOURCE",
        "source_sha256": source_sha,
        "initial_train_rows": len(old_train),
        "old_disjoint_holdout_rows": len(old_test),
        "new_train_rows": len(recent),
        "replayed_prior_rows": len(replay),
        "old_holdout_loss_before": float(before),
        "without_replay_loss_after": float(plain),
        "with_replay_loss_after": float(replayed),
        "forgetting_delta_without_replay": float(plain-before),
        "forgetting_delta_with_replay": float(replayed-before),
        "replay_better_on_this_cohort": bool(replayed < plain),
        "guaranteed_replay_superiority": False,
        "both_models_changed_numeric_weights": True,
        "source_ids_disjoint": True,
        "native_android_executed": False,
        "b1_b2_c3_gguf_weights_modified": False,
        "active_model_promoted": False,
    }
