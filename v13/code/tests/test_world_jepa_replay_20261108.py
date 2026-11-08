import pytest
from v13.world_jepa_replay import ReplaySession
from v13.world_jepa_action_outcome_adapter import build
from v13 import world_model


def rows(n=96):
    routes = tuple(world_model.ACTIONS)
    return [{"action_id": f"action-{i:04d}",
             "s": [float(i), float(i % 7), float(i % 11), float(i % 13)],
             "a": routes[i % len(routes)],
             "y": [float(i % 3), float(i % 5), float(i % 17)]}
            for i in range(n)]


class FakeJEPA:
    def __init__(self):
        self.calls = []

    def fit(self, x, a, y, **kw):
        self.calls.append(("fit", len(x)))
        self.enc = {}

    def partial_fit(self, x, a, y, **kw):
        self.calls.append(("partial", len(x)))

    def prediction_loss(self, x, a, y):
        return 0.5


def test_real_adapter_partition_dedup_and_restore():
    records = rows()
    split = build(records)
    session = ReplaySession("a" * 64)
    model = FakeJEPA()
    result = session.update(model, records, steps=2)
    assert result["updated"] is True
    assert result["new_rows"] == len(split["train_action_ids"])
    assert result["active_model_promoted"] is False
    assert model.calls == [("fit", result["new_rows"])]
    assert not session.update(model, records)["updated"]
    restored = ReplaySession.restore(session.snapshot(), "a" * 64)
    assert not restored.update(model, records)["updated"]
    assert len(model.calls) == 1


def test_modified_action_identity_rejected_before_gradient():
    records = rows()
    session = ReplaySession("a" * 64)
    model = FakeJEPA()
    session.update(model, records)
    train_id = build(records)["train_action_ids"][0]
    for row in records:
        if row["action_id"] == train_id:
            row["y"][0] += 1
            break
    with pytest.raises(ValueError, match="changed content"):
        session.update(model, records)
    assert len(model.calls) == 1


def test_mismatched_source_and_malformed_journal_rejected():
    session = ReplaySession("a" * 64)
    with pytest.raises(ValueError):
        ReplaySession.restore(session.snapshot(), "b" * 64)
    bad = session.snapshot()
    bad["seen"] = {"x": "not-a-digest"}
    with pytest.raises(ValueError):
        ReplaySession.restore(bad, "a" * 64)


def test_second_batch_updates_only_fresh_train_ids():
    initial = rows(96)
    extended = rows(120)
    model = FakeJEPA()
    session = ReplaySession("a" * 64)
    first = session.update(model, initial)
    second = session.update(model, extended)
    assert second["updated"] is True
    assert second["new_rows"] == len(build(extended)["train_action_ids"]) - first["new_rows"]
    assert model.calls == [("fit", first["new_rows"]),
                           ("partial", second["new_rows"])]
    assert not session.update(model, extended)["updated"]


def test_capacity_fails_before_mutating_model_or_journal():
    model = FakeJEPA()
    session = ReplaySession("a" * 64, max_seen=32)
    with pytest.raises(ValueError, match="journal full"):
        session.update(model, rows(96))
    assert model.calls == []
    assert session.snapshot()["seen"] == {}
