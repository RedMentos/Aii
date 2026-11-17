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
        result=w2.update()
        assert result['learned']==1
        assert result['old_replay_loss_before'] is not None
        assert np.isfinite(result['old_replay_loss_delta'])
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


def test_operator_command_uses_runtime_online_learning_without_growth_hub(tmp_path):
    from v13.agi import operator_command
    runtime=SimpleNamespace(home=tmp_path,store=object())
    runtime.online_world_update=lambda limit: {'learned':limit,'status':'LOCAL'}
    import json
    assert json.loads(operator_command(runtime,['onlineworld','3']))['learned']==3
    with pytest.raises(ValueError):operator_command(runtime,['onlineworld','3','extra'])


def test_actual_runtime_method_learns_committed_world_transition(tmp_path):
    from v13.runtime import Runtime
    fake=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(1)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        result=Runtime.online_world_update(fake,limit=16)
    assert result['learned']==1
    assert fake._online_world.model.seen==1


def test_restart_after_checkpoint_before_legacy_cursor_write_is_exactly_once(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(0)]
    # Failure after atomic NPZ replacement must not train the same action again.
    import os
    original_replace=os.replace
    def fail_only_cursor(src,dst):
        if str(dst).endswith('cursor.json'):
            raise OSError('cursor crash')
        return original_replace(src,dst)
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        with patch('v13.online_world.os.replace',side_effect=fail_only_cursor):
            with pytest.raises(OSError,match='cursor crash'):
                OnlineWorld(runtime).update()
        restored=OnlineWorld(runtime)
        assert restored.model.seen==1
        assert restored.processed==['action-0']
        assert restored.update()['learned']==0
        assert restored.model.seen==1


def test_snapshot_ids_override_stale_legacy_cursor(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(0),transition(1)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        w=OnlineWorld(runtime)
        assert w.update()['learned']==2
        w.cursor.write_text('{"revision":"v13-online-world-v1","processed":["action-0"]}')
        restored=OnlineWorld(runtime)
        assert restored.processed==['action-0','action-1']
        assert restored.update()['learned']==0


def test_atomic_snapshot_survives_corrupted_legacy_cursor(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(0)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        first=OnlineWorld(runtime)
        assert first.update()['learned']==1
        first.cursor.write_text('not valid json')
        restored=OnlineWorld(runtime)
        assert restored.processed==['action-0']
        assert restored.update()['learned']==0


def test_legacy_cursor_migrates_into_next_atomic_snapshot(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(0)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        first=OnlineWorld(runtime)
        assert first.update()['learned']==1
        # Simulate a pre-migration predictor snapshot (no action ID metadata).
        first.model.committed_action_ids=None
        first.model.checkpoint()
        legacy=OnlineWorld(runtime)
        assert legacy.processed==['action-0']
        assert legacy.update()['learned']==0
        assert legacy.model.seen==1


def test_checkpoint_failure_restores_live_weights_and_allows_exactly_once_retry(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(0),transition(1)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        world=OnlineWorld(runtime)
        with patch.object(world.model,'checkpoint',wraps=world.model.checkpoint) as save:
            original=save.side_effect
            def fail_second():
                if save.call_count==2:
                    raise OSError('disk full before checkpoint')
                return world.model.__class__.checkpoint(world.model)
            save.side_effect=fail_second
            with pytest.raises(OSError,match='disk full'):
                world.update()
        # The second observation was not durably committed.
        assert world.model.seen==1
        assert world.processed==['action-0']
        np.testing.assert_allclose(world.model.W,OnlineWorld(runtime).model.W)
        assert world.update()['learned']==1
        assert world.model.seen==2
        assert OnlineWorld(runtime).update()['learned']==0


def test_first_checkpoint_failure_resets_undurable_live_predictor(tmp_path):
    runtime=SimpleNamespace(home=tmp_path,store=object())
    rows=[transition(0)]
    with patch('v13.online_world.world_model.transitions',return_value=rows):
        world=OnlineWorld(runtime)
        with patch.object(world.model,'checkpoint',side_effect=OSError('disk full')):
            with pytest.raises(OSError,match='disk full'):
                world.update()
        assert world.model.seen==0
        assert world.processed==[]
        assert world.update()['learned']==1
        assert OnlineWorld(runtime).update()['learned']==0
