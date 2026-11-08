import numpy as np
from v13.world_jepa import WorldJEPA
from v13.world_jepa_online_experiment import update


def records():
    return [{'action_id':f'transition-{i:03d}',
             's':[i/90.,(i%7)/7.,np.sin(i/11.),np.cos(i/11.)],
             'a':('simple','detail','gist','both')[i%4],
             'y':[i/180.,float(i%3==0),i/200.]}
            for i in range(96)]


def test_committed_disjoint_transition_adapter_updates_same_jepa_weights():
    model=WorldJEPA(seed=7,ensemble=2)
    first=update(model,records(),steps=2)
    assert first['mode']=='INITIAL_WEIGHTS'
    assert first['holdout_loss_before'] is None
    old=model.enc['W1'].copy()
    second=update(model,records(),steps=3)
    assert second['mode']=='CONTINUED_WEIGHTS'
    assert second['holdout_loss_before']>=0
    assert second['holdout_loss_after']>=0
    assert np.isfinite(second['holdout_delta'])
    assert not np.array_equal(old,model.enc['W1'])
    assert model._fit_steps==5
    assert second['source_verified'] is False
