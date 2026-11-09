"""Real Store checks for isolated source-lifecycle helpers; frozen code unchanged."""
import hashlib
import json
import os
import sqlite3
import threading
import zlib
from concurrent.futures import ThreadPoolExecutor

import pytest

from v13 import archive
from v13 import source_lifecycle_candidate as helper
from v13 import vision
from v13.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    r = Runtime(tmp_path)
    r.sleep.cycle.set_policy('enabled', 'off')
    try:
        yield r
    finally:
        r.close()


def mark_deleted(r, ref):
    with r.store.tx() as c:
        c.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))


def blob(r, ref):
    return r.home / 'data/blobs' / ref['sha256']


def test_verify_or_create_without_overwrite(runtime):
    data = b'synthetic long source' * 100
    key = hashlib.sha256(data).hexdigest()
    path = runtime.home / 'data/blobs' / key
    with runtime.store.tx():
        assert helper.verify_or_create_blob(path, data, key) == 'CREATED'
        assert helper.verify_or_create_blob(path, data, key) == 'EXISTING'
    assert path.read_bytes() == data
    path.write_bytes(b'x' * len(data))
    with runtime.store.tx(), pytest.raises(ValueError, match='mismatch'):
        helper.verify_or_create_blob(path, data, key)
    assert path.read_bytes() == b'x' * len(data)


def test_bad_hash_or_symlink_never_replaced(runtime, tmp_path):
    data = b'synthetic sample'
    key = hashlib.sha256(data).hexdigest()
    path = runtime.home / 'data/blobs' / key
    with runtime.store.tx(), pytest.raises(ValueError, match='expected hash'):
        helper.verify_or_create_blob(path, data + b'bad', key)
    assert not path.exists()
    victim = tmp_path / 'victim'
    victim.write_bytes(data)
    path.symlink_to(victim)
    with runtime.store.tx(), pytest.raises(OSError):
        helper.verify_or_create_blob(path, data, key)
    assert path.is_symlink() and victim.read_bytes() == data


def test_competing_name_not_overwritten(runtime, monkeypatch):
    data = b'synthetic sample'
    key = hashlib.sha256(data).hexdigest()
    path = runtime.home / 'data/blobs' / key
    original = helper._link_anonymous
    def competitor(fd, dir_fd, name):
        path.write_bytes(b'foreign')
        return original(fd, dir_fd, name)
    monkeypatch.setattr(helper, '_link_anonymous', competitor)
    with runtime.store.tx(), pytest.raises(ValueError):
        helper.verify_or_create_blob(path, data, key)
    assert path.read_bytes() == b'foreign'


def test_new_blob_change_after_publication_fails_before_db_insert(runtime, monkeypatch):
    data = b'synthetic sample'
    key = hashlib.sha256(data).hexdigest()
    path = runtime.home / 'data/blobs' / key
    original = helper._link_anonymous
    def link_then_mutate(fd, dir_fd, name):
        original(fd, dir_fd, name)
        path.write_bytes(b'foreign')
    monkeypatch.setattr(helper, '_link_anonymous', link_then_mutate)
    with runtime.store.tx(), pytest.raises(ValueError):
        helper.verify_or_create_blob(path, data, key)
    assert path.read_bytes() == b'foreign'


def test_source_creation_write_failure_leaves_no_visible_temp(runtime, monkeypatch):
    data = b'synthetic sample'
    key = hashlib.sha256(data).hexdigest()
    path = runtime.home / 'data/blobs' / key
    before = set(path.parent.iterdir())
    def fail_after_partial(fd, value):
        os.write(fd, value[:3])
        raise OSError('injected write error')
    monkeypatch.setattr(helper, '_write_all', fail_after_partial)
    with runtime.store.tx(), pytest.raises(OSError):
        helper.verify_or_create_blob(path, data, key)
    assert set(path.parent.iterdir()) == before


