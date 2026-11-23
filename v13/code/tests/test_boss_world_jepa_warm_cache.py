from types import SimpleNamespace

import pytest

from v13 import bodyview, world_jepa_consumer, world_jepa_receiver_matrix, world_model
from v13.common import dumps


def test_model_cache_is_exact_and_foreground_warm_only(monkeypatch, tmp_path):
    store = SimpleNamespace(home=tmp_path)
    consumer = world_jepa_consumer.WorldJEPAStoreConsumer(
        store, tmp_path / "world_jepa", learning_enabled=False, recover_pending=False
    )
    checkpoint = tmp_path / "checkpoint.npz"
    checkpoint.write_bytes(b"fixture")
    monkeypatch.setattr(consumer, "_checkpoint_path", lambda record: checkpoint)

    loaded = []

    def load(path, source_sha256, checkpoint_sha256):
        model = object()
        loaded.append((source_sha256, checkpoint_sha256, model))
        return model

    monkeypatch.setattr(world_jepa_consumer.world_jepa_shadow_checkpoint, "load", load)
    record = {"source_sha256": "b" * 64, "checkpoint_sha256": "a" * 64}

    with pytest.raises(world_jepa_consumer.ModelNotWarmError):
        consumer._load_model(record, allow_cold=False, cache=True)
    assert loaded == []

    cached = consumer._load_model(record, cache=True)
    assert consumer._load_model(record, allow_cold=False, cache=True) is cached
    assert len(loaded) == 1

    # A training-style load is private and cannot mutate or replace the read cache.
    private = consumer._load_model(record, cache=False)
    assert private is not cached
    assert len(loaded) == 2
    assert consumer._load_model(record, allow_cold=False, cache=True) is cached

    changed = record | {"checkpoint_sha256": "c" * 64}
    refreshed = consumer._load_model(changed, cache=True)
    assert refreshed is not cached
    assert len(loaded) == 3
    consumer._clear_model_cache()
    with pytest.raises(world_jepa_consumer.ModelNotWarmError):
        consumer._load_model(changed, allow_cold=False, cache=True)


def test_receiver_matrix_reuses_store_consumer_and_never_cold_loads_when_warm_only(
    monkeypatch, tmp_path
):
    store = SimpleNamespace(home=tmp_path)
    active = {"source_sha256": "b" * 64, "checkpoint_sha256": "a" * 64}
    monkeypatch.setattr(
        world_jepa_consumer.WorldJEPAStoreConsumer,
        "_read_state",
        lambda self: ({"active": active}, None),
    )
    loads = []

    def cold_only(self, record, *, allow_cold=True, cache=False):
        loads.append((allow_cold, cache))
        raise world_jepa_consumer.ModelNotWarmError()

    monkeypatch.setattr(
        world_jepa_consumer.WorldJEPAStoreConsumer, "_load_model", cold_only
    )
    actions = list(world_model.ACTIONS)
    for _ in range(2):
        matrix = world_jepa_receiver_matrix.receiver_matrix(
            store, [0.1, 0.2, 0.3, 0.4], actions,
            home=tmp_path, nonblocking=True, warm_only=True,
        )
        assert all(
            matrix[action][role]["status"] == "MODEL_NOT_WARM"
            and matrix[action][role]["native_body_consumed"] is False
            and matrix[action][role]["native_body_weights_changed"] is False
            for action in actions
            for role in world_jepa_receiver_matrix.RECEIVER_ROLES
        )
    assert len(loads) == 2 and all(args == (False, True) for args in loads)
    assert isinstance(store._v14_world_jepa_consumer,
                      world_jepa_consumer.WorldJEPAStoreConsumer)


def _valid_matrix(actions):
    matrix = {}
    for action in actions:
        matrix[action] = {}
        for role in world_jepa_receiver_matrix.RECEIVER_ROLES:
            prediction = (
                {"predicted_action_duration_s": 2.0, "predicted_output_characters": 96}
                if role == "B1_DETAIL"
                else {"predicted_success_probability": 0.75}
            )
            matrix[action][role] = {
                "role": role,
                "status": "SHADOW_READOUT_ONLY",
                "prediction": prediction,
                "uncertainty": 0.1,
                "checkpoint_sha256": "a" * 64,
                "source_sha256": "b" * 64,
                "receiver_utility": {"accepted": True},
                "support_samples": 8,
                "support_min_samples": 8,
                "support_scope": "TRAIN_SPLIT_ONLY",
                "decision_authority": "NONE",
                "native_body_consumed": False,
                "native_body_weights_changed": False,
            }
    return matrix


