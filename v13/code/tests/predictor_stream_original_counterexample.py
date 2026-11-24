"""Confirm the known bug only against the unmodified #1716 test-copy builder."""
import numpy as np
import pytest

from integrated_online_world_disposable_cases import synthetic_c3, turn
from v13 import online_world_policy, world_model
from v13.online_world import OnlineWorld
from v13.operator import Operator
from v13.runtime import Runtime


def test_bound_stream_mutates_before_rejected_checkpoint(tmp_path):
    r = Runtime(tmp_path)
    try:
        synthetic_c3(r)
        turn(r)
        Operator(r).run(':learning shadow')
        online_world_policy.set_enabled(r.store, True, online_world_policy.HUMAN)
        assert r.online_world_update(limit=64, authority=online_world_policy.HUMAN)['learned'] == 1
        model = r._online_world.model
        checkpoint = model.path.read_bytes()
        before, seen = model.U.copy(), model.seen
        x, action, target = OnlineWorld.encode(world_model.transitions(r.store)[0])
        with pytest.raises(ValueError, match='Bound checkpoint metadata'):
            model.learn_stream([(x, action, target)], checkpoint_every=1)
        assert model.seen == seen + 1
        assert not np.array_equal(before, model.U)
        assert model.path.read_bytes() == checkpoint
    finally:
        r.close()