def test_cleanup_requires_committed_deletion_and_preserves_shared_sources(runtime):
    text = 'synthetic source ' * 100
    first = runtime.store.source(text, 'USER')
    second = runtime.store.source(text, 'USER')
    path = blob(runtime, first)
    archive_path = path.with_name(path.name + '.z')
    archive_path.write_bytes(zlib.compress(text.encode()))
    with pytest.raises(ValueError, match='committed deleted'):
        helper.cleanup_unreferenced(runtime.store, first['source_id'])
    mark_deleted(runtime, first)
    assert helper.cleanup_unreferenced(runtime.store, first['source_id']) == 'PRESERVED_LIVE'
    assert runtime.store.read_source(second) == text and archive_path.exists()
    mark_deleted(runtime, second)
    assert helper.cleanup_unreferenced(runtime.store, first['source_id']) == 'REMOVED'
    assert not path.exists() and not archive_path.exists()
    assert helper.cleanup_unreferenced(runtime.store, first['source_id']) == 'REMOVED'


def test_cleanup_preflights_symlinks_before_any_unlink(runtime, tmp_path):
    ref = runtime.store.source('synthetic source ' * 100, 'USER')
    path = blob(runtime, ref)
    archive_path = path.with_name(path.name + '.z')
    victim = tmp_path / 'victim'
    victim.write_text('keep')
    archive_path.symlink_to(victim)
    mark_deleted(runtime, ref)
    with pytest.raises(ValueError, match='non-regular'):
        helper.cleanup_unreferenced(runtime.store, ref['source_id'])
    assert path.exists() and archive_path.is_symlink() and victim.read_text() == 'keep'


