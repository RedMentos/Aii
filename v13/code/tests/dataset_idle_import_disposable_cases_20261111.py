"""Actual G13 -> offline external SourceRef, with no inference or training."""
import hashlib
import json
from pathlib import Path
import threading
import time

import pytest

from v13 import dataset_idle_import_candidate as importer
from v13 import dataset_probe_candidate as probe
from v13 import inputs
from v13.agi.weights import NullTrainer
from v13.body_jepa import BodyJepaTrainer
from v13.lora_trainer import LoraTrainer
from v13.operator import Operator
from v13.runtime import Runtime
from v13.store import Store


def forbidden(*args, **kwargs):
    pytest.fail('record importer invoked network or a trainer')


@pytest.fixture(autouse=True)
def no_network_or_training(monkeypatch):
    for name in ('fetch_one', 'stage_one', '_open_viewer'):
        monkeypatch.setattr(probe, name, forbidden)
    for trainer in (NullTrainer, BodyJepaTrainer, LoraTrainer):
        monkeypatch.setattr(trainer, 'fit', forbidden)


def prepare(runtime):
    runtime.sleep.cycle.set_policy('enabled', 'off')
    runtime.sleep.cycle.set_policy('tick_seconds', '1')
    assert runtime.cfg['learning_mode'] == 'RECORD_ONLY'


@pytest.fixture
def live(tmp_path):
    runtime = Runtime(tmp_path / 'home')
    try:
        prepare(runtime)
        yield runtime
    finally:
        runtime.close()


def stage(directory, texts=('A synthetic source about ordinary blue stones.',), dataset_id='cosmo_small'):
    """Write a synthetic local viewer receipt; never use the network stager."""
    directory.mkdir(parents=True, exist_ok=True)
    entry = probe.load_catalog()[dataset_id]
    files = []
    for offset, text in enumerate(texts):
        row = {'text': text, 'fixture': 'SYNTHETIC_ONLY'}
        value = dict(schema='v13-dataset-preview-v1', dataset_id=dataset_id,
                     **{key: entry[key] for key in ('repo', 'config', 'split', 'revision')},
                     offset=offset, total_rows=len(texts), row=row,
                     row_sha256=hashlib.sha256(probe._json_bytes(row)).hexdigest(),
                     response_sha256=hashlib.sha256(b'synthetic offline receipt').hexdigest(),
                     purpose='PREVIEW_ONLY', training_authority=0)
        path = directory / probe._filename(entry, offset)
        path.write_bytes(probe._json_bytes(value) + b'\n')
        files.append(path)
    return files


def admit(runtime, directory, offsets=(0,), **kwargs):
    return importer.admit_record(runtime, 'cosmo_small', directory, offsets,
                                 authority=importer.HUMAN, **kwargs)['admission_id']


def make_due(runtime):
    importer.box(runtime).mutate(lambda state: state.update(last_attempt=time.time() - 1000.))


def wait_result(runtime, event_id):
    end = time.monotonic() + 10.
    while time.monotonic() < end:
        result = importer.status(runtime)['last_result']
        if result and result['event_id'] == event_id and runtime.idle():
            return result
        time.sleep(.01)
    raise AssertionError('record import did not finish: ' + repr(runtime.sleep.scheduler.report()))


def request(runtime):
    event_id = json.loads(Operator(runtime).run(':dataset step'))['scheduled']
    assert event_id is not None
    return wait_result(runtime, event_id)


def sources(runtime):
    return runtime.store.rows('SELECT id,kind,hash,deleted FROM sources WHERE kind=?', (importer.KIND,))


