"""Run only inside the hash-bound materialized copy, never on frozen sources."""
import os
from pathlib import Path
import threading
import time

import pytest

from v13 import archive, source_lifecycle_candidate as lifecycle, vision
from v13.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    r = Runtime(tmp_path)
    r.sleep.cycle.set_policy('enabled', 'off')
    try:
        yield r
    finally:
        r.close()


def future():
    return time.time() + (archive.ARCHIVE_DAYS + 1) * 86400


def old_fact(r, text):
    event = r.store.event(r.session, 'synthetic event')
    mid = r.memory.feedback(event['event_id'], 'fact', text)
    r.memory.feedback(event['event_id'], 'fact', 'synthetic newer decision ' * 50)
    row = r.store.one('SELECT s.id,s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?', (mid,))
    return mid, row


def test_new_source_before_cleanup_keeps_its_bytes(runtime, monkeypatch):
    text = 'synthetic shared source ' * 100
    mid, row = old_fact(runtime, text)
    created = []
    original = lifecycle.cleanup_unreferenced
    def create_then_cleanup(store, source_id):
        created.append(store.source(text, 'USER'))
        return original(store, source_id)
    monkeypatch.setattr(lifecycle, 'cleanup_unreferenced', create_then_cleanup)
    runtime.memory.forget(mid)
    assert created and runtime.store.read_source(created[0]) == text
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (row['id'],))['deleted'] == 1


def test_new_source_waits_while_old_hash_is_removed(runtime, monkeypatch):
    text = 'synthetic shared source ' * 100
    mid, row = old_fact(runtime, text)
    key = row['hash']
    at_unlink, release, started, done = (threading.Event() for _ in range(4))
    errors, new = [], []
    original = os.unlink
    def paused_unlink(path, *args, **kwargs):
        if Path(path).name == key and not at_unlink.is_set():
            at_unlink.set()
            if not release.wait(5):
                raise TimeoutError('test did not release unlink')
        return original(path, *args, **kwargs)
    def forget():
        try: runtime.memory.forget(mid)
        except BaseException as exc: errors.append(exc)
    def create():
        started.set()
        try: new.append(runtime.store.source(text, 'USER'))
        except BaseException as exc: errors.append(exc)
        finally: done.set()
    monkeypatch.setattr(os, 'unlink', paused_unlink)
    forget_thread = threading.Thread(target=forget)
    create_thread = threading.Thread(target=create)
    forget_thread.start()
    try:
        assert at_unlink.wait(5)
        create_thread.start()
        assert started.wait(5) and not done.wait(.1)
    finally:
        release.set()
        forget_thread.join(5)
        if create_thread.ident is not None: create_thread.join(5)
    assert not forget_thread.is_alive() and not create_thread.is_alive()
    assert not errors and new and runtime.store.read_source(new[0]) == text


def test_active_image_prevents_shared_source_from_being_archived(runtime, monkeypatch):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    source = runtime.store.source(text, 'USER')
    verified, release, archive_started, archive_done = (threading.Event() for _ in range(4))
    original = lifecycle.verify_or_create_blob
    errors, records, results = [], [], []
    def pause_image(path, data, key):
        result = original(path, data, key)
        if key == source['sha256']:
            verified.set()
            if not release.wait(5): raise TimeoutError('test did not release image writer')
        return result
    def ingest():
        try: records.append(vision.ingest(runtime.store, text.encode()))
        except BaseException as exc: errors.append(exc)
    def archive_source():
        archive_started.set()
        try: results.append(archive.archive_blob(runtime.store, source['sha256'], future))
        except BaseException as exc: errors.append(exc)
        finally: archive_done.set()
    monkeypatch.setattr(lifecycle, 'verify_or_create_blob', pause_image)
    image_thread = threading.Thread(target=ingest)
    archive_thread = threading.Thread(target=archive_source)
    image_thread.start()
    try:
        assert verified.wait(5)
        archive_thread.start()
        assert archive_started.wait(5) and not archive_done.wait(.1)
    finally:
        release.set()
        image_thread.join(5)
        if archive_thread.ident is not None: archive_thread.join(5)
    assert not errors and results == ['SOURCE_NO_LONGER_COLD'] and records
    assert vision.read_image(runtime.store, records[0]['ref']).size == (16, 16)


def test_final_image_forget_removes_both_plain_and_shared_text_archive(runtime):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    mid, row = old_fact(runtime, text)
    assert archive.archive_blob(runtime.store, row['hash'], future) == 'ARCHIVED'
    rec = vision.ingest(runtime.store, text.encode())
    runtime.memory.forget(mid)
    path = runtime.home / 'data/blobs' / row['hash']
    assert path.exists() and path.with_name(path.name + '.z').exists()
    vision.forget(runtime.store, rec)
    assert not path.exists() and not path.with_name(path.name + '.z').exists()


