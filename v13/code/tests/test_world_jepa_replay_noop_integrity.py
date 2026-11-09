"""Zero-gradient replay batches must still bind held-out observations."""
import pytest
from v13 import world_jepa_replay as replay_mod
from v13.world_jepa_replay import ReplaySession


def _rows(value=1):
    return [
        {"action_id": "train-1", "payload": 0},
        {"action_id": "held-1", "payload": value},
    ]


def _split(records):
    return {
        "train_action_ids": ["train-1"],
        "holdout_action_ids": ["held-1"],
        "train": ([], [], []),
        "holdout": ([], [], []),
    }


def test_no_gradient_batch_journals_new_holdout_and_rejects_mutation(monkeypatch):
    monkeypatch.setattr(replay_mod, "build", _split)
    session = ReplaySession("a" * 64)
    session.seen["train-1"] = session._digest(_rows()[0])
    result = session.update(object(), _rows())
    assert not result["updated"]
    assert session.holdout_seen["held-1"] == session._digest(_rows()[1])
    restored = ReplaySession.restore(result["journal"], "a" * 64)
    with pytest.raises(ValueError, match="holdout action ID changed"):
        restored.update(object(), _rows(2))
    assert restored.holdout_seen == session.holdout_seen


def test_no_gradient_batch_enforces_capacity_without_mutation(monkeypatch):
    monkeypatch.setattr(replay_mod, "build", _split)
    session = ReplaySession("a" * 64, max_seen=32)
    session.seen["train-1"] = session._digest(_rows()[0])
    for i in range(30):
        session.seen[f"old-{i}"] = "b" * 64
    before = session.snapshot()
    with pytest.raises(ValueError, match="journal full"):
        session.update(object(), _rows())
    assert session.snapshot() == before