def test_actual_scheduler_source_restart_and_no_duplicate(tmp_path):
    directory = tmp_path / 'previews'
    texts = ('First synthetic external reading.', 'Second synthetic external reading.')
    stage(directory, texts)
    runtime = Runtime(tmp_path / 'home')
    try:
        prepare(runtime)
        # Exercise the actual Operator admission and explicit activation seams.
        choice = json.loads(Operator(runtime).run(':dataset admit cosmo_small ' + str(directory) + ' offsets=0,1 field=text'))
        key = choice['admission_id']
        Operator(runtime).run(':dataset on')
        first = request(runtime)
        assert first['status'] == 'IMPORTED' and first['persisted'] and first['training_authority'] == 0
        assert runtime.store.read_source(first['source_ref']) == texts[0]
        assert sources(runtime)[0]['kind'] == 'EXTERNAL_DATASET'
        assert not runtime.store.rows('SELECT id FROM events')
        assert not runtime.store.rows('SELECT id FROM feedback')
        assert not runtime.store.rows('SELECT id FROM memories')
        assert not runtime.store.rows('SELECT id FROM updates')
        generation = runtime.store.generation_id
        runtime.close()
        runtime = Runtime(tmp_path / 'home'); prepare(runtime)
        assert importer.status(runtime)['enabled']
        assert runtime.store.read_source(first['source_ref']) == texts[0]
        assert admit(runtime, directory, (0, 1)) == key
        make_due(runtime)
        second = request(runtime)
        assert second['offset'] == 1 and runtime.store.read_source(second['source_ref']) == texts[1]
        assert len(sources(runtime)) == 2 and importer.status(runtime)['imported_rows'] == 2
        make_due(runtime)
        assert request(runtime)['status'] == 'SKIPPED_NO_PENDING_RECORDS'
        assert len(sources(runtime)) == 2 and runtime.store.generation_id == generation
        events = runtime.sleep.scheduler.report()['history']
        assert next(e for e in events if e['id'] == first['event_id'])['origin'] == 'USER'
        print('DATASET_RECORD_RUNTIME', json.dumps(dict(actual_scheduler=True, restart=True,
              source_kind='EXTERNAL_DATASET', imported_rows=2, training_authority=0, native_or_redmi=False)))
    finally:
        runtime.close()


def test_default_off_explicit_authority_and_actual_owner_required(live, tmp_path):
    runtime = live; directory = tmp_path / 'preview'; stage(directory)
    assert not importer.status(runtime)['enabled'] and importer.maybe_post(runtime) is None
    with pytest.raises(PermissionError):
        importer.admit_record(runtime, 'cosmo_small', directory)
    with pytest.raises(PermissionError):
        importer.set_enabled(runtime, True)
    with pytest.raises(importer.ImportRefused, match='enable'):
        importer.operator(runtime, ['step'])
    with pytest.raises(PermissionError):
        importer.step(runtime, {'id':'unowned', 'action':importer.ACTION, 'origin':'SYSTEM'})
    assert not sources(runtime)


def test_another_thread_cannot_take_over_dispatched_import(live, tmp_path, monkeypatch):
    runtime = live; directory = tmp_path/'preview';stage(directory);admit(runtime, directory)
    step = importer.step
    def actual_job(runtime, event):
        refused = []
        def foreign_call():
            try:step(runtime, event)
            except PermissionError:refused.append(True)
        caller = threading.Thread(target=foreign_call)
        caller.start();caller.join(timeout=10)
        assert not caller.is_alive() and refused == [True]
        assert importer.status(runtime)['charged_rows'] == 0 and not sources(runtime)
        return step(runtime, event)
    monkeypatch.setattr(importer, 'step', actual_job)
    importer.set_enabled(runtime, True, importer.HUMAN)
    assert request(runtime)['imported']
    assert importer.status(runtime)['charged_rows'] == 1


def test_configured_system_job_records_while_training_is_paused(live, tmp_path):
    runtime = live; directory = tmp_path / 'preview'; stage(directory)
    admit(runtime, directory)
    inputs.set_pause(runtime.store, 'training', True)
    importer.configure(runtime, {'min_idle_s':0}, importer.HUMAN)
    importer.set_enabled(runtime, True, importer.HUMAN)
    event_id = importer.maybe_post(runtime)
    if event_id is None:
        matches = [e for e in runtime.sleep.scheduler.pending() if e['action'] == importer.ACTION]
        event_id = matches[0]['id'] if matches else importer.status(runtime)['last_result']['event_id']
    result = wait_result(runtime, event_id)
    assert result['imported'] and result['training_authority'] == 0 and not result['weights_updated']
    event = next(e for e in runtime.sleep.scheduler.report()['history'] if e['id'] == event_id)
    assert event['origin'] == 'SYSTEM'
    assert runtime.cfg['learning_mode'] == 'RECORD_ONLY' and runtime.cfg['system_stage'] == 0


@pytest.mark.parametrize('name', ['gsm8k_train', 'open_assistant', 'does_not_exist'])
def test_held_unknown_or_evaluation_datasets_cannot_be_admitted(live, tmp_path, name):
    with pytest.raises((importer.ImportRefused, probe.ProbeError)):
        importer.admit_record(live, name, tmp_path, authority=importer.HUMAN)
    assert importer.status(live)['admissions'] == []


