"""Exercise source-bound and standalone streams in the composed Runtime copy."""
import numpy as np
import pytest

from integrated_online_world_disposable_cases import synthetic_c3, turn
from v13 import online_world_policy, world_model
from v13.online_world import OnlineWorld
from v13.operator import Operator
from v13.runtime import Runtime


def test_source_bound_stream_never_consumes_or_mutates_before_or_after_first_commit(tmp_path):
    r = Runtime(tmp_path)
    try:
        synthetic_c3(r)
        turn(r)
        op = Operator(r)
        op.run(':learning shadow')
        online_world_policy.set_enabled(r.store, True, online_world_policy.HUMAN)
        world = OnlineWorld(r)
        r._online_world = world
        x, action, target = OnlineWorld.encode(world_model.transitions(r.store)[0])
        consumed = []
        def stream():
            consumed.append(True)
            yield x, action, target
        model = world.model
        before = model._snapshot()
        with pytest.raises(ValueError, match='Source-bound predictor'):
            model.learn_stream(stream(), checkpoint_every=1)
        assert not consumed and model.seen == before['seen'] == 0
        np.testing.assert_array_equal(model.U, before['arrays']['U'])
        assert not model.path.exists()
        assert r.online_world_update(limit=64, authority=online_world_policy.HUMAN)['learned'] == 1
        checkpoint = model.path.read_bytes()
        snapshot = model._snapshot()
        with pytest.raises(ValueError, match='Source-bound predictor'):
            model.learn_stream(stream(), checkpoint_every=1)
        assert not consumed and model.path.read_bytes() == checkpoint
        for key in ('W', 'U', 'bias', 'x', 'act', 'y'):
            np.testing.assert_array_equal(getattr(model, key), snapshot['arrays'][key])
        assert model.seen == snapshot['seen'] and model.updates == snapshot['updates']
        assert model.rng.bit_generator.state == snapshot['rng']
        assert model.metadata == snapshot['metadata']
        r.close()
        r = Runtime(tmp_path)
        op = Operator(r)
        op.run(':learning shadow')
        assert r.online_world_update(limit=64, authority=online_world_policy.HUMAN)['learned'] == 0
        assert r._online_world.model.path.read_bytes() == checkpoint
        with pytest.raises(ValueError, match='Source-bound predictor'):
            r._online_world.model.learn_stream(stream(), checkpoint_every=1)
        assert not consumed
    finally:
        r.close()


def test_bound_checkpoint_outside_world_is_also_rejected_without_mutation(tmp_path):
    from v13.continuous_predictor import OnlinePredictor
    model = OnlinePredictor(2, 2, tmp_path)
    model.observe([.1, .2], 0, [.3, .4])
    model.checkpoint(metadata={'test': 'bound'})
    snapshot = model._snapshot()
    checkpoint = model.path.read_bytes()
    with pytest.raises(ValueError, match='Source-bound predictor'):
        model.learn_stream([([.2, .1], 1, [.4, .2])], checkpoint_every=1)
    np.testing.assert_array_equal(model.U, snapshot['arrays']['U'])
    assert model.seen == snapshot['seen'] and model.metadata == snapshot['metadata']
    assert model.path.read_bytes() == checkpoint


def test_large_finite_weight_fails_gradient_check_without_partial_state(tmp_path):
    # The #1717 CI fixture overflows the gradient norm before it can reach
    # its intended post-update loss check; preserve that distinction here.
    from v13.continuous_predictor import OnlinePredictor
    model = OnlinePredictor(1, 2, tmp_path, replay=8, seed=17)
    model.W[0, 0] = 1e155
    before = model._snapshot()
    with np.errstate(over='ignore', invalid='ignore'):
        with pytest.raises(ValueError, match='Nonfinite online gradient'):
            model.observe([1.], 0, [0.], rehearsals=1)
    for key in ('W', 'U', 'bias', 'x', 'act', 'y'):
        np.testing.assert_array_equal(getattr(model, key), before['arrays'][key])
    assert model.seen == before['seen'] and model.updates == before['updates']
    assert model.rng.bit_generator.state == before['rng']