def test_cleanup_unlink_failure_is_retryable(runtime, monkeypatch):
    ref = runtime.store.source('synthetic source ' * 100, 'USER')
    path = blob(runtime, ref)
    archive_path = path.with_name(path.name + '.z')
    archive_path.write_bytes(b'archive')
    mark_deleted(runtime, ref)
    original = helper.os.unlink
    def fail_archive(name, *args, **kwargs):
        if name.endswith('.z'):
            raise OSError('injected unlink error')
        return original(name, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(helper.os, 'unlink', fail_archive)
        with pytest.raises(OSError):
            helper.cleanup_unreferenced(runtime.store, ref['source_id'])
    assert not path.exists() and archive_path.read_bytes() == b'archive'
    assert helper.cleanup_unreferenced(runtime.store, ref['source_id']) == 'REMOVED'
    assert not archive_path.exists()


def test_restore_verified_archive_and_intact_plain(runtime):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = blob(runtime, ref)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    assert helper.restore(runtime.store, ref['sha256']) == 'RESTORED'
    assert path.read_text() == text and not path.with_name(path.name + '.z').exists()
    assert runtime.store.read_source(ref) == text
    assert helper.restore(runtime.store, ref['sha256']) == 'ALREADY_PLAIN'


def test_restore_rejects_deleted_source_and_retains_archive(runtime):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = blob(runtime, ref)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    mark_deleted(runtime, ref)
    with pytest.raises(ValueError, match='no live source'):
        helper.restore(runtime.store, ref['sha256'])
    assert not path.exists() and zlib.decompress(path.with_name(path.name + '.z').read_bytes()).decode() == text


def test_restore_rejects_corrupt_plain_and_keeps_both(runtime):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = blob(runtime, ref)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    archive_path = path.with_name(path.name + '.z')
    previous_archive = archive_path.read_bytes()
    path.write_bytes(b'corrupted plain')
    with pytest.raises(ValueError):
        helper.restore(runtime.store, ref['sha256'])
    assert path.read_bytes() == b'corrupted plain' and archive_path.read_bytes() == previous_archive


@pytest.mark.parametrize('mutation', [
    lambda b: b[:-2],
    lambda b: b + b'extra',
    lambda b: b + zlib.compress(b'other'),
    lambda b: zlib.compress(b'other same size' * 100),
])
def test_restore_bad_archive_never_releases_plain_or_discards_archive(runtime, mutation):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = blob(runtime, ref)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    archive_path = path.with_name(path.name + '.z')
    bad = mutation(archive_path.read_bytes())
    archive_path.write_bytes(bad)
    before = set(path.parent.iterdir())
    with pytest.raises(ValueError):
        helper.restore(runtime.store, ref['sha256'])
    assert not path.exists() and archive_path.read_bytes() == bad
    assert set(path.parent.iterdir()) == before


def test_restore_write_failure_keeps_archive_and_no_visible_temp(runtime, monkeypatch):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = blob(runtime, ref)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    archive_path = path.with_name(path.name + '.z')
    before = archive_path.read_bytes()
    def fail_after_partial(fd, value):
        os.write(fd, value[:3])
        raise OSError('injected write error')
    monkeypatch.setattr(helper, '_write_all', fail_after_partial)
    with pytest.raises(OSError):
        helper.restore(runtime.store, ref['sha256'])
    assert not path.exists() and archive_path.read_bytes() == before
    assert {p.name for p in path.parent.iterdir()} == {archive_path.name}


def test_interrupt_after_restore_link_preserves_both_valid_copies(runtime, monkeypatch):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = blob(runtime, ref)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    archive_path = path.with_name(path.name + '.z')
    original = helper._link_anonymous
    def link_then_interrupt(*args):
        original(*args)
        raise KeyboardInterrupt('after link')
    monkeypatch.setattr(helper, '_link_anonymous', link_then_interrupt)
    with pytest.raises(KeyboardInterrupt):
        helper.restore(runtime.store, ref['sha256'])
    assert path.read_text() == text
    assert zlib.decompress(archive_path.read_bytes()).decode() == text
    assert runtime.store.read_source(ref) == text


def test_restore_detects_in_place_plain_change_before_archive_unlink(runtime, monkeypatch):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = blob(runtime, ref)
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    archive_path = path.with_name(path.name + '.z')
    before = archive_path.read_bytes()
    original = helper.os.fsync
    calls = []
    def alter_after_directory_sync(fd):
        original(fd)
        calls.append(fd)
        if len(calls) == 2:
            path.write_bytes(b'foreign replacement')
    monkeypatch.setattr(helper.os, 'fsync', alter_after_directory_sync)
    with pytest.raises(ValueError, match='published blob changed'):
        helper.restore(runtime.store, ref['sha256'])
    assert path.read_bytes() == b'foreign replacement'
    assert archive_path.read_bytes() == before


def test_helpers_reject_nested_transactions(runtime):
    ref = runtime.store.source('synthetic source ' * 100, 'USER')
    with runtime.store.tx():
        with pytest.raises(sqlite3.OperationalError, match='transaction'):
            helper.cleanup_unreferenced(runtime.store, ref['source_id'])
        with pytest.raises(sqlite3.OperationalError, match='transaction'):
            helper.restore(runtime.store, ref['sha256'])


def ppm(value=0):
    return ('P3\n8 8\n255\n' + (f'{value} 0 0\n' * 64)).encode()


def test_parallel_vision_ingests_share_one_live_registry_source(runtime, monkeypatch):
    data = ppm()
    barrier = threading.Barrier(2)
    original = vision.decode
    def simultaneous_decode(value, cfg):
        image = original(value, cfg)
        barrier.wait(timeout=5)
        return image
    monkeypatch.setattr(vision, 'decode', simultaneous_decode)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: helper.vision_ingest(runtime.store, data), range(2)))
    first, second = results
    assert first == second
    sid = first['ref']['source_id']
    assert list(vision.load(runtime.store)['images']) == [sid]
    rows = runtime.store.rows("SELECT id FROM sources WHERE kind='IMAGE' AND deleted=0")
    assert rows == [{'id': sid}]
    assert helper.vision_forget(runtime.store, first) == {'forgotten': sid}
    assert not runtime.store.rows("SELECT id FROM sources WHERE kind='IMAGE' AND deleted=0")


