"""Actual old Ridge mutation versus shared live training admission."""
import pytest
from unittest.mock import Mock

from v13 import authority, inputs, world_model
from v13.operator import Operator
from v13.runtime import Runtime
from integrated_jepa_disposable_cases import populate


@pytest.mark.parametrize('action', ['learn_medium', 'learn_slow'])
@pytest.mark.parametrize('condition,reason', [('record','RECORD_ONLY'), ('pause','PAUSED_TRAINING'),
                                           ('cancel','PAUSED_OR_CANCELLED'),
                                           ('resources','RESOURCES'), ('queue','USER_OR_JOB_WAITING')])
def test_legacy_learning_checks_before_review_or_numeric_mutation(tmp_path, monkeypatch, action, condition, reason):
    runtime = Runtime(tmp_path)
    try:
        runtime.sleep.cycle.set_policy('enabled', 'off')
        Operator(runtime).run(':learning shadow')
        if condition == 'record':runtime.cfg['learning_mode'] = 'RECORD_ONLY'
        elif condition == 'pause':inputs.set_pause(runtime.store, 'training', True)
        elif condition == 'cancel':runtime.cancel_event.set()
        elif condition == 'resources':runtime.guard.state = 'PRESSURE'
        else:monkeypatch.setattr(runtime.jobs, 'empty', lambda:False)
        before = runtime.store.state(world_model.KEY, None)
        review = Mock(side_effect=AssertionError('review must follow admission'))
        monkeypatch.setattr(authority, 'review', review)
        result = authority.job(runtime, action)
        assert result['status'] == 'SKIPPED_'+reason and not result['review']
        assert runtime.store.state(world_model.KEY, None) == before
        review.assert_not_called()
    finally:
        monkeypatch.undo()
        runtime.close()


def test_authorized_medium_still_fits_actual_ridge(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        populate(runtime)
        Operator(runtime).run(':learning shadow')
        result = authority.job(runtime, 'learn_medium')
        state = runtime.store.state(world_model.KEY, None)[0]
        assert result['world_model'] == state['status'] == 'FITTED' and state['n'] >= 32
    finally:
        runtime.close()
