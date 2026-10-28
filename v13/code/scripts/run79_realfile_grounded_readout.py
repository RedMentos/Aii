#!/usr/bin/env python3
"""Run79 preregistered real-file supervised grounded readout for slot-wise JEPA.

SHADOW diagnostic on isolated temporary Linux file actions. No runtime use,
native weights, tool authority, Redmi measurement, or acceptance promotion.
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
from scripts import run78_realfile_ensemble_comparison as run78
from scripts import z12b_world_jepa as world
from v13.world_jepa_slots_isolated import SlotWorldJEPA
from v13.world_jepa_slots_mean_candidate import EnsembleMeanSlotWorldJEPA

SCHEMA = "v13.run79.realfile_slotwise_grounded_readout_shadow.v1"
SEEDS = (431, 433, 439)
N_TRAIN = 240
N_TEST = 60
STEPS = 240
ENSEMBLE = 3
RIDGE = 0.01
PARENT_SHA = "7f7cdc1a9c35a72267955f20e3b6480a717650c2"


def _predicted(model, x, actions, *, member0):
    if member0:
        z, _ = SlotWorldJEPA.predict(model, x, actions)
    else:
        z, _ = model.predict(x, actions)
    if z.shape != (len(x), world.SLOTS, model.k) or not np.isfinite(z).all():
        raise ValueError("RUN79_BAD_PREDICTED_LATENTS")
    return z.reshape(len(x), -1)


def _fit_readout(predicted_train, train_targets):
    """Train-only supervised ridge; no test outcome enters this function."""
    if (predicted_train.ndim != 2 or train_targets.ndim != 2
            or len(predicted_train) != len(train_targets)
            or len(predicted_train) < 2
            or train_targets.shape[1] != fixture.FEATURES
            or not np.isfinite(predicted_train).all()
            or not np.isfinite(train_targets).all()):
        raise ValueError("RUN79_BAD_READOUT_TRAIN")
    return fixture._ridge(np.c_[np.ones(len(predicted_train)), predicted_train],
                          train_targets)


def _decode(predicted, weights):
    features = np.c_[np.ones(len(predicted)), predicted]
    if features.shape[1] != weights.shape[0]:
        raise ValueError("RUN79_BAD_READOUT_SHAPE")
    result = features @ weights
    if not np.isfinite(result).all():
        raise ValueError("RUN79_NONFINITE_GROUNDED_OUTPUT")
    return result


def _metrics(predicted, target, target_slots):
    if (predicted.shape != target.shape
            or predicted.shape[1] != fixture.FEATURES
            or len(target_slots) != len(target)
            or not np.isfinite(predicted).all()
            or not np.isfinite(target).all()):
        raise ValueError("RUN79_INVALID_OUTCOMES")
    err = (predicted - target) ** 2
    touched = np.array([
        err[i, slot*fixture.SLOT_FEATURES:(slot+1)*fixture.SLOT_FEATURES].mean()
        for i, slot in enumerate(target_slots)
    ])
    return {"overall_mse": float(err.mean()),
            "target_slot_mse": float(touched.mean())}


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_test=N_TEST, steps=STEPS):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_test) is not int or n_test != N_TEST
            or type(steps) is not int or steps != STEPS):
        raise PermissionError("RUN79_UNREGISTERED_COHORT")
    reports = []
    for seed in seeds:
        held = tuple(sorted(random.Random(seed).sample(fixture.NON_NOOP, 4)))
        train = fixture._rows(seed, held, n_train, test=False)
        test = fixture._rows(seed, held, n_test, test=True)
        if (len(train) != n_train or len(test) != n_test
                or any(r[1] in held for r in train)
                or any(r[1] not in held for r in test)):
            raise ValueError("RUN79_SPLIT_CONTAMINATION")
        x, a, y = run78._action_rows(train)
        xt, at, yt = run78._action_rows(test)
        slots = np.asarray([world.ACTIONS[r[1]][1] for r in test], dtype=int)
        model = EnsembleMeanSlotWorldJEPA(world.SLOTS, seed=seed, ensemble=ENSEMBLE)
        model.fit(x, a, y, steps=steps)
        train_first = _predicted(model, x, a, member0=True)
        train_mean = _predicted(model, x, a, member0=False)
        first_w = _fit_readout(train_first, y)
        mean_w = _fit_readout(train_mean, y)
        test_first = _predicted(model, xt, at, member0=True)
        test_mean = _predicted(model, xt, at, member0=False)
        perm = np.random.default_rng(seed + 7000).permutation(n_test)
        test_shuffled = _predicted(model, xt, at[perm], member0=False)
        scores = {
            "member0": _metrics(_decode(test_first, first_w), yt, slots),
            "ensemble_mean": _metrics(_decode(test_mean, mean_w), yt, slots),
            "ensemble_mean_shuffled_test_action":
                _metrics(_decode(test_shuffled, mean_w), yt, slots),
            "slot_local_ridge": fixture._evaluate(train, test)["slot_local_ridge"],
        }
        reports.append({
            "seed": seed,
            "heldout_action_indices": list(held),
            "train_sha256": run78._digest(x, a, y),
            "holdout_sha256": run78._digest(xt, at, yt),
            "test_action_permutation_sha256": hashlib.sha256(
                np.asarray(perm, dtype="<i8").tobytes()).hexdigest(),
            "n_train": n_train, "n_test": n_test,
            "train_changed_count": sum(not np.array_equal(r[0], r[2]) for r in train),
            "test_changed_count": sum(not np.array_equal(r[0], r[2]) for r in test),
            "scores": scores,
        })
    names = tuple(reports[0]["scores"])
    aggregate = {
        name: {key: float(np.mean([r["scores"][name][key] for r in reports]))
               for key in ("overall_mse", "target_slot_mse")}
        for name in names
    }
    first = aggregate["member0"]["target_slot_mse"]
    mean = aggregate["ensemble_mean"]["target_slot_mse"]
    ratio = (first - mean) / max(first, 1e-12)
    report = {
        "schema": SCHEMA,
        "status": "SUPERVISED_GROUNDED_REALFILE_SHADOW_ONLY",
        "parent_sha": PARENT_SHA,
        "seeds": list(seeds),
        "n_train_per_seed": n_train,
        "n_test_per_seed": n_test,
        "steps": steps,
        "ensemble": ENSEMBLE,
        "ridge_lambda": RIDGE,
        "reports": reports,
        "aggregate": aggregate,
        "mean_vs_member0_target_slot_improvement_ratio": float(ratio),
        "exploratory_criterion": bool(
            ratio >= 0.05
            and all(r["scores"]["ensemble_mean"]["target_slot_mse"]
                    <= r["scores"]["member0"]["target_slot_mse"] for r in reports)
            and mean < aggregate["ensemble_mean_shuffled_test_action"]["target_slot_mse"]
            and mean < aggregate["slot_local_ridge"]["target_slot_mse"]),
        "real_temporary_file_actions_executed": True,
        "supervised_readout_used": True,
        "jepa_only_utility_proven": False,
        "source_disjointness_verified": False,
        "native_model_executed": False,
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