def test_vision_ingest_after_forget_commit_preserves_new_source(runtime, monkeypatch):
    data = ppm()
    old = helper.vision_ingest(runtime.store, data)
    entered, resume = threading.Event(), threading.Event()
    original = helper.cleanup_unreferenced
    def pause_cleanup(store, sid):
        entered.set()
        if not resume.wait(5):
            raise TimeoutError('cleanup was not resumed')
        return original(store, sid)
    monkeypatch.setattr(helper, 'cleanup_unreferenced', pause_cleanup)
    with ThreadPoolExecutor(max_workers=2) as pool:
        forgotten = pool.submit(helper.vision_forget, runtime.store, old)
        try:
            assert entered.wait(5)
            new = pool.submit(helper.vision_ingest, runtime.store, data).result(timeout=5)
        finally:
            resume.set()
        assert forgotten.result(timeout=5) == {'forgotten': old['ref']['source_id']}
    assert new['ref']['source_id'] != old['ref']['source_id']
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (old['ref']['source_id'],))['deleted'] == 1
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (new['ref']['source_id'],))['deleted'] == 0
    assert vision.read_image(runtime.store, new['ref']).size == (8, 8)


def test_vision_ingest_waits_for_cleanup_and_recreates_blob(runtime, monkeypatch):
    data = ppm()
    old = helper.vision_ingest(runtime.store, data)
    key = old['ref']['sha256']
    entered, resume, started, finished = (threading.Event() for _ in range(4))
    original = helper.os.unlink
    def pause_unlink(name, *args, **kwargs):
        if name == key:
            entered.set()
            if not resume.wait(5):
                raise TimeoutError('unlink was not resumed')
        return original(name, *args, **kwargs)
    def ingest():
        started.set()
        try:
            return helper.vision_ingest(runtime.store, data)
        finally:
            finished.set()
    monkeypatch.setattr(helper.os, 'unlink', pause_unlink)
    with ThreadPoolExecutor(max_workers=2) as pool:
        forgotten = pool.submit(helper.vision_forget, runtime.store, old)
        try:
            assert entered.wait(5)
            created = pool.submit(ingest)
            assert started.wait(5) and not finished.wait(.1)
        finally:
            resume.set()
        assert forgotten.result(timeout=5) == {'forgotten': old['ref']['source_id']}
        new = created.result(timeout=5)
    assert new['ref']['source_id'] != old['ref']['source_id']
    assert vision.read_image(runtime.store, new['ref']).size == (8, 8)


def test_vision_ingest_rejects_stale_registry_and_untracked_live_image(runtime):
    data = ppm()
    record = helper.vision_ingest(runtime.store, data)
    sid = record['ref']['source_id']
    with runtime.store.tx() as conn:
        conn.execute('UPDATE sources SET deleted=1 WHERE id=?', (sid,))
    with pytest.raises(ValueError, match='registry and live sources disagree'):
        helper.vision_ingest(runtime.store, data)
    with runtime.store.tx() as conn:
        conn.execute('UPDATE sources SET deleted=0 WHERE id=?', (sid,))
    stale = vision.load(runtime.store)
    stale['images'].clear()
    vision.save(runtime.store, stale)  # Model a legacy read-then-save race.
    with pytest.raises(ValueError, match='registry and live sources disagree'):
        helper.vision_ingest(runtime.store, data)
    assert runtime.store.rows("SELECT id FROM sources WHERE kind='IMAGE' AND deleted=0") == [{'id': sid}]