def test_concurrent_duplicate_image_ingest_has_one_registered_live_source(runtime, monkeypatch):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    rendezvous = threading.Barrier(2)
    original = vision.decode
    records, errors = [], []
    def decode_together(*args, **kwargs):
        image = original(*args, **kwargs)
        rendezvous.wait(timeout=5)
        return image
    def ingest():
        try: records.append(vision.ingest(runtime.store, text.encode()))
        except BaseException as exc: errors.append(exc)
    monkeypatch.setattr(vision, 'decode', decode_together)
    threads = [threading.Thread(target=ingest) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(5)
    assert all(not thread.is_alive() for thread in threads) and not errors and len(records) == 2
    assert records[0]['ref']['source_id'] == records[1]['ref']['source_id']
    key = records[0]['ref']['sha256']
    assert len(vision.load(runtime.store)['images']) == 1
    assert runtime.store.one('SELECT COUNT(*) AS n FROM sources WHERE hash=? AND kind=? AND deleted=0', (key, 'IMAGE'))['n'] == 1
    vision.forget(runtime.store, records[0])
    assert not runtime.store.one('SELECT id FROM sources WHERE hash=? AND deleted=0', (key,))
    assert not (runtime.home / 'data/blobs' / key).exists()


def test_ingest_after_forget_rechecks_registry_and_returns_live_source(runtime, monkeypatch):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    old = vision.ingest(runtime.store, text.encode())
    decoded, release = threading.Event(), threading.Event()
    original = vision.decode
    records, errors = [], []
    def pause_decode(*args, **kwargs):
        image = original(*args, **kwargs)
        decoded.set()
        if not release.wait(5): raise TimeoutError('test did not release image decode')
        return image
    def ingest():
        try: records.append(vision.ingest(runtime.store, text.encode()))
        except BaseException as exc: errors.append(exc)
    monkeypatch.setattr(vision, 'decode', pause_decode)
    thread = threading.Thread(target=ingest)
    thread.start()
    try:
        assert decoded.wait(5)
        vision.forget(runtime.store, old)
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive() and not errors and records
    assert records[0]['ref']['source_id'] != old['ref']['source_id']
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (records[0]['ref']['source_id'],))['deleted'] == 0
    assert vision.read_image(runtime.store, records[0]['ref']).size == (16, 16)


def test_stale_teacher_switch_cannot_restore_forgotten_image_or_caption(runtime, monkeypatch):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    rec = vision.ingest(runtime.store, text.encode())
    old_state = vision.load(runtime.store)
    old_state['images'][rec['ref']['source_id']]['captions'] = [
        {'text': 'synthetic caption', 'source_ref': vision.region_ref(rec['ref'], rec['regions'][0])}]
    vision.save(runtime.store, old_state)
    original_load = vision.load
    fired = []
    def load_then_forget(store):
        state = original_load(store)
        if not fired:
            fired.append(True)
            vision.forget(store, rec)
        return state
    monkeypatch.setattr(vision, 'load', load_then_forget)
    with pytest.raises(ValueError, match='[Ss]tale'):
        vision.teacher_switch(runtime.store, False)
    assert rec['ref']['source_id'] not in original_load(runtime.store)['images']
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (rec['ref']['source_id'],))['deleted'] == 1


def test_corrupt_existing_hash_never_creates_live_text_or_event_source(runtime):
    text = 'synthetic shared source ' * 100
    ref = runtime.store.source(text, 'USER')
    path = runtime.home / 'data/blobs' / ref['sha256']
    path.write_bytes(b'not the correct bytes')
    before = runtime.store.one('SELECT COUNT(*) AS n FROM sources WHERE hash=? AND deleted=0', (ref['sha256'],))['n']
    with pytest.raises((ValueError, OSError)):
        runtime.store.source(text, 'USER')
    with pytest.raises((ValueError, OSError)):
        runtime.store.event(runtime.session, text)
    assert runtime.store.one('SELECT COUNT(*) AS n FROM sources WHERE hash=? AND deleted=0', (ref['sha256'],))['n'] == before
    assert path.read_bytes() == b'not the correct bytes'


def test_corrupt_existing_hash_never_creates_live_image_source(runtime):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    ref = runtime.store.source(text, 'USER')
    path = runtime.home / 'data/blobs' / ref['sha256']
    path.write_bytes(b'not the correct bytes')
    with pytest.raises((ValueError, OSError)):
        vision.ingest(runtime.store, text.encode())
    assert not runtime.store.one('SELECT id FROM sources WHERE hash=? AND kind=?', (ref['sha256'], 'IMAGE'))
    assert path.read_bytes() == b'not the correct bytes'


