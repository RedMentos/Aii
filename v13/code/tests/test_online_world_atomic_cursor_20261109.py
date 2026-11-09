"""Crash-window regression: committed action IDs and weights share one atomic snapshot."""
import json
from types import SimpleNamespace
import pytest
from v13 import world_model
from v13.online_world import OnlineWorld
from v13.continuous_predictor import OnlinePredictor


def row(action_id):
    return {'action_id':action_id,'s':[0.2,0.1,0.0,1.0],
            'a':'simple','y':[0.3,1.0,0.2]}


def test_checkpoint_cursor_wins_over_stale_sidecar_after_restart(tmp_path,monkeypatch):
    rows=[row('action-one')]
    monkeypatch.setattr(world_model,'transitions',lambda store,limit=2048:rows)
    runtime=SimpleNamespace(home=tmp_path,store=object())
    first=OnlineWorld(runtime)
    assert first.update()['learned']==1
    assert first.model.checkpoint_ids==['action-one']
    # Reproduce power loss between the atomic model save and sidecar update.
    (tmp_path/'online_world'/'cursor.json').write_text(json.dumps({
        'revision':'v13-online-world-v1','processed':[]}))
    restored=OnlineWorld(runtime)
    assert restored.processed==['action-one']
    assert restored.model.seen==1
    assert restored.update()['learned']==0
    assert restored.model.seen==1


def test_legacy_predictor_checkpoint_without_cursor_still_loads(tmp_path):
    p=OnlinePredictor(7,4,tmp_path)
    p.checkpoint()
    q=OnlinePredictor(7,4,tmp_path)
    assert q.checkpoint_ids is None


@pytest.mark.parametrize('ids', [['duplicate','duplicate'],[''],[True],['ok',17]])
def test_bad_cursor_rejected_before_checkpoint_write(tmp_path,ids):
    p=OnlinePredictor(7,4,tmp_path)
    with pytest.raises(ValueError,match='cursor'):
        p.checkpoint(processed_ids=ids)
    assert not p.path.exists()


def test_failed_checkpoint_rolls_back_in_memory_and_allows_retry(tmp_path,monkeypatch):
    rows=[row('retry-action')]
    monkeypatch.setattr(world_model,'transitions',lambda store,limit=2048:rows)
    runtime=SimpleNamespace(home=tmp_path,store=object())
    learner=OnlineWorld(runtime)
    def failed_checkpoint(*args,**kwargs):
        raise OSError('simulated disk write failure')
    monkeypatch.setattr(learner.model,'checkpoint',failed_checkpoint)
    with pytest.raises(OSError,match='disk write'):
        learner.update()
    assert learner.model.seen==0
    assert learner.processed==[]
    assert learner.update()['learned']==1
    assert learner.model.seen==1