def test_vision_limits_and_symlink_fail_without_state_change(runtime, tmp_path):
    data = ppm()
    cfg = dict(vision.DEFAULTS, max_bytes=2)
    with pytest.raises(ValueError, match='groß'):
        helper.vision_ingest(runtime.store, data, cfg=cfg)
    assert not runtime.store.rows("SELECT id FROM sources WHERE kind='IMAGE'")
    key = hashlib.sha256(data).hexdigest()
    path = runtime.home / 'data/blobs' / key
    victim = tmp_path / 'victim'
    victim.write_bytes(data)
    path.symlink_to(victim)
    with pytest.raises(OSError):
        helper.vision_ingest(runtime.store, data)
    assert victim.read_bytes() == data and path.is_symlink()
    assert not runtime.store.rows("SELECT id FROM sources WHERE kind='IMAGE'")


def test_vision_forget_cleanup_failure_can_be_retried(runtime, monkeypatch):
    record = helper.vision_ingest(runtime.store, ppm())
    sid = record['ref']['source_id']
    original = helper.cleanup_unreferenced
    def fail(store, source_id):
        raise OSError('injected cleanup failure')
    with monkeypatch.context() as patch:
        patch.setattr(helper, 'cleanup_unreferenced', fail)
        with pytest.raises(OSError):
            helper.vision_forget(runtime.store, record)
    assert sid not in vision.load(runtime.store)['images']
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (sid,))['deleted'] == 1
    assert helper.cleanup_unreferenced is original
    assert helper.vision_forget(runtime.store, record) == {'forgotten': sid}
    assert not blob(runtime, record['ref']).exists()


def test_vision_state_write_failure_rolls_back_row_but_can_leave_orphan_blob(runtime, monkeypatch):
    data = ppm()
    key = hashlib.sha256(data).hexdigest()
    def fail(*args):
        raise OSError('injected state write failure')
    monkeypatch.setattr(helper, '_write_vision_state', fail)
    with pytest.raises(OSError):
        helper.vision_ingest(runtime.store, data)
    assert not runtime.store.rows("SELECT id FROM sources WHERE kind='IMAGE'")
    assert vision.load(runtime.store)['images'] == {}
    assert (runtime.home / 'data/blobs' / key).read_bytes() == data


def test_vision_forget_invalid_caption_key_fails_without_deletion(runtime, monkeypatch):
    record = helper.vision_ingest(runtime.store, ppm())
    sid = record['ref']['source_id']
    original = helper._read_vision_state
    def malformed(conn):
        state, version = original(conn)
        state['projector'] = {'captions': {7: 'retain'}}
        return state, version
    monkeypatch.setattr(helper, '_read_vision_state', malformed)
    with pytest.raises(ValueError, match='caption key'):
        helper.vision_forget(runtime.store, record)
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (sid,))['deleted'] == 0
    assert sid in vision.load(runtime.store)['images']
    assert blob(runtime, record['ref']).exists()


def test_vision_state_cas_preserves_visible_dict_and_supports_repeated_save(runtime):
    state = helper.load_vision_state(runtime.store)
    assert isinstance(state, dict)
    assert set(state) == {'revision', 'images', 'projector', 'last'}
    assert json.loads(json.dumps(state)) == dict(state)
    state['teacher_removed'] = True
    assert helper.save_vision_state(runtime.store, state) is None
    state['teacher_removed'] = False
    assert helper.save_vision_state(runtime.store, state) is None
    assert helper.load_vision_state(runtime.store)['teacher_removed'] is False
    with pytest.raises(ValueError, match='versioned'):
        helper.save_vision_state(runtime.store, dict(state))


def test_competing_vision_state_saves_reject_stale_writer(runtime):
    first = helper.load_vision_state(runtime.store)
    second = helper.load_vision_state(runtime.store)
    first['teacher_removed'] = True
    helper.save_vision_state(runtime.store, first)
    second['teacher_removed'] = False
    with pytest.raises(ValueError, match='Stale state'):
        helper.save_vision_state(runtime.store, second)
    assert helper.load_vision_state(runtime.store)['teacher_removed'] is True


