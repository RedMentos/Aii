import numpy as np
import pytest
from v13.continuous_predictor import OnlinePredictor


def samples(n=32):
    for i in range(n):
        x=np.array([i%7/7.,(i%5)/5.])
        a=i%2
        yield x,a,x+np.array([0.25 if a==0 else -0.25,0.1])


def test_online_updates_real_parameters_and_reduces_holdout_error(tmp_path):
    m=OnlinePredictor(2,2,tmp_path,lr=0.04,seed=3)
    test=list(samples(32));before=m.error(test);old=m.U.copy()
    for _ in range(25):
        for x,a,y in samples(32):m.observe(x,a,y)
    assert not np.array_equal(old,m.U)
    assert m.error(test)<before*0.2
    assert m.updates==25*32*3


def test_restart_restores_weights_and_replay(tmp_path):
    m=OnlinePredictor(2,2,tmp_path,replay=8,seed=4)
    for x,a,y in samples(40):m.observe(x,a,y)
    prediction=m.predict([.2,.4],1)
    m.checkpoint()
    n=OnlinePredictor(2,2,tmp_path,replay=8,seed=4)
    np.testing.assert_allclose(n.predict([.2,.4],1),prediction)
    assert n.seen==40 and len(n.x)==8 and n.updates==120
    n.observe([.2,.4],1,[.1,.5]);assert n.seen==41


def test_bad_data_never_changes_weights(tmp_path):
    m=OnlinePredictor(2,2,tmp_path)
    w=m.W.copy()
    for x,a,y in [([float('nan'),0],0,[1,0]),([0,0],4,[1,0]),([0,0],0,[float('inf'),0])]:
        with pytest.raises(ValueError):m.observe(x,a,y)
    np.testing.assert_array_equal(m.W,w)
    assert m.seen==0


def test_checkpoint_is_dimension_checked(tmp_path):
    m=OnlinePredictor(2,2,tmp_path);m.checkpoint()
    with pytest.raises(ValueError):OnlinePredictor(3,2,tmp_path)


def test_restarted_learning_matches_uninterrupted_replay(tmp_path):
    a=OnlinePredictor(2,2,tmp_path/'a',replay=8,seed=9)
    b=OnlinePredictor(2,2,tmp_path/'b',replay=8,seed=9)
    stream=list(samples(64))
    for x,act,y in stream[:32]:a.observe(x,act,y);b.observe(x,act,y)
    b.checkpoint();b=OnlinePredictor(2,2,tmp_path/'b',replay=8,seed=9)
    for x,act,y in stream[32:]:a.observe(x,act,y);b.observe(x,act,y)
    np.testing.assert_array_equal(a.W,b.W)
    np.testing.assert_array_equal(a.U,b.U)
    np.testing.assert_array_equal(a.x,b.x)
    assert a.seen==b.seen and a.updates==b.updates


def test_checkpoint_rollback_restores_previous_learned_weights(tmp_path):
    m=OnlinePredictor(2,2,tmp_path)
    for x,a,y in samples(16):m.observe(x,a,y)
    old=m.W.copy();m.checkpoint()
    for x,a,y in samples(16):m.observe(x,a,y)
    m.checkpoint()
    assert not np.array_equal(m.W,old)
    assert m.rollback()['status']=='ROLLED_BACK_IN_MEMORY'
    np.testing.assert_array_equal(m.W,old)


def test_rollback_without_prior_snapshot_is_rejected(tmp_path):
    m=OnlinePredictor(2,2,tmp_path)
    with pytest.raises(FileNotFoundError):m.rollback()
