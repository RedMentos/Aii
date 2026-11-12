"""Chronological retention and optimizer restart on committed T8 SQLite transitions.

Run only against the pinned integrated WorldJEPA stage. This is an empirical
synthetic T8 regression, not a production sleep scheduler or Android proof.
"""
import json
import resource
import time

import numpy as np

from tests.test_world_jepa_readonly_store import fixture, sha
from tests.test_t8_world_jepa_optimizer_resume_integration_20261111 import arrays, equal_numeric
from scripts.world_jepa_readonly_store import ReadOnlyStore
from v13 import world_model
from v13.world_jepa import WorldJEPA
from v13.world_jepa_action_outcome_adapter import build
from v13.world_jepa_shadow_checkpoint import save, load


def test_chronological_t8_retention_replay_and_restart(tmp_path):
    db = tmp_path / "trusted-t8.sqlite"
    fixture(db, n=144)
    original_db_sha = sha(db)
    store = ReadOnlyStore(db)
    try:
        rows = world_model.transitions(store, limit=2048)
    finally:
        store.close()
    split = build(rows)
    held = set(split["holdout_action_ids"])
    training = [r for r in rows if r["action_id"] not in held]
    # Chronology comes from the trusted T8 reader's ordering. Preserve its
    # order; do not sort by content or randomize old/recent assignments.
    assert len(training) >= 40
    assert len(held) >= 8
    assert not held.intersection(r["action_id"] for r in training)
    old, recent = training[:len(training)//2], training[len(training)//2:]
    old_holdout = [r for r in rows[:len(rows)//2] if r["action_id"] in held]
    recent_holdout = [r for r in rows[len(rows)//2:] if r["action_id"] in held]
    assert len(old_holdout) >= 4 and len(recent_holdout) >= 4
    old_train, recent_train = arrays(old), arrays(recent)
    old_eval, recent_eval = arrays(old_holdout), arrays(recent_holdout)
    source = split["manifest"]["all_rows_sha256"]
    start = time.perf_counter()

    base = WorldJEPA(seed=19, ensemble=2).fit(*old_train, steps=6, log_every=1)
    pre = {
        "old": float(base.prediction_loss(*old_eval)),
        "recent": float(base.prediction_loss(*recent_eval)),
    }
    checkpoint = tmp_path / "training-state.npz"
    receipt = save(base, checkpoint, source)
    assert receipt["optimizer_state_persisted"] is True
    replay = load(checkpoint, source, receipt["sha256"])
    no_replay = load(checkpoint, source, receipt["sha256"])
    equal_numeric(base._training_state, replay._training_state)
    equal_numeric(base._training_state, no_replay._training_state)

    # Same number of updates, different retention intervention.
    # Old replay is drawn only from training rows; no holdout leaks.
    replay_batch = arrays(recent + old[::2])
    recent_only_batch = recent_train
    replay.partial_fit(*replay_batch, steps=6, log_every=1)
    no_replay.partial_fit(*recent_only_batch, steps=6, log_every=1)
    assert replay._training_state["main"]["t"] == 12
    assert no_replay._training_state["main"]["t"] == 12
    after_replay = {
        "old": float(replay.prediction_loss(*old_eval)),
        "recent": float(replay.prediction_loss(*recent_eval)),
    }
    after_no_replay = {
        "old": float(no_replay.prediction_loss(*old_eval)),
        "recent": float(no_replay.prediction_loss(*recent_eval)),
    }
    for result in (pre, after_replay, after_no_replay):
        assert all(np.isfinite(v) for v in result.values())

    final = tmp_path / "after-replay.npz"
    final_receipt = save(replay, final, source)
    resumed = load(final, source, final_receipt["sha256"])
    equal_numeric(replay._training_state, resumed._training_state)
    assert resumed.prediction_loss(*old_eval) == replay.prediction_loss(*old_eval)
    assert resumed.prediction_loss(*recent_eval) == replay.prediction_loss(*recent_eval)
    assert sha(db) == original_db_sha
    print("T8_CHRONOLOGICAL_RETENTION_OPTIMIZER", json.dumps({
        "source_sha256": source,
        "train_old": len(old), "train_recent": len(recent),
        "holdout_old": len(old_holdout), "holdout_recent": len(recent_holdout),
        "old_loss_before": pre["old"],
        "old_loss_after_replay": after_replay["old"],
        "old_loss_after_no_replay": after_no_replay["old"],
        "recent_loss_before": pre["recent"],
        "recent_loss_after_replay": after_replay["recent"],
        "recent_loss_after_no_replay": after_no_replay["recent"],
        "old_forgetting_replay": after_replay["old"] - pre["old"],
        "old_forgetting_no_replay": after_no_replay["old"] - pre["old"],
        "replay_advantage_old": after_no_replay["old"] - after_replay["old"],
        "elapsed_s": time.perf_counter() - start,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "full_optimizer_restart": True,
        "android_verified": False, "gguf_weights_changed": False,
        "production_sleep_consumer": False,
    }, sort_keys=True))