def test_changed_valid_preview_is_not_reauthorized_and_failures_keep_quota(live, tmp_path):
    runtime = live; directory = tmp_path / 'preview'; paths = stage(directory)
    key = admit(runtime, directory)
    # Still a well-formed probe receipt, but different from the human selection.
    value = json.loads(paths[0].read_text()); value['row']['text'] = 'Different synthetic text.'
    value['row_sha256'] = hashlib.sha256(probe._json_bytes(value['row'])).hexdigest()
    paths[0].write_bytes(probe._json_bytes(value) + b'\n')
    importer.set_enabled(runtime, True, importer.HUMAN)
    result = request(runtime)
    assert result['status'] == 'BLOCKED_IMPORT' and not result['imported']
    assert 'changed' in result['blocked_reason']
    state = importer.box(runtime).load()[0]
    assert state['charged_rows'] == 1 and state['admissions'][key]['cursor'] == 0
    assert not sources(runtime)
    assert request(runtime)['status'] == 'SKIPPED_COOLDOWN'
    assert importer.status(runtime)['charged_rows'] == 1


def test_replaced_preview_symlink_and_changed_catalog_are_refused(live, tmp_path, monkeypatch):
    runtime = live; directory = tmp_path / 'preview'; paths = stage(directory)
    admit(runtime, directory)
    data = paths[0].read_bytes(); other = tmp_path / 'other.json'; other.write_bytes(data)
    paths[0].unlink(); paths[0].symlink_to(other)
    importer.set_enabled(runtime, True, importer.HUMAN)
    assert request(runtime)['status'] == 'BLOCKED_IMPORT'
    assert not sources(runtime)
    paths[0].unlink(); paths[0].write_bytes(data)
    make_due(runtime)
    monkeypatch.setattr(probe, 'CATALOG_SHA256', '0' * 64)
    assert request(runtime)['status'] == 'BLOCKED_IMPORT'
    assert not sources(runtime)


def test_revocation_before_publication_vetoes_the_reserved_job(live, tmp_path, monkeypatch):
    runtime = live; directory = tmp_path / 'preview'; stage(directory)
    key = admit(runtime, directory)
    reserve = importer._reserve
    def withdraw_after_reservation(*args):
        result = reserve(*args)
        importer.revoke(runtime, key, importer.HUMAN)
        return result
    monkeypatch.setattr(importer, '_reserve', withdraw_after_reservation)
    importer.set_enabled(runtime, True, importer.HUMAN)
    result = request(runtime)
    assert result['status'] == 'BLOCKED_IMPORT' and not result['imported']
    assert not sources(runtime) and importer.status(runtime)['charged_rows'] == 1
    with pytest.raises(importer.ImportRefused, match='revoked'):
        admit(runtime, directory)


def test_revocation_invalidates_only_its_own_source_and_preserves_files_and_charges(live, tmp_path):
    runtime = live; one = tmp_path / 'one'; two = tmp_path / 'two'
    stage(one); stage(two)
    key = admit(runtime, one); admit(runtime, two)
    importer.set_enabled(runtime, True, importer.HUMAN)
    first = request(runtime); make_due(runtime); second = request(runtime)
    assert first['source_ref']['sha256'] == second['source_ref']['sha256']
    assert first['source_ref']['source_id'] != second['source_ref']['source_id']
    before = importer.status(runtime)['charged_bytes']
    with pytest.raises(PermissionError):
        importer.revoke(runtime, key)
    result = importer.revoke(runtime, key, importer.HUMAN)
    assert not result['files_deleted'] and not result['quota_refunded']
    with pytest.raises(ValueError):
        runtime.store.read_source(first['source_ref'])
    assert runtime.store.read_source(second['source_ref'])
    assert (runtime.home / 'data/blobs' / first['source_ref']['sha256']).is_file()
    assert importer.status(runtime)['charged_bytes'] == before


def test_source_receipt_and_cursor_roll_back_together_after_publication_error(live, tmp_path, monkeypatch):
    runtime = live; directory = tmp_path / 'preview'; stage(directory)
    key = admit(runtime, directory)
    setter = Store.set_state
    def fail_after_source(self, name, payload, expected=None):
        if name == importer.KEY and payload['imported_rows']:
            raise OSError('synthetic failure before receipt publication')
        return setter(self, name, payload, expected)
    importer.set_enabled(runtime, True, importer.HUMAN)
    with monkeypatch.context() as patch:
        patch.setattr(Store, 'set_state', fail_after_source)
        result = request(runtime)
    assert result['status'] == 'BLOCKED_IMPORT' and not sources(runtime)
    state = importer.box(runtime).load()[0]
    assert state['admissions'][key]['cursor'] == 0 and state['charged_rows'] == 1
    # A failed DB commit can leave a bounded orphan blob. Its budget stays charged.
    sha = state['admissions'][key]['rows'][0]['field_sha256']
    assert (runtime.home / 'data/blobs' / sha).is_file()
    make_due(runtime)
    assert request(runtime)['imported'] and len(sources(runtime)) == 1
    assert importer.status(runtime)['charged_rows'] == 2


