#!/usr/bin/env python3
"""Run78 preregistered real temporary-file slot-wise JEPA aggregation comparison.

Software/isolated Linux SHADOW only; no Runtime, tools, native models, or gates.
The frozen model and prior registered cohorts are not modified.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import run60_z12b_slotlocal_real_file_baseline as fixture
from scripts import z12b_world_jepa as file_world
from v13.world_jepa_slots_isolated import SlotWorldJEPA
from v13.world_jepa_slots_mean_candidate import EnsembleMeanSlotWorldJEPA

SCHEMA = "v13.run78.realfile_ensemble_aggregation_shadow.v1"
SEEDS = (401, 409, 419)
TRAIN_N = 240
TEST_N = 60
STEPS = 240
ENSEMBLE = 3
PARENT_SHA = "cdb99f73c6d3af39ddd4e88dd8952cad636fed58"
FIXTURE_BLOB = "08063f3df630f558589dd297860dd19e0021dc90"
FILE_WORLD_BLOB = "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4"


def _action_rows(rows):
    x = np.stack([r[0] for r in rows]).astype(np.float64)
    y = np.stack([r[2] for r in rows]).astype(np.float64)
    a = np.zeros((len(rows), file_world.SLOTS, len(file_world.OPS) + 1), dtype=np.float64)
    a[:, :, -1] = 1.0
    for i, (_, action, _, _) in enumerate(rows):
        op, slot = file_world.ACTIONS[action]
        if slot is not None:
            a[i, slot, :] = 0.0
            a[i, slot, file_world.OPS.index(op)] = 1.0
    if x.shape != (len(rows), fixture.FEATURES) or y.shape != x.shape:
        raise ValueError("RUN78_BAD_FILE_FEATURES")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("RUN78_NONFINITE_FILE_FEATURES")
    if not (a.sum(axis=2) == 1).all():
        raise ValueError("RUN78_INVALID_ONEHOT")
    return x, a, y


def _digest(x, a, y):
    h = hashlib.sha256()
    for arr in (x, a, y):
        h.update(np.ascontiguousarray(arr, dtype="<f8").tobytes())
    return h.hexdigest()


def _equal_fit(old, new):
    for key in ("enc", "tgt"):
        for name, value in getattr(old, key).items():
            if not np.array_equal(value, getattr(new, key)[name]):
                raise AssertionError("RUN78_TRAINING_WEIGHTS_DIFFER")
    for a, b in zip(old.preds, new.preds):
        for name, value in a.items():
            if not np.array_equal(value, b[name]):
                raise AssertionError("RUN78_PREDICTOR_WEIGHTS_DIFFER")
    if len(old.preds) != ENSEMBLE or len(new.preds) != ENSEMBLE:
        raise AssertionError("RUN78_ENSEMBLE_SIZE")
    if not np.array_equal(old.zsd, new.zsd):
        raise AssertionError("RUN78_NORMALIZATION_DIFFER")


def _metrics(model, x, a, y, target_slots):
    errors = model.slot_errors(x, a, y)
    if errors.shape != (len(x), file_world.SLOTS) or not np.isfinite(errors).all():
        raise ValueError("RUN78_INVALID_ERRORS")
    return {
        "all_slot_mse": float(errors.mean()),
        "target_slot_mse": float(errors[np.arange(len(x)), target_slots].mean()),
    }


def run(*, seeds=SEEDS, train_n=TRAIN_N, test_n=TEST_N, steps=STEPS):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(train_n) is not int or train_n != TRAIN_N
            or type(test_n) is not int or test_n != TEST_N
            or type(steps) is not int or steps != STEPS):
        raise PermissionError("RUN78_UNREGISTERED_COHORT")
    reports = []
    for seed in seeds:
        held = tuple(sorted(random.Random(seed).sample(fixture.NON_NOOP, 4)))
        train = fixture._rows(seed, held, train_n, test=False)
        test = fixture._rows(seed, held, test_n, test=True)
        if (len(train) != train_n or len(test) != test_n
                or any(r[1] in held for r in train)
                or any(r[1] not in held for r in test)):
            raise ValueError("RUN78_SPLIT_CONTAMINATION")
        x, a, y = _action_rows(train)
        xt, at, yt = _action_rows(test)
        target_slots = np.asarray([file_world.ACTIONS[r[1]][1] for r in test], dtype=int)
        old = SlotWorldJEPA(file_world.SLOTS, seed=seed, ensemble=ENSEMBLE)
        new = EnsembleMeanSlotWorldJEPA(file_world.SLOTS, seed=seed, ensemble=ENSEMBLE)
        old.fit(x, a, y, steps=steps)
        new.fit(x, a, y, steps=steps)
        _equal_fit(old, new)
        member0 = _metrics(old, xt, at, yt, target_slots)
        mean = _metrics(new, xt, at, yt, target_slots)
        perm = np.random.default_rng(seed + 7000).permutation(test_n)
        shuffled = _metrics(new, xt, at[perm], yt, target_slots)
        improvement = ((member0["target_slot_mse"] - mean["target_slot_mse"])
                       / max(member0["target_slot_mse"], 1e-12))
        reports.append({
            "seed": seed,
            "heldout_action_indices": list(held),
            "train_sha256": _digest(x, a, y),
            "holdout_sha256": _digest(xt, at, yt),
            "action_permutation_sha256": hashlib.sha256(
                np.asarray(perm, dtype="<i8").tobytes()).hexdigest(),
            "train_count": train_n,
            "test_count": test_n,
            "train_changed_count": sum(not np.array_equal(r[0], r[2]) for r in train),
            "test_changed_count": sum(not np.array_equal(r[0], r[2]) for r in test),
            "weights_exactly_equal": True,
            "member0": member0,
            "ensemble_mean": mean,
            "mean_shuffled_action": shuffled,
            "target_slot_improvement_ratio": float(improvement),
        })
    member_mse = float(np.mean([r["member0"]["target_slot_mse"] for r in reports]))
    mean_mse = float(np.mean([r["ensemble_mean"]["target_slot_mse"] for r in reports]))
    shuffled_mse = float(np.mean([r["mean_shuffled_action"]["target_slot_mse"] for r in reports]))
    ratio = (member_mse - mean_mse) / max(member_mse, 1e-12)
    report = {
        "schema": SCHEMA,
        "status": "REAL_FILE_SHADOW_DIAGNOSTIC_ONLY",
        "parent_sha": PARENT_SHA,
        "fixture_blob": FIXTURE_BLOB,
        "file_world_blob": FILE_WORLD_BLOB,
        "seeds": list(seeds),
        "train_n": train_n,
        "test_n": test_n,
        "steps": steps,
        "ensemble": ENSEMBLE,
        "reports": reports,
        "aggregate": {
            "member0_target_slot_mse": member_mse,
            "ensemble_mean_target_slot_mse": mean_mse,
            "ensemble_mean_shuffled_target_slot_mse": shuffled_mse,
            "improvement_ratio": float(ratio),
            "exploratory_5pct_each_seed": bool(ratio >= 0.05 and all(
                r["target_slot_improvement_ratio"] >= 0 for r in reports)),
            "action_conditioning_positive": bool(mean_mse < shuffled_mse),
        },
        "real_temporary_file_actions_executed": True,
        "native_model_executed": False,
        "source_disjointness_verified": False,
        "grounded_outcome_utility_proven": False,
        "runtime_wired": False,
        "age_authority": 0,
        "learning_gate_pass": False,
        "jepa_weight": 0,
        "whole_system_complete": False,
    }
    json.dumps(report, allow_nan=False)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2, allow_nan=False))
