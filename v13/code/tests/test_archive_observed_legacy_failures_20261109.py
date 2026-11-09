"""Document reproduced frozen-source failures; these are not passing gates."""
import time
import zlib

import pytest

from v13 import archive
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


def future():
    return time.time() + (archive.ARCHIVE_DAYS + 1) * 86400


def test_legacy_restore_accepts_corrupt_plain_even_when_valid_archive_exists(runtime):
    text = 'synthetic source ' * 100
    ref = runtime.store.source(text, 'USER')
    key = ref['sha256']
    assert archive.archive_blob(runtime.store, key) == 'ARCHIVED'
    path = runtime.home / 'data/blobs' / key
    path.write_text('corrupted plain')
    assert archive.restore(runtime.store, key) == 'ALREADY_PLAIN'
    with pytest.raises(ValueError, match='Hash'):
        runtime.store.read_source(ref)
    assert zlib.decompress(path.with_name(key + '.z').read_bytes()).decode() == text


def test_legacy_candidate_scan_can_starve_cold_source(runtime):
    for i in range(4):
        ref = runtime.store.source(f'not archivable {i} ' + 'x' * 600, 'MEMORY_KEY')
        with runtime.store.tx() as c:
            c.execute('UPDATE sources SET created=? WHERE id=?', (100 + i, ref['source_id']))
    target = runtime.store.source('eligible user source ' + 'y' * 600, 'USER')
    with runtime.store.tx() as c:
        c.execute('UPDATE sources SET created=? WHERE id=?', (110, target['source_id']))
    assert archive.candidates(runtime.store, future, limit=1) == []
    assert target['sha256'] in archive.candidates(runtime.store, future, limit=2)


def test_legacy_forget_can_delete_a_new_live_source_with_same_hash(runtime, monkeypatch):
    text = 'synthetic user fact ' * 100
    event = runtime.store.event(runtime.session, 'synthetic event')
    mid = runtime.memory.feedback(event['event_id'], 'fact', text)
    initial = runtime.store.one('SELECT source_id FROM memories WHERE id=?', (mid,))['source_id']
    new = []
    original = runtime.store.one
    def insert_after_last_live_source_check(sql, args=()):
        result = original(sql, args)
        if sql == 'SELECT id FROM sources WHERE hash=? AND deleted=0' and result is None and not new:
            new.append(runtime.store.source(text, 'USER'))
        return result
    monkeypatch.setattr(runtime.store, 'one', insert_after_last_live_source_check)
    runtime.memory.forget(mid)
    assert new and runtime.store.one('SELECT deleted FROM sources WHERE id=?', (initial,))['deleted'] == 1
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (new[0]['source_id'],))['deleted'] == 0
    with pytest.raises(FileNotFoundError):
        runtime.store.read_source(new[0])


def test_legacy_archive_can_recreate_deleted_source_after_forget(runtime, monkeypatch):
    old = 'synthetic old decision ' * 100
    event = runtime.store.event(runtime.session, 'synthetic event')
    mid = runtime.memory.feedback(event['event_id'], 'fact', old)
    runtime.memory.feedback(event['event_id'], 'fact', 'synthetic new decision ' * 100)
    row = runtime.store.one('SELECT s.id,s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?', (mid,))
    assert row['hash'] in archive.candidates(runtime.store, future)
    original = archive.atomic_write
    def forget_then_write(path, data):
        runtime.memory.forget(mid)
        return original(path, data)
    monkeypatch.setattr(archive, 'atomic_write', forget_then_write)
    with pytest.raises(FileNotFoundError):
        archive.archive_blob(runtime.store, row['hash'])
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (row['id'],))['deleted'] == 1
    path = runtime.home / 'data/blobs' / (row['hash'] + '.z')
    assert zlib.decompress(path.read_bytes()).decode() == old


def test_legacy_restore_can_recreate_deleted_plain_source(runtime, monkeypatch):
    old = 'synthetic old decision ' * 100
    event = runtime.store.event(runtime.session, 'synthetic event')
    mid = runtime.memory.feedback(event['event_id'], 'fact', old)
    runtime.memory.feedback(event['event_id'], 'fact', 'synthetic new decision ' * 100)
    row = runtime.store.one('SELECT s.id,s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?', (mid,))
    assert archive.archive_blob(runtime.store, row['hash']) == 'ARCHIVED'
    original = archive.atomic_write
    def forget_then_restore(path, data):
        runtime.memory.forget(mid)
        return original(path, data)
    monkeypatch.setattr(archive, 'atomic_write', forget_then_restore)
    with pytest.raises(FileNotFoundError):
        archive.restore(runtime.store, row['hash'])
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (row['id'],))['deleted'] == 1
    assert (runtime.home / 'data/blobs' / row['hash']).read_text() == old


def test_legacy_vision_forget_leaves_shared_text_archive(runtime):
    # ASCII PPM is valid both UTF-8 text and an image with the same byte hash.
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    event = runtime.store.event(runtime.session, 'synthetic event')
    mid = runtime.memory.feedback(event['event_id'], 'fact', text)
    runtime.memory.feedback(event['event_id'], 'fact', 'different synthetic decision ' * 30)
    row = runtime.store.one('SELECT s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?', (mid,))
    assert archive.archive_blob(runtime.store, row['hash']) == 'ARCHIVED'
    rec = vision.ingest(runtime.store, text.encode())
    assert rec['ref']['sha256'] == row['hash']
    runtime.memory.forget(mid)
    vision.forget(runtime.store, rec)
    assert not runtime.store.one('SELECT id FROM sources WHERE hash=? AND deleted=0', (row['hash'],))
    path = runtime.home / 'data/blobs' / row['hash']
    assert not path.exists()
    assert zlib.decompress(path.with_name(path.name + '.z').read_bytes()).decode() == text
