"""Real G13 worker -> bounded numeric JEPA -> private restart; synthetic only."""
import json
import shutil
import threading
import time

import numpy as np
import pytest

from v13 import inputs
from v13 import world_jepa_idle_runtime_candidate as idle
from v13.operator import Operator
from v13.runtime import Runtime
from integrated_jepa_disposable_cases import populate


def wait_result(runtime, event_id, seconds=10):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        record = idle.status(runtime)['last_result']
        if record and record.get('event_id') == event_id and runtime.idle():
            return record
        time.sleep(.01)
    raise AssertionError('idle World job did not finish: ' + repr(runtime.sleep.scheduler.report()))


def request(runtime):
    answer = json.loads(Operator(runtime).run(':learning idle step'))
    assert answer['scheduled'] is not None
    return wait_result(runtime, answer['scheduled'])


def make_due(runtime):
    idle.box(runtime).mutate(lambda state: state.update(last_attempt=time.time() - 1000.))


@pytest.fixture
def empty_live(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        runtime.sleep.cycle.set_policy('enabled', 'off')
        Operator(runtime).run(':learning shadow')
        yield runtime
    finally:
        runtime.close()


@pytest.fixture(scope='module')
def recorded_home(tmp_path_factory):
    home = tmp_path_factory.mktemp('idle-real-recorded-source')
    runtime = Runtime(home)
    try:
        populate(runtime)
    finally:
        runtime.close()
    return home


@pytest.fixture
def live(recorded_home, tmp_path):
    home = tmp_path/'runtime'
    shutil.copytree(recorded_home, home)
    runtime = Runtime(home)
    try:
        runtime.sleep.cycle.set_policy('enabled', 'off')
        Operator(runtime).run(':learning shadow')
        yield runtime
    finally:
        runtime.close()


def test_real_scheduled_update_persists_and_restart_continues_optimizer(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        populate(runtime)
        operator = Operator(runtime)
        operator.run(':learning shadow')
        operator.run(':learning idle on')
        result = request(runtime)
        assert result['status'] == 'UPDATED' and result['trained'] and result['persisted']
        first = runtime._world_jepa_online
        assert first._fit_steps == first._training_state['main']['t'] == 1
        weights = first.enc['W1'].copy()
        receipts = dict(runtime._world_jepa_lineage)
        assert (runtime.home / 'world_jepa_lineage/manifest.json').is_file()
        assert idle.status(runtime)['reserved_today'] == 1
        denied = runtime.world_jepa_update(steps=1, limit=64, authority=idle.AUTHORITY)
        assert not denied['trained'] and runtime._world_jepa_online._fit_steps == 1
        runtime.close()
        runtime = Runtime(tmp_path)
        runtime.sleep.cycle.set_policy('enabled', 'off')
        assert idle.status(runtime)['enabled'] and idle.status(runtime)['reserved_today'] == 1
        assert not hasattr(runtime, '_world_jepa_online')
        make_due(runtime)
        result = request(runtime)
        assert result['status'] == 'UPDATED' and result['persisted']
        assert runtime._world_jepa_online._fit_steps == runtime._world_jepa_online._training_state['main']['t'] == 2
        assert not np.array_equal(runtime._world_jepa_online.enc['W1'], weights)
        assert runtime._world_jepa_lineage == receipts
        assert idle.status(runtime)['reserved_today'] == 2
        print('IDLE_JEPA_RUNTIME', json.dumps({'first_steps':1, 'restart_steps':2,
              'private_persistence':True, 'actual_scheduler':True, 'native_or_redmi':False}))
    finally:
        runtime.close()


def test_default_off_and_unsupported_direct_authority_never_create_model(empty_live):
    runtime = empty_live
    assert not idle.status(runtime)['enabled']
    assert idle.maybe_post(runtime) is None
    with pytest.raises(PermissionError):
        idle.set_enabled(runtime, True)
    with pytest.raises(ValueError, match='enable idle'):
        idle.operator(runtime, ['step'])
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    result = runtime.world_jepa_update(steps=1, limit=64, authority=idle.AUTHORITY)
    assert not result['trained']
    for operation in ('update', 'save', 'restore'):
        assert idle.scope_blocked(runtime, operation) == 'OWNER_REQUIRED'
        with pytest.raises(PermissionError):
            idle.require_owner(runtime, operation)
    for method in (runtime.world_jepa_save, runtime.world_jepa_restore):
        with pytest.raises(PermissionError):
            method(authority=idle.AUTHORITY)
    assert not hasattr(runtime, '_world_jepa_online')


def test_actual_owner_cannot_expand_reserved_step_or_row_budget(live, monkeypatch):
    runtime = live
    update = runtime.world_jepa_update
    def capped_update(*args, **kwargs):
        for steps, rows in ((2, 64), (1, 65), (True, 64), (1, True)):
            with pytest.raises(ValueError):
                update(steps=steps, limit=rows, authority=idle.AUTHORITY)
        foreign = []
        caller = threading.Thread(target=lambda:foreign.append(update(steps=1, limit=64, authority=idle.AUTHORITY)))
        caller.start();caller.join(timeout=10)
        assert not caller.is_alive() and len(foreign) == 1 and not foreign[0]['trained']
        result = update(*args, **kwargs)
        repeated = update(steps=1, limit=64, authority=idle.AUTHORITY)
        assert repeated['status'] == 'SKIPPED_UPDATE_ALREADY_USED' and not repeated['trained']
        return result
    monkeypatch.setattr(runtime, 'world_jepa_update', capped_update)
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    result = request(runtime)
    assert result['trained'] and result['persisted']
    assert runtime._world_jepa_online._fit_steps == 1
    assert idle.status(runtime)['reserved_today'] == 1


@pytest.mark.parametrize('condition', ['record', 'pause', 'resources'])
def test_dispatched_job_rechecks_mode_pause_and_resources_before_update(live, monkeypatch, condition):
    runtime = live
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    if condition == 'record':
        runtime.cfg['learning_mode'] = 'RECORD_ONLY'
    elif condition == 'pause':
        inputs.set_pause(runtime.store, 'training', True)
    else:
        runtime.guard.state = 'PRESSURE'
        # Let the scheduler dispatch this USER request, then preserve the
        # failing live resource guard checked by the learner itself.
        monkeypatch.setattr(runtime.sleep, 'resource_state', lambda:'NORMAL')
    result = request(runtime)
    assert not result['trained'] and not result['persisted']
    assert result['status'].startswith('SKIPPED_')
    assert not hasattr(runtime, '_world_jepa_online')
    assert not (runtime.home / 'world_jepa_lineage').exists()
    assert idle.status(runtime)['reserved_today'] == 0


def test_cooldown_and_daily_budget_survive_repeated_requests(live):
    runtime = live
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    assert request(runtime)['trained']
    assert request(runtime)['status'] == 'SKIPPED_COOLDOWN'
    assert runtime._world_jepa_online._fit_steps == 1
    idle.configure(runtime, {'daily_steps':1}, 'EXPLICIT_HUMAN')
    assert request(runtime)['status'] == 'SKIPPED_DAILY_BUDGET'
    assert runtime._world_jepa_online._fit_steps == 1
    assert idle.status(runtime)['reserved_today'] == 1


def test_failed_input_still_reserves_budget_and_cannot_hot_loop(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        runtime.sleep.cycle.set_policy('enabled', 'off')
        Operator(runtime).run(':learning shadow')
        idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
        result = request(runtime)
        assert result['status'] == 'BLOCKED_INPUT' and not result['trained']
        assert idle.status(runtime)['reserved_today'] == 1
        assert request(runtime)['status'] == 'SKIPPED_COOLDOWN'
        assert not hasattr(runtime, '_world_jepa_online')
    finally:
        runtime.close()


def test_clock_rollback_cannot_reset_cooldown_or_daily_budget(empty_live):
    runtime = empty_live
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    idle.box(runtime).mutate(lambda state: state.update(last_attempt=time.time()+3600.))
    assert request(runtime)['status'] == 'SKIPPED_CLOCK_ROLLBACK'
    assert not hasattr(runtime, '_world_jepa_online')


def test_actual_configured_system_job_uses_existing_worker_without_human_spoof(live):
    runtime = live
    idle.configure(runtime, {'min_idle_s':0}, 'EXPLICIT_HUMAN')
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    event_id = idle.maybe_post(runtime)
    if event_id is None:
        matches = [e for e in runtime.sleep.scheduler.pending() if e['action'] == idle.ACTION]
        if matches:
            event_id = matches[0]['id']
        else:
            record = idle.status(runtime)['last_result']
            assert record and record['trained']
            event_id = record['event_id']
    result = wait_result(runtime, event_id)
    assert result['trained'] and result['persisted']
    history = runtime.sleep.scheduler.report()['history']
    event = next(e for e in history if e['id'] == event_id)
    assert event['origin'] == 'SYSTEM' and event['action'] == idle.ACTION
    assert runtime.cfg['system_stage'] == 0
    assert idle.AUTHORITY != 'EXPLICIT_HUMAN'


def test_foreground_queue_prevents_automatic_job_post(empty_live, monkeypatch):
    runtime = empty_live
    with monkeypatch.context() as blocked:
        blocked.setattr(runtime.jobs, 'empty', lambda:False)
        idle.configure(runtime, {'min_idle_s':0}, 'EXPLICIT_HUMAN')
        idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
        assert idle.maybe_post(runtime) is None
        assert idle.status(runtime)['blocked_reason'] == 'USER_OR_JOB_WAITING'


def test_system_job_rechecks_idle_duration_at_actual_dispatch(live, monkeypatch):
    runtime = live
    monkeypatch.setattr(runtime.sleep, 'idle_seconds', lambda:100.)
    reserve = idle._reserve
    def foreground_activity_before_dispatch(runtime, event, marker):
        monkeypatch.setattr(runtime.sleep, 'idle_seconds', lambda:0.)
        return reserve(runtime, event, marker)
    monkeypatch.setattr(idle, '_reserve', foreground_activity_before_dispatch)
    idle.configure(runtime, {'min_idle_s':1}, 'EXPLICIT_HUMAN')
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    event_id = idle.maybe_post(runtime)
    if event_id is None:
        matches = [e for e in runtime.sleep.scheduler.pending() if e['action'] == idle.ACTION]
        event_id = matches[0]['id'] if matches else idle.status(runtime)['last_result']['event_id']
    result = wait_result(runtime, event_id)
    assert result['status'] == 'SKIPPED_MIN_IDLE' and not result['trained']
    assert idle.status(runtime)['reserved_today'] == 0
    assert not hasattr(runtime, '_world_jepa_online')


def test_unconfirmed_save_quarantines_and_never_claims_durable_success(live, monkeypatch):
    runtime = live
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    def fail_save(*args, **kwargs):
        raise OSError('synthetic ambiguous checkpoint publication')
    monkeypatch.setattr(runtime, 'world_jepa_save', fail_save)
    result = request(runtime)
    assert result['status'] == 'SAVE_UNCERTAIN_QUARANTINED'
    assert result['trained'] and result['persisted'] is None
    assert result['checkpoint_outcome'] == 'UNKNOWN_AFTER_SAVE_ERROR'
    assert runtime._world_jepa_quarantined
    assert idle.status(runtime)['quarantined']
    assert request(runtime)['status'] == 'SKIPPED_QUARANTINED'
    assert runtime._world_jepa_online._fit_steps == 1


def test_post_publish_failure_requires_explicit_recovery_and_preserves_budget(live, monkeypatch):
    runtime = live
    idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    assert request(runtime)['persisted']
    make_due(runtime)
    save = runtime.world_jepa_save
    def fail_after_publish(*args, **kwargs):
        save(*args, **kwargs)
        raise OSError('synthetic error after confirmed manifest publication')
    with monkeypatch.context() as patch:
        patch.setattr(runtime, 'world_jepa_save', fail_after_publish)
        result = request(runtime)
    assert result['persisted'] is None and result['quarantined']
    assert idle.status(runtime)['reserved_today'] == 2
    with pytest.raises(ValueError, match='recover'):
        idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
    with pytest.raises(PermissionError):
        idle.recover(runtime)
    recovered = idle.recover(runtime, 'EXPLICIT_HUMAN')
    assert recovered['restored'] and not idle.status(runtime)['quarantined']
    assert runtime._world_jepa_online._fit_steps == 2
    assert idle.status(runtime)['reserved_today'] == 2


@pytest.mark.parametrize('config', [{'daily_steps':True}, {'daily_steps':33}, {'max_rows':129},
                                   {'interval_s':0}, {'enabled':True}, {'max_rows':float('nan')}])
def test_invalid_budget_configuration_does_not_change_policy(empty_live, config):
    runtime = empty_live
    before = idle.box(runtime).load()[0]
    with pytest.raises(ValueError):
        idle.configure(runtime, config, 'EXPLICIT_HUMAN')
    assert idle.box(runtime).load()[0] == before
