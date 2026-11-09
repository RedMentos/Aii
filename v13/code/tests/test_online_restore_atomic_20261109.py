"""Corrupted RNG snapshots must not partially mutate a live predictor."""
import json
import numpy as np
import pytest
from v13.continuous_predictor import OnlinePredictor


def test_invalid_rng_state_rejected_without_partial_restore(tmp_path):
    learner=OnlinePredictor(7,4,tmp_path)
    learner.observe(np.ones(7)*0.1,1,np.ones(7)*0.2)
    learner.checkpoint(processed_ids=['action-1'])
    with np.load(learner.path,allow_pickle=False) as archive:
        payload={k:archive[k].copy() for k in archive.files}
    payload['rng_state']=np.array(json.dumps({'bit_generator':'PCG64','state':'broken'}))
    np.savez_compressed(learner.path,**payload)
    live=OnlinePredictor(7,4,tmp_path/'fresh')
    before=(live.W.copy(),live.U.copy(),live.bias.copy(),live.seen,live.updates,
            json.dumps(live.rng.bit_generator.state,sort_keys=True))
    live.path=learner.path
    with pytest.raises(ValueError,match='RNG checkpoint'):
        live.restore()
    np.testing.assert_array_equal(live.W,before[0])
    np.testing.assert_array_equal(live.U,before[1])
    np.testing.assert_array_equal(live.bias,before[2])
    assert (live.seen,live.updates)==before[3:5]
    assert json.dumps(live.rng.bit_generator.state,sort_keys=True)==before[5]
    assert live.checkpoint_ids is None


def test_valid_rng_resume_remains_deterministic(tmp_path):
    x=np.arange(7,dtype=float)/10
    a=OnlinePredictor(7,4,tmp_path)
    a.observe(x,1,x*0.3)
    a.checkpoint(processed_ids=['action-1'])
    b=OnlinePredictor(7,4,tmp_path)
    for _ in range(5):
        a.observe(x,2,x*0.7)
        b.observe(x,2,x*0.7)
    np.testing.assert_array_equal(a.W,b.W)
    np.testing.assert_array_equal(a.U,b.U)
    np.testing.assert_array_equal(a.x,b.x)
    assert a.seen==b.seen and a.updates==b.updates