@pytest.mark.parametrize('quota', ['daily_rows', 'daily_bytes', 'total_rows', 'total_bytes'])
def test_daily_and_total_attempt_quotas_cannot_be_reset_by_a_new_event(live, tmp_path, quota):
    runtime = live; directory = tmp_path / 'preview'
    text = 'Tiny synthetic reading.'; stage(directory, (text, text))
    limit = 1 if quota.endswith('rows') else len(text.encode()) + importer.RECEIPT_BYTES
    importer.configure(runtime, {quota:limit}, importer.HUMAN)
    admit(runtime, directory, (0, 1))
    importer.set_enabled(runtime, True, importer.HUMAN)
    assert request(runtime)['imported']; make_due(runtime)
    result = request(runtime)
    assert result['status'] == ('SKIPPED_DAILY_QUOTA' if quota.startswith('daily') else 'SKIPPED_TOTAL_QUOTA')
    assert len(sources(runtime)) == importer.status(runtime)['charged_rows'] == 1


def test_raising_global_limits_cannot_expand_an_existing_grant(live, tmp_path):
    runtime = live; directory = tmp_path / 'preview'; stage(directory, ('First.', 'Second.'))
    admit(runtime, directory, (0, 1), quotas={'total_rows':1})
    importer.configure(runtime, {'total_rows':128}, importer.HUMAN)
    importer.set_enabled(runtime, True, importer.HUMAN)
    assert request(runtime)['imported']; make_due(runtime)
    assert request(runtime)['status'] == 'SKIPPED_TOTAL_QUOTA'
    assert len(sources(runtime)) == 1


@pytest.mark.parametrize('condition,reason', [('queue','USER_OR_JOB_WAITING'), ('cancel','PAUSED_OR_CANCELLED'),
                                           ('pause','PAUSED_OR_CANCELLED'), ('resources','RESOURCES')])
def test_dispatched_import_rechecks_foreground_pause_cancel_and_resources(live, tmp_path, monkeypatch, condition, reason):
    runtime = live; directory = tmp_path / 'preview'; stage(directory); admit(runtime, directory)
    reserve = importer._reserve
    def gated(*args):
        with monkeypatch.context() as patch:
            if condition == 'queue':patch.setattr(runtime.jobs, 'empty', lambda:False)
            elif condition == 'cancel':patch.setattr(runtime.cancel_event, 'is_set', lambda:True)
            elif condition == 'pause':patch.setattr(runtime, 'paused', True)
            else:patch.setattr(runtime.guard, 'state', 'PRESSURE')
            return reserve(*args)
    monkeypatch.setattr(importer, '_reserve', gated)
    importer.set_enabled(runtime, True, importer.HUMAN)
    assert request(runtime)['status'] == 'SKIPPED_' + reason
    assert not sources(runtime) and importer.status(runtime)['charged_rows'] == 0


def test_system_event_rechecks_minimum_idle_at_dispatch(live, tmp_path):
    runtime = live; directory = tmp_path / 'preview'; stage(directory); admit(runtime, directory)
    importer.set_enabled(runtime, True, importer.HUMAN)
    event_id = runtime.sleep.scheduler.post('TIMER', origin='SYSTEM', action=importer.ACTION, ttl=60)
    runtime.wake.set()
    assert wait_result(runtime, event_id)['status'] == 'SKIPPED_MIN_IDLE'
    assert not sources(runtime) and importer.status(runtime)['charged_rows'] == 0
    assert request(runtime)['imported']


def test_expired_cooperative_budget_cannot_publish_a_source(live, tmp_path, monkeypatch):
    runtime = live; directory = tmp_path / 'preview'; stage(directory); admit(runtime, directory)
    check = importer._check_grant
    def expire(grant, budget):
        budget.deadline = budget.clock() - 1.
        return check(grant, budget)
    monkeypatch.setattr(importer, '_check_grant', expire)
    importer.set_enabled(runtime, True, importer.HUMAN)
    result = request(runtime)
    assert result['status'] == 'BLOCKED_IMPORT' and result['blocked_reason'] == 'CANCELLED_OR_DEADLINE'
    assert not sources(runtime) and importer.status(runtime)['charged_rows'] == 1


@pytest.mark.parametrize('overrides', [{'daily_rows':True}, {'daily_rows':33}, {'row_bytes':16385},
                                     {'total_bytes':float('nan')}, {'deadline_ms':0}, {'training_authority':1}])
def test_invalid_configuration_never_mutates_policy(live, overrides):
    before = importer.box(live).load()[0]
    with pytest.raises(importer.ImportRefused):
        importer.configure(live, overrides, importer.HUMAN)
    assert importer.box(live).load()[0] == before
