from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest
from v13.online_world import OnlineWorld


def transition(i):
    return {'action_id':f'action-{i}','s':[.1+i*.01,0.,0.,1.],
            'a':'simple' if i%2==0 else 'detail','y':[.2+i*.005,1.,.3]}


def test_real_committed_feed_is_incrementally_learned_and_deduplicated(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(i) for i in range(12)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        w=OnlineWorld(runtime)
        assert w.update()['learned']==12
        assert w.model.seen==12
        assert w.update()['learned']==0
        before=w.predict(rows[0]['s'],'simple')
        w2=OnlineWorld(runtime)
        assert w2.update()['learned']==0
        np.testing.assert_allclose(w2.predict(rows[0]['s'],'simple'),before)
    with patch('v13.online_world.world_model.transitions',return_value=rows+[transition(12)]):
        assert w2.update()['learned']==1
        assert w2.model.seen==13


def test_invalid_or_speculative_input_never_becomes_online_learning(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    bad=transition(0);bad['y']=[float('nan'),0.,1.]
    with patch('v13.online_world.world_model.transitions',return_value=[bad]):
        w=OnlineWorld(runtime)
        with pytest.raises(ValueError):w.update()
        assert w.model.seen==0
    with patch('v13.online_world.world_model.transitions',return_value=[]):
        assert w.update()['learned']==0


def test_real_action_identifiers_are_strings_not_ordered_integers(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(2),transition(1)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        assert OnlineWorld(runtime).update()['learned']==2
