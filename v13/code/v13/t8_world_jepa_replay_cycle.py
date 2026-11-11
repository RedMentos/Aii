"""Source-grounded T8 -> WorldJEPA replay/retention -> private inference readback.

Uses actual committed V13 SQLite transitions via world_model.transitions. Unlike
android_sim_jepa_probe, this is the T8 digital route, not synthetic UI receipts.
The model is never promoted; inference checkpoint is not optimizer resume.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from . import world_model
from .world_jepa import WorldJEPA
from .world_jepa_action_outcome_adapter import build
from .world_jepa_shadow_checkpoint import save, load


def _arrays(rows):
    x = np.asarray([r["s"] + [0., 0., 0.] for r in rows], dtype=np.float64)
    a = np.asarray([world_model.onehot(r["a"]) for r in rows], dtype=np.float64)
    y = np.asarray([r["s"] + r["y"] for r in rows], dtype=np.float64)
    return x, a, y


def _concat(first, second):
    return tuple(np.concatenate((x, y), axis=0) for x, y in zip(first, second))


def run(store, checkpoint, *, seed=17, steps=5, limit=2048):
    """Train matched replay-on/off branches from the same trusted T8 read.

    This is a *one-shot* bounded experimental run, not an idle scheduler or
    permission grant. The caller must explicitly authorize Store reading and
    supply a fresh private checkpoint path. No user/source text is exported.
    """
    if (type(seed) is not int or not 0 <= seed <= 2**63-1
            or type(steps) is not int or not 1 <= steps <= 100
            or type(limit) is not int or not 32 <= limit <= world_model.MAX_ROWS):
        raise ValueError("invalid T8 replay budget")
    checkpoint = Path(checkpoint)
    if checkpoint.exists() or checkpoint.is_symlink():
        raise ValueError("T8 replay checkpoint destination must be fresh")
    rows = world_model.transitions(store, limit=limit)
    split = build(rows)  # provenance adapter: disjoint IDs/content/action support
    holdout_ids = set(split["holdout_action_ids"])
    train_rows = sorted((r for r in rows if r["action_id"] not in holdout_ids),
                        key=lambda r: r["action_id"])
    if len(train_rows) != len(split["train_action_ids"]):
        raise ValueError("T8 training split changed")
    boundary = (2 * len(train_rows)) // 3
    old, recent = train_rows[:boundary], train_rows[boundary:]
    if len(old) < 8 or len(recent) < 8:
        raise ValueError("insufficient distinct T8 replay phases")
    # Old retention is evaluated ONLY on the adapter's untouched holdout.
    old_arrays = _arrays(old)
    recent_arrays = _arrays(recent)
    holdout = split["holdout"]
    replay_rows = old[::2]
    replay_arrays = _arrays(replay_rows)
    if set(r["action_id"] for r in replay_rows) & holdout_ids:
        raise ValueError("T8 holdout leaked into replay")
    plain = WorldJEPA(seed=seed, ensemble=2).fit(*old_arrays, steps=4, log_every=1)
    replay = WorldJEPA(seed=seed, ensemble=2).fit(*old_arrays, steps=4, log_every=1)
    before = plain.prediction_loss(*holdout)
    if not np.isclose(before, replay.prediction_loss(*holdout), rtol=0, atol=1e-12):
        raise ValueError("T8 replay branches started differently")
    previous = replay.enc["W1"].copy()
    plain.partial_fit(*recent_arrays, steps=steps, log_every=max(1, steps // 3))
    replay.partial_fit(*_concat(recent_arrays, replay_arrays),
                       steps=steps, log_every=max(1, steps // 3))
    without = plain.prediction_loss(*holdout)
    with_replay = replay.prediction_loss(*holdout)
    if (not np.isfinite([before, without, with_replay]).all()
            or np.array_equal(previous, replay.enc["W1"])):
        raise ValueError("T8 replay failed numeric gradient update")
    source = split["manifest"]["all_rows_sha256"]
    saved = save(replay, checkpoint, source)
    restored = load(checkpoint, source, saved["sha256"])
    after_restart = restored.prediction_loss(*holdout)
    if not np.isclose(after_restart, with_replay, rtol=1e-9, atol=1e-12):
        raise ValueError("T8 replay checkpoint did not reproduce retention")
    return {
        "schema": "v13.t8_world_jepa_replay_cycle.v1",
        "status": "SHADOW_T8_DIGITAL_LEARNING",
        "source_sha256": source,
        "source_verified": True,
        "train_rows": len(train_rows),
        "old_train_rows": len(old),
        "new_train_rows": len(recent),
        "replayed_rows": len(replay_rows),
        "holdout_rows": len(split["holdout_action_ids"]),
        "id_content_disjoint": True,
        "holdout_loss_before": float(before),
        "holdout_loss_without_replay": float(without),
        "holdout_loss_with_replay": float(with_replay),
        "forgetting_without_replay": float(without - before),
        "forgetting_with_replay": float(with_replay - before),
        "replay_better_on_this_cohort": bool(with_replay < without),
        "encoder_weights_changed": True,
        "checkpoint_sha256": saved["sha256"],
        "holdout_loss_after_restart": float(after_restart),
        "optimizer_resume_verified": False,
        "active_model_promoted": False,
        "body_weights_modified": False,
        "android_device_verified": False,
        "native_android_executed": False,
        "voice_adapter_weights_modified": False,
    }
