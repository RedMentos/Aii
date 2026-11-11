"""Integration: committed SQLite T8 -> numeric WorldJEPA -> full optimizer restart -> replay.

Runs on the integrated WorldJEPA training-state candidate. No phone or active-model claim.
"""
import hashlib
import json

import numpy as np

from tests.test_world_jepa_readonly_store import fixture, sha
from scripts.world_jepa_readonly_store import ReadOnlyStore
from v13 import world_model
from v13.world_jepa import WorldJEPA
from v13.world_jepa_action_outcome_adapter import build
from v13.world_jepa_shadow_checkpoint import save, load


def arrays(rows):
    return (np.asarray([r["s"] + [0., 0., 0.] for r in rows], dtype=np.float64),
            np.asarray([world_model.onehot(r["a"]) for r in rows], dtype=np.float64),
            np.asarray([r["s"] + r["y"] for r in rows], dtype=np.float64))


def equal_numeric(a, b):
    assert a.keys() == b.keys()
    for key in a:
        if isinstance(a[key], dict):
            equal_numeric(a[key], b[key])
        elif isinstance(a[key], list):
            assert len(a[key]) == len(b[key])
            for x, y in zip(a[key], b[key]):
                if isinstance(x, dict):
                    equal_numeric(x, y)
                else:
                    assert x == y
        elif isinstance(a[key], np.ndarray):
            assert np.array_equal(a[key], b[key]), key
        else:
            assert a[key] == b[key], key


def test_committed_t8_replay_optimizer_resume_exact(tmp_path):
    db = tmp_path / "committed.sqlite"
    fixture(db, n=96)
    db_before = sha(db)
    store = ReadOnlyStore(db)
    try:
        rows = world_model.transitions(store, limit=2048)
    finally:
        store.close()
    split = build(rows)
    holdout_ids = set(split["holdout_action_ids"])
    train = [r for r in rows if r["action_id"] not in holdout_ids]
    cut = 2 * len(train) // 3
    old, recent = train[:cut], train[cut:]
    assert len(old) >= 8 and len(recent) >= 8
    assert not holdout_ids.intersection(r["action_id"] for r in old + recent)
    first = arrays(old)
    second = arrays(recent + old[::2])
    holdout = split["holdout"]
    source = split["manifest"]["all_rows_sha256"]

    original = WorldJEPA(seed=7, ensemble=2).fit(*first, steps=4, log_every=1)
    assert original._training_state["main"]["t"] == 4
    checkpoint = tmp_path / "full-training.npz"
    receipt = save(original, checkpoint, source)
    assert receipt["optimizer_state_persisted"] is True
    restored = load(checkpoint, source, receipt["sha256"])
    assert restored._training_state["main"]["t"] == 4
    equal_numeric(original._training_state, restored._training_state)
    assert original.prediction_loss(*holdout) == restored.prediction_loss(*holdout)

    before = original.enc["W1"].copy()
    original.partial_fit(*second, steps=3, log_every=1)
    restored.partial_fit(*second, steps=3, log_every=1)
    assert not np.array_equal(before, original.enc["W1"])
    assert original._training_state["main"]["t"] == restored._training_state["main"]["t"] == 7
    equal_numeric(original._training_state, restored._training_state)
    assert np.array_equal(original.enc["W1"], restored.enc["W1"])
    assert np.array_equal(original.tgt["W1"], restored.tgt["W1"])
    for p, q in zip(original.preds, restored.preds):
        equal_numeric(p, q)
    assert original.prediction_loss(*holdout) == restored.prediction_loss(*holdout)
    assert sha(db) == db_before
    print("T8_OPTIMIZER_REPLAY_RESUME", json.dumps({
        "source_sha256": source, "old_rows": len(old), "recent_rows": len(recent),
        "replay_rows": len(old[::2]), "steps_after_restart": 7,
        "optimizer_ema_rng_and_weights_exact": True,
        "android_device_verified": False, "body_weights_modified": False}))
