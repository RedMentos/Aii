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