@pytest.mark.parametrize("role", ["B1_DETAIL", "B2_GIST"])
def test_body_prompt_has_explicit_no_weight_change_and_rejects_tampered_rows(
    monkeypatch, tmp_path, role
):
    actions = tuple(world_model.ACTIONS)
    matrix = _valid_matrix(actions)
    pressure = next(iter(world_model.PRESSURE))
    monkeypatch.setattr(world_model, "state_vec", lambda *args: [0.1, 0.2, 0.3, 0.4])
    monkeypatch.setattr(
        world_jepa_receiver_matrix, "receiver_matrix",
        lambda store, state, requested, home=None, *, nonblocking=False, warm_only=False:
            matrix if nonblocking and warm_only and tuple(requested) == actions else None,
    )
    runtime = SimpleNamespace(
        guard=SimpleNamespace(state=pressure),
        store=object(),
        home=tmp_path,
    )
    event = {"event_id": "evt_test", "brain_generation_id": "gen_test"}

    context, audit = bodyview._world_jepa_body_readout(
        runtime, event, "bounded source query", role
    )
    assert context is not None and audit is not None
    assert context["native_body_consumed"] is False
    assert context["native_body_weights_changed"] is False
    assert context["decision_authority"] == "NONE"
    assert audit["native_body_weights_changed"] is False
    assert len(dumps(context)) <= bodyview.STATE_CHARS

    tampered = _valid_matrix(actions)
    tampered[actions[0]][role]["native_body_weights_changed"] = True
    monkeypatch.setattr(
        world_jepa_receiver_matrix, "receiver_matrix",
        lambda *args, **kwargs: tampered,
    )
    assert bodyview._world_jepa_body_readout(
        runtime, event, "bounded source query", role
    ) == (None, None)

def test_idle_warm_primes_exact_store_checkpoint_without_training_or_authority(
    monkeypatch, tmp_path
):
    store = SimpleNamespace(home=tmp_path)
    checkpoint = tmp_path / "checkpoint.npz"
    checkpoint.write_bytes(b"verified-fixture")
    active = {"source_sha256": "b" * 64, "checkpoint_sha256": "a" * 64}
    monkeypatch.setattr(
        world_jepa_consumer.WorldJEPAStoreConsumer,
        "_read_state",
        lambda self: ({"active": active}, 1),
    )
    monkeypatch.setattr(
        world_jepa_consumer.WorldJEPAStoreConsumer,
        "_checkpoint_path",
        lambda self, record: checkpoint,
    )
    loads = []

    def load(path, source_sha256, checkpoint_sha256):
        model = object()
        loads.append((source_sha256, checkpoint_sha256, model))
        return model

    monkeypatch.setattr(
        world_jepa_consumer.world_jepa_shadow_checkpoint, "load", load
    )
    warmed = world_jepa_receiver_matrix.warm_receiver_cache(
        store, tmp_path, nonblocking=True
    )
    assert warmed["status"] == "WARMED"
    assert warmed["decision_authority"] == "NONE"
    assert warmed["native_body_consumed"] is False
    assert warmed["native_body_weights_changed"] is False
    consumer = store._v14_world_jepa_consumer
    assert consumer._load_model(
        active, allow_cold=False, cache=True
    ) is loads[0][2]
    assert len(loads) == 1

    # A changed source/checkpoint identity must replace, never reuse, the cache.
    changed = active | {"checkpoint_sha256": "c" * 64}
    monkeypatch.setattr(
        world_jepa_consumer.WorldJEPAStoreConsumer,
        "_read_state",
        lambda self: ({"active": changed}, 2),
    )
    warmed_again = world_jepa_receiver_matrix.warm_receiver_cache(
        store, tmp_path, nonblocking=True
    )
    assert warmed_again["status"] == "WARMED"
    assert consumer._load_model(
        changed, allow_cold=False, cache=True
    ) is loads[1][2]
    assert len(loads) == 2


def test_sleep_scheduler_retries_idle_receiver_warm_after_planner_completion(tmp_path):
    from v13.sleep import SleepRuntime

    class _Store:
        def __init__(self):
            self.cursor = {
                "last_learning_event_id": "evt-1",
                "last_planner_event_id": "evt-1",
            }

        def one(self, *_args, **_kwargs):
            return {"event_id": "evt-1", "status": "FINAL"}

        def state(self, key, default=None):
            if key == "v14.world_jepa.sleep_cursor":
                return self.cursor, 1
            if key == "v14.world_jepa.store_consumer":
                return {"active": {"checkpoint_sha256": "a" * 64}}, 1
            return default, 0

    class _Scheduler:
        def __init__(self):
            self.calls = []

        def post(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return "queued"

    store = _Store()
    scheduler = _Scheduler()
    worker = SimpleNamespace(
        r=SimpleNamespace(store=store, home=tmp_path),
        scheduler=scheduler,
    )
    assert SleepRuntime.schedule_world_jepa(worker) == "queued"
    assert len(scheduler.calls) == 1

    store.cursor["last_receiver_warm_event_id"] = "evt-1"
    assert SleepRuntime.schedule_world_jepa(worker) is None
    assert len(scheduler.calls) == 1