def test_restore_refuses_deleted_source_and_keeps_archived_state(runtime):
    text = 'synthetic old decision ' * 100
    mid, row = old_fact(runtime, text)
    assert archive.archive_blob(runtime.store, row['hash'], future) == 'ARCHIVED'
    runtime.memory.forget(mid)
    with pytest.raises((ValueError, OSError)):
        archive.restore(runtime.store, row['hash'])
    path = runtime.home / 'data/blobs' / row['hash']
    assert not path.exists() and not path.with_name(path.name + '.z').exists()


def test_restore_and_forget_serialize_without_recreating_deleted_bytes(runtime, monkeypatch):
    text = 'synthetic old decision ' * 100
    mid, row = old_fact(runtime, text)
    key = row['hash']
    assert archive.archive_blob(runtime.store, key, future) == 'ARCHIVED'
    at_link, release, started, done = (threading.Event() for _ in range(4))
    original = lifecycle._link_anonymous
    errors, result = [], []
    def paused_link(fd, dir_fd, name):
        if name == key:
            at_link.set()
            if not release.wait(5): raise TimeoutError('test did not release restore')
        return original(fd, dir_fd, name)
    def restore():
        try: result.append(archive.restore(runtime.store, key))
        except BaseException as exc: errors.append(exc)
    def forget():
        started.set()
        try: runtime.memory.forget(mid)
        except BaseException as exc: errors.append(exc)
        finally: done.set()
    monkeypatch.setattr(lifecycle, '_link_anonymous', paused_link)
    restore_thread = threading.Thread(target=restore)
    forget_thread = threading.Thread(target=forget)
    restore_thread.start()
    try:
        assert at_link.wait(5)
        forget_thread.start()
        assert started.wait(5) and not done.wait(.1)
    finally:
        release.set()
        restore_thread.join(5)
        if forget_thread.ident is not None: forget_thread.join(5)
    assert not restore_thread.is_alive() and not forget_thread.is_alive()
    assert not errors and result == ['RESTORED'] and done.is_set()
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (row['id'],))['deleted'] == 1
    path = runtime.home / 'data/blobs' / key
    assert not path.exists() and not path.with_name(path.name + '.z').exists()


def test_restore_refuses_corrupt_plain_and_keeps_valid_archive(runtime):
    text = 'synthetic shared source ' * 100
    ref = runtime.store.source(text, 'USER')
    assert archive.archive_blob(runtime.store, ref['sha256'], future) == 'ARCHIVED'
    path = runtime.home / 'data/blobs' / ref['sha256']
    path.write_bytes(b'corrupted plain')
    archive_bytes = path.with_name(path.name + '.z').read_bytes()
    with pytest.raises((ValueError, OSError)):
        archive.restore(runtime.store, ref['sha256'])
    assert path.read_bytes() == b'corrupted plain'
    assert path.with_name(path.name + '.z').read_bytes() == archive_bytes


def test_cleanup_failure_after_forget_commit_is_visible_and_can_be_retried(runtime, monkeypatch):
    text = 'synthetic shared source ' * 100
    mid, row = old_fact(runtime, text)
    original = lifecycle.cleanup_unreferenced
    def fail_before_cleanup(store, source_id):
        raise OSError('injected cleanup failure')
    monkeypatch.setattr(lifecycle, 'cleanup_unreferenced', fail_before_cleanup)
    with pytest.raises(OSError, match='cleanup failure'):
        runtime.memory.forget(mid)
    path = runtime.home / 'data/blobs' / row['hash']
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (row['id'],))['deleted'] == 1
    assert path.exists()  # committed deletion does not imply completed file removal
    assert original(runtime.store, row['id']) == 'REMOVED'
    assert not path.exists()


def test_composed_pins_keep_large_archive_guard_and_streaming_reader(runtime):
    text = 'synthetic source with unicode Ω😀 ' * 100
    ref = runtime.store.source(text, 'USER')
    assert archive.archive_blob(runtime.store, ref['sha256'], future) == 'ARCHIVED'
    from v13 import archive_stream_range_candidate as stream
    assert stream.read_span(runtime.store, dict(ref, char_start=3, char_end=21)) == text[3:21]


def test_image_created_after_shared_text_was_archived_restores_plain_bytes(runtime):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    ref = runtime.store.source(text, 'USER')
    assert archive.archive_blob(runtime.store, ref['sha256'], future) == 'ARCHIVED'
    rec = vision.ingest(runtime.store, text.encode())
    assert rec['ref']['sha256'] == ref['sha256']
    assert vision.read_image(runtime.store, rec['ref']).size == (16, 16)
