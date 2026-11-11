"""Actual SQLite T8 reader -> numeric WorldJEPA replay -> persisted readback."""
import json
import math

import pytest

from tests.test_world_jepa_readonly_store import fixture, sha
from scripts.world_jepa_readonly_store import ReadOnlyStore
from v13.t8_world_jepa_replay_cycle import run
from v13.world_jepa_shadow_checkpoint import load


def test_real_sqlite_t8_replay_and_restart(tmp_path):
    db = tmp_path / "closed.sqlite"
    fixture(db, n=96)
    before_db = sha(db)
    store = ReadOnlyStore(db)
    try:
        report = run(store, tmp_path / "t8-replay.npz", seed=7, steps=3)
    finally:
        store.close()
    assert sha(db) == before_db
    assert report["status"] == "SHADOW_T8_DIGITAL_LEARNING"
    assert report["source_verified"] is True
    assert report["holdout_rows"] >= 8
    assert report["id_content_disjoint"] is True
    # Replay phases must follow the T8 reader's committed chronological order,
    # never the opaque action ID's lexical order.
    from v13 import world_model
    from v13.world_jepa_action_outcome_adapter import build
    verify = ReadOnlyStore(db)
    try:
        chronological = world_model.transitions(verify, limit=2048)
    finally:
        verify.close()
    split = build(chronological)
    allowed = set(split["train_action_ids"])
    train = [r["action_id"] for r in chronological if r["action_id"] in allowed]
    cut = 2 * len(train) // 3
    import hashlib
    expected_old = hashlib.sha256(json.dumps(train[:cut], separators=(",", ":")).encode()).hexdigest()
    expected_new = hashlib.sha256(json.dumps(train[cut:], separators=(",", ":")).encode()).hexdigest()
    assert report["phase_order"] == "T8_COMMITTED_CHRONOLOGICAL_OLDEST_TO_NEWEST"
    assert report["old_train_ids_sha256"] == expected_old
    assert report["recent_train_ids_sha256"] == expected_new
    assert report["encoder_weights_changed"] is True
    assert report["holdout_loss_after_restart"] == pytest.approx(
        report["holdout_loss_with_replay"], abs=1e-12, rel=1e-9)
    assert report["active_model_promoted"] is False
    assert report["optimizer_resume_verified"] is False
    assert report["android_device_verified"] is False
    assert all(math.isfinite(report[k]) for k in (
        "holdout_loss_before", "holdout_loss_without_replay",
        "holdout_loss_with_replay", "forgetting_without_replay", "forgetting_with_replay"))
    assert "synthetic-action-" not in json.dumps(report)
    assert "synthetic-event-" not in json.dumps(report)
    with pytest.raises(ValueError):
        load(tmp_path / "t8-replay.npz", "0" * 64, report["checkpoint_sha256"])


def test_refuse_checkpoint_overwrite_and_invalid_budgets(tmp_path):
    db = tmp_path / "closed.sqlite"
    fixture(db, n=96)
    store = ReadOnlyStore(db)
    try:
        target = tmp_path / "already.npz"
        target.write_bytes(b"do-not-overwrite")
        with pytest.raises(ValueError):
            run(store, target, seed=3, steps=2)
        assert target.read_bytes() == b"do-not-overwrite"
        for steps in (0, 101, True):
            with pytest.raises(ValueError):
                run(store, tmp_path / "not-created.npz", steps=steps)
        assert not (tmp_path / "not-created.npz").exists()
    finally:
        store.close()
