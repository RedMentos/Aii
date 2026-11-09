"""Document still-open failures of the frozen source lifecycle using synthetic data."""
import sqlite3

import pytest

from v13 import backup, vision
from v13.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    r = Runtime(tmp_path)
    r.sleep.cycle.set_policy('enabled', 'off')
    try:
        yield r
    finally:
        r.close()


def old_fact(r, text):
    event = r.store.event(r.session, 'synthetic event')
    mid = r.memory.feedback(event['event_id'], 'fact', text)
    row = r.store.one('SELECT s.id,s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?', (mid,))
    return mid, row


def test_legacy_rolled_back_event_leaves_orphaned_blob(runtime):
    text = 'synthetic transaction rollback ' * 100
    ref = None
    with pytest.raises(RuntimeError, match='force rollback'):
        with runtime.store.tx() as c:
            ref = runtime.store._event_in_tx(c, runtime.session, text, 'AUTHORITATIVE')['source_ref']
            raise RuntimeError('force rollback')
    assert not runtime.store.one('SELECT id FROM sources WHERE id=?', (ref['source_id'],))
    assert (runtime.home / 'data/blobs' / ref['sha256']).read_text() == text


def test_legacy_vision_ingest_can_return_revoked_reference(runtime, monkeypatch):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    old = vision.ingest(runtime.store, text.encode())
    original = vision.load
    fired = []
    def loaded_before_forget(store):
        state = original(store)
        if not fired:
            fired.append(True)
            vision.forget(store, old)
        return state
    monkeypatch.setattr(vision, 'load', loaded_before_forget)
    returned = vision.ingest(runtime.store, text.encode())
    assert returned['ref']['source_id'] == old['ref']['source_id']
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (returned['ref']['source_id'],))['deleted'] == 1
    with pytest.raises(ValueError):
        vision.read_image(runtime.store, returned['ref'])


def test_legacy_revoked_source_ref_can_still_read_shared_blob(runtime, monkeypatch):
    text = 'synthetic shared fact ' * 100
    mid, row = old_fact(runtime, text)
    other = runtime.store.source(text, 'USER')
    ref = {'source_id': row['id'], 'sha256': row['hash'], 'char_start': 0,
           'char_end': len(text), 'modality': 'text'}
    original = runtime.store.one
    fired = []
    def lookup_then_forget(sql, args=()):
        found = original(sql, args)
        if sql == 'SELECT * FROM sources WHERE id=?' and args == (row['id'],) and not fired:
            fired.append(True)
            runtime.memory.forget(mid)
        return found
    monkeypatch.setattr(runtime.store, 'one', lookup_then_forget)
    assert runtime.store.read_source(ref) == text
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (row['id'],))['deleted'] == 1
    assert runtime.store.read_source(other) == text


def test_legacy_revoked_image_ref_can_still_read_shared_blob(runtime, monkeypatch):
    text = 'P3\n16 16\n255\n' + '0 0 0\n' * (16 * 16)
    rec = vision.ingest(runtime.store, text.encode())
    other = runtime.store.source(text, 'USER')
    sid = rec['ref']['source_id']
    original = runtime.store.one
    fired = []
    def lookup_then_forget(sql, args=()):
        found = original(sql, args)
        if sql == 'SELECT * FROM sources WHERE id=?' and args == (sid,) and not fired:
            fired.append(True)
            vision.forget(runtime.store, rec)
        return found
    monkeypatch.setattr(runtime.store, 'one', lookup_then_forget)
    assert vision.read_image(runtime.store, rec['ref']).size == (16, 16)
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (sid,))['deleted'] == 1
    assert runtime.store.read_source(other) == text


def test_legacy_backup_can_omit_blob_of_live_snapshot_source(runtime, monkeypatch, tmp_path):
    text = 'synthetic shared fact ' * 100
    mid, row = old_fact(runtime, text)
    original = backup.shutil.copytree
    fired = []
    def delete_before_blob_copy(src, dst, *args, **kwargs):
        if src == runtime.home / 'data/blobs' and not fired:
            fired.append(True)
            runtime.memory.forget(mid)
        return original(src, dst, *args, **kwargs)
    monkeypatch.setattr(backup.shutil, 'copytree', delete_before_blob_copy)
    out = backup.backup(runtime.store, tmp_path / 'synthetic-backup.tar.gz')
    stage = tmp_path / 'unpacked'
    stage.mkdir()
    backup.unpack_verified(out, stage, 1024 * 1024 * 128)
    conn = sqlite3.connect(stage / 'data/db/brain.sqlite3')
    try:
        assert conn.execute('SELECT deleted FROM sources WHERE id=?', (row['id'],)).fetchone()[0] == 0
    finally:
        conn.close()
    assert not (stage / 'data/blobs' / row['hash']).exists()
    assert not (stage / 'data/blobs' / (row['hash'] + '.z')).exists()
