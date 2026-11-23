"""Transactional local-gradient learning regression (software-only)."""
import copy
import numpy as np
import pytest
from v13.continuous_predictor import OnlinePredictor


def snapshot(p):
    return (p.W.copy(), p.U.copy(), p.bias.copy(), p.x.copy(),
            p.act.copy(), p.y.copy(), p.seen, p.updates,
            copy.deepcopy(p.rng.bit_generator.state))


def assert_unchanged(p, before):
    for current, old in zip(snapshot(p)[:6], before[:6]):
        np.testing.assert_array_equal(current, old)
    assert snapshot(p)[6:] == before[6:]


def test_gradient_overflow_does_not_consume_replay_or_rng(tmp_path):
    p=OnlinePredictor(2,2,tmp_path,replay=2)
    p.observe([0.,0.],0,[0.,0.])
    p.observe([0.,0.],1,[0.,0.])
    p.W[0,0]=1e300
    before=snapshot(p)
    with pytest.raises(ValueError,match='Nonfinite online gradient'):
        p.observe([1e6,0.],0,[0.,0.],rehearsals=2)
    assert_unchanged(p,before)


def test_rejected_observation_does_not_change_next_replay(tmp_path):
    first=OnlinePredictor(2,2,tmp_path/'first',replay=2,seed=9)
    second=OnlinePredictor(2,2,tmp_path/'second',replay=2,seed=9)
    for p in (first,second):
        p.observe([0.2,0.3],0,[0.1,0.4])
        p.observe([0.5,0.1],1,[0.2,0.2])
    with pytest.raises(ValueError,match='Invalid observation'):
        first.observe([float('nan'),0.],0,[0.,0.])
    for p in (first,second):
        p.observe([0.4,0.6],1,[0.3,0.2])
    a,b=snapshot(first),snapshot(second)
    for i in range(6):
        np.testing.assert_array_equal(a[i],b[i])
    assert a[6:]==b[6:]


def test_atomic_observe_still_persists_and_resumes(tmp_path):
    p=OnlinePredictor(2,2,tmp_path)
    result=p.observe([0.1,0.2],1,[0.3,0.4])
    assert result['updates']==3
    p.checkpoint()
    q=OnlinePredictor(2,2,tmp_path)
    assert q.seen==1 and q.updates==3
    np.testing.assert_array_equal(q.W,p.W)
    np.testing.assert_array_equal(q.y,p.y)