def test_teacher_switch_stale_save_does_not_resurrect_forgotten_image_or_caption(runtime, monkeypatch):
    record = helper.vision_ingest(runtime.store, ppm())
    sid = record['ref']['source_id']
    state = helper.load_vision_state(runtime.store)
    caption_ref = vision.region_ref(record['ref'], record['regions'][0])
    state['images'][sid]['captions'].append({'text': 'synthetic caption', 'source_ref': caption_ref})
    state['projector'] = {'captions': {sid + ':g': 'synthetic caption'}}
    helper.save_vision_state(runtime.store, state)
    loaded, resume = threading.Event(), threading.Event()
    def paused_load(store):
        old_state = helper.load_vision_state(store)
        loaded.set()
        if not resume.wait(5):
            raise TimeoutError('stale writer not resumed')
        return old_state
    monkeypatch.setattr(vision, 'load', paused_load)
    monkeypatch.setattr(vision, 'save', helper.save_vision_state)
    with ThreadPoolExecutor(max_workers=1) as pool:
        stale_switch = pool.submit(vision.teacher_switch, runtime.store, False)
        try:
            assert loaded.wait(5)
            helper.vision_forget(runtime.store, record)
        finally:
            resume.set()
        with pytest.raises(ValueError, match='Stale state'):
            stale_switch.result(timeout=5)
    fresh = helper.load_vision_state(runtime.store)
    assert sid not in fresh['images']
    assert sid + ':g' not in fresh['projector']['captions']
    assert not blob(runtime, record['ref']).exists()


def test_fresh_state_rejects_projector_captions_from_pre_forget_dataset(runtime):
    record = helper.vision_ingest(runtime.store, ppm())
    sid = record['ref']['source_id']
    helper.vision_forget(runtime.store, record)
    fresh = helper.load_vision_state(runtime.store)
    fresh['projector'] = {'captions': {sid + ':g': 'forgotten synthetic caption'}}
    with pytest.raises(ValueError, match='projector caption'):
        helper.save_vision_state(runtime.store, fresh)
    assert helper.load_vision_state(runtime.store)['projector'] is None


def test_actual_vision_train_rejects_pre_forget_dataset_after_fresh_load(runtime, monkeypatch):
    record = helper.vision_ingest(runtime.store, ppm())
    sid = record['ref']['source_id']
    def snapshot_then_forget(store, cfg):
        texts = ['forgotten synthetic caption'] * 4
        ids = [sid + ':g'] * 4
        helper.vision_forget(store, record)
        return [0] * 4, texts, [0] * 4, ids
    class SyntheticProjector:
        def __init__(self, ridge):
            pass
        def fit(self, x, y):
            return self
        def save(self, path):
            path.parent.mkdir(parents=True, exist_ok=True)
            data = b'synthetic projector'
            path.write_bytes(data)
            return hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(vision, 'dataset', snapshot_then_forget)
    monkeypatch.setattr(vision, 'Projector', SyntheticProjector)
    monkeypatch.setattr(vision, 'crossval', lambda *args, **kwargs: {'held_out_top1': 0.})
    monkeypatch.setattr(vision, 'load', helper.load_vision_state)
    monkeypatch.setattr(vision, 'save', helper.save_vision_state)
    with pytest.raises(ValueError, match='projector caption'):
        vision.train(runtime, encoder=('synthetic', lambda values: [0] * len(values)))
    fresh = helper.load_vision_state(runtime.store)
    assert sid not in fresh['images'] and fresh['projector'] is None
    assert list((runtime.home / 'data/vision').glob('projector-*.npz'))  # pre-save side effect remains


def test_vision_state_rejects_forged_source_reference(runtime):
    record = helper.vision_ingest(runtime.store, ppm())
    sid = record['ref']['source_id']
    state = helper.load_vision_state(runtime.store)
    state['images'][sid]['ref']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='non-live image source'):
        helper.save_vision_state(runtime.store, state)
    assert helper.load_vision_state(runtime.store)['images'][sid]['ref']['sha256'] == record['ref']['sha256']
