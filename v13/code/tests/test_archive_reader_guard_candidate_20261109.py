"""Real store and disposable integration checks for the archive guard."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

import pytest

from v13 import archive
from v13 import archive_reader_guard_candidate as guard
from v13 import archive_stream_range_candidate as stream
from v13.runtime import Runtime


CODE = Path(__file__).resolve().parents[1]


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


def put_source(r, text='cold synthetic source ' * 120):
    ref = r.store.source(text, 'USER')
    return ref, r.home / 'data/blobs' / ref['sha256']


def large_source(r, size):
    """Build a deterministic large source without holding the text in RAM."""
    directory = r.home / 'data/blobs'
    temporary = directory / 'synthetic-preparation'
    block = b'A' * (1024 * 1024)
    sha = hashlib.sha256()
    with temporary.open('wb') as f:
        left = size
        while left:
            chunk = block[:min(len(block), left)]
            f.write(chunk)
            sha.update(chunk)
            left -= len(chunk)
    key = sha.hexdigest()
    temporary.rename(directory / key)
    sid = 'src_synthetic_' + key[:24]
    with r.store.tx() as conn:
        conn.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,0)', (sid, key, 'USER', size, size, time.time()))
    return {'source_id': sid, 'sha256': key, 'char_start': 0, 'char_end': size, 'modality': 'text'}


def test_cold_source_archive_is_readable_and_hash_verified(runtime):
    ref, path = put_source(runtime)
    assert guard.archive_blob(runtime.store, ref['sha256'], future) == 'ARCHIVED'
    assert not path.exists() and path.with_name(path.name + '.z').exists()
    assert runtime.store.read_source(ref) == 'cold synthetic source ' * 120


def test_exact_reader_boundary_remains_readable(runtime):
    ref = large_source(runtime, guard.READER_LIMIT)
    assert guard.archive_blob(runtime.store, ref['sha256'], future) == 'ARCHIVED'
    value = runtime.store.blob_bytes(ref['sha256'])
    assert len(value) == guard.READER_LIMIT and hashlib.sha256(value).hexdigest() == ref['sha256']


def test_above_reader_limit_is_preserved_and_baseline_fails(runtime):
    ref = large_source(runtime, guard.READER_LIMIT + 1)
    path = runtime.home / 'data/blobs' / ref['sha256']
    assert guard.archive_blob(runtime.store, ref['sha256'], future) == 'READER_LIMIT'
    assert path.stat().st_size == guard.READER_LIMIT + 1
    assert not path.with_name(path.name + '.z').exists()
    # Reproduce the original frozen implementation, using only synthetic data.
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    assert not path.exists() and path.with_name(path.name + '.z').exists()
    with pytest.raises(ValueError, match='zu groß'):
        runtime.store.blob_bytes(ref['sha256'])
    small_ref = dict(ref, char_start=guard.READER_LIMIT - 5, char_end=guard.READER_LIMIT + 1)
    assert stream.read_span(runtime.store, small_ref) == 'A' * 6


def test_deleted_source_between_compression_and_publication_is_not_recreated(runtime, monkeypatch):
    event = runtime.store.event(runtime.session, 'synthetic event')
    old_id = runtime.memory.feedback(event['event_id'], 'fact', 'old decision ' * 100)
    runtime.memory.feedback(event['event_id'], 'fact', 'new decision ' * 100)
    row = runtime.store.one('SELECT s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?', (old_id,))
    key = row['hash']
    assert key in archive.candidates(runtime.store, future)
    original_compress = guard.zlib.compress
    def forget_during_compression(raw, level):
        result = original_compress(raw, level)
        runtime.memory.forget(old_id)
        return result
    monkeypatch.setattr(guard.zlib, 'compress', forget_during_compression)
    assert guard.archive_blob(runtime.store, key, future) == 'SOURCE_DELETED'
    assert not (runtime.home / 'data/blobs' / key).exists()
    assert not (runtime.home / 'data/blobs' / (key + '.z')).exists()


def test_became_hot_during_compression_is_not_archived(runtime, monkeypatch):
    ref, path = put_source(runtime)
    original = guard.zlib.compress
    def duplicate_as_newer_source(raw, level):
        encoded = original(raw, level)
        # Created after the simulated cutoff: a newly shared source is hot.
        runtime.store.source('cold synthetic source ' * 120, 'UNKNOWN')
        return encoded
    monkeypatch.setattr(guard.zlib, 'compress', duplicate_as_newer_source)
    assert guard.archive_blob(runtime.store, ref['sha256'], future) == 'SOURCE_NO_LONGER_COLD'
    assert path.exists() and not path.with_name(path.name + '.z').exists()


def test_existing_or_partial_archive_is_never_overwritten(runtime):
    ref, path = put_source(runtime)
    archived = path.with_name(path.name + '.z')
    archived.write_bytes(b'partial archive from an interrupted process')
    assert guard.archive_blob(runtime.store, ref['sha256'], future) == 'EXISTING_ARCHIVE'
    assert path.exists() and archived.read_bytes() == b'partial archive from an interrupted process'
    assert runtime.store.read_source(ref) == 'cold synthetic source ' * 120


def test_write_failure_keeps_plain_and_preserves_partial_archive_for_review(runtime, monkeypatch):
    ref, path = put_source(runtime)
    def partial_then_fail(fd, value):
        os.write(fd, value[:3])
        raise OSError('injected write failure')
    monkeypatch.setattr(guard, '_write_all', partial_then_fail)
    with pytest.raises(OSError):
        guard.archive_blob(runtime.store, ref['sha256'], future)
    assert path.exists() and path.with_name(path.name + '.z').stat().st_size == 3
    assert runtime.store.read_source(ref) == 'cold synthetic source ' * 120


def test_replaced_archive_name_does_not_cause_plain_to_be_deleted(runtime, monkeypatch):
    ref, path = put_source(runtime)
    original = guard._write_all
    archived = path.with_name(path.name + '.z')
    def replace_archive(fd, value):
        original(fd, value)
        archived.unlink()
        archived.write_bytes(b'foreign archive')
    monkeypatch.setattr(guard, '_write_all', replace_archive)
    assert guard.archive_blob(runtime.store, ref['sha256'], future) == 'ARCHIVE_CHANGED'
    assert path.exists() and archived.read_bytes() == b'foreign archive'
    assert runtime.store.read_source(ref) == 'cold synthetic source ' * 120


def test_changed_archive_inode_contents_do_not_cause_plain_to_be_deleted(runtime, monkeypatch):
    ref, path = put_source(runtime)
    archived = path.with_name(path.name + '.z')
    original = guard.os.fsync
    calls = []
    def change_after_directory_sync(fd):
        original(fd)
        calls.append(fd)
        if len(calls) == 2:
            archived.write_bytes(b'foreign in-place content')
    monkeypatch.setattr(guard.os, 'fsync', change_after_directory_sync)
    assert guard.archive_blob(runtime.store, ref['sha256'], future) == 'ARCHIVE_CHANGED'
    assert path.exists() and archived.read_bytes() == b'foreign in-place content'
    assert runtime.store.read_source(ref) == 'cold synthetic source ' * 120


def test_concurrent_forget_waits_until_archive_publication(runtime, monkeypatch):
    event = runtime.store.event(runtime.session, 'synthetic event')
    old_id = runtime.memory.feedback(event['event_id'], 'fact', 'old decision ' * 100)
    runtime.memory.feedback(event['event_id'], 'fact', 'new decision ' * 100)
    row = runtime.store.one('SELECT s.hash,s.id FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?', (old_id,))
    key = row['hash']
    writing = threading.Event()
    release = threading.Event()
    forget_started = threading.Event()
    forget_done = threading.Event()
    outcomes, errors = [], []
    original = guard._write_all
    def paused_write(fd, value):
        writing.set()
        if not release.wait(5):
            raise TimeoutError('test did not release writer')
        original(fd, value)
    def do_archive():
        try:
            outcomes.append(guard.archive_blob(runtime.store, key, future))
        except BaseException as exc:
            errors.append(exc)
    def do_forget():
        forget_started.set()
        try:
            runtime.memory.forget(old_id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            forget_done.set()
    monkeypatch.setattr(guard, '_write_all', paused_write)
    archive_thread = threading.Thread(target=do_archive)
    forget_thread = threading.Thread(target=do_forget)
    archive_thread.start()
    try:
        assert writing.wait(5)
        forget_thread.start()
        assert forget_started.wait(5)
        assert not forget_done.wait(.1)
    finally:
        release.set()
        archive_thread.join(5)
        if forget_thread.ident is not None:
            forget_thread.join(5)
    assert not archive_thread.is_alive() and not forget_thread.is_alive()
    assert not errors and outcomes == ['ARCHIVED'] and forget_done.is_set()
    assert runtime.store.one('SELECT deleted FROM sources WHERE id=?', (row['id'],))['deleted'] == 1
    assert not (runtime.home / 'data/blobs' / key).exists()
    assert not (runtime.home / 'data/blobs' / (key + '.z')).exists()


def test_interrupt_after_plain_unlink_never_removes_the_only_verified_copy(runtime, monkeypatch):
    ref, path = put_source(runtime)
    original = guard.os.unlink
    def unlink_then_interrupt(name, *args, **kwargs):
        original(name, *args, **kwargs)
        if name == ref['sha256']:
            raise KeyboardInterrupt('injected after unlink')
    monkeypatch.setattr(guard.os, 'unlink', unlink_then_interrupt)
    with pytest.raises(KeyboardInterrupt):
        guard.archive_blob(runtime.store, ref['sha256'], future)
    assert not path.exists() and path.with_name(path.name + '.z').exists()
    assert runtime.store.read_source(ref) == 'cold synthetic source ' * 120


def test_failure_after_plain_unlink_retains_the_verified_archive(runtime, monkeypatch):
    ref, path = put_source(runtime)
    original = guard.os.fsync
    calls = []
    def fail_last(fd):
        calls.append(fd)
        if len(calls) == 3:
            raise OSError('injected directory fsync failure')
        return original(fd)
    monkeypatch.setattr(guard.os, 'fsync', fail_last)
    with pytest.raises(OSError):
        guard.archive_blob(runtime.store, ref['sha256'], future)
    assert not path.exists() and path.with_name(path.name + '.z').exists()
    assert runtime.store.read_source(ref) == 'cold synthetic source ' * 120


def test_symlink_source_and_changed_plain_are_not_archived(runtime):
    ref, path = put_source(runtime)
    replacement = path.with_name('other')
    path.rename(replacement)
    path.symlink_to(replacement)
    with pytest.raises(OSError):
        guard.archive_blob(runtime.store, ref['sha256'], future)
    assert replacement.exists() and not path.with_name(path.name + '.z').exists()


def test_materializer_checks_all_source_hashes(tmp_path):
    path = CODE / 'scripts/archive_reader_guard_integration_candidate.py'
    spec = importlib.util.spec_from_file_location('archive_guard_materializer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    patched = module.build_sources(CODE / 'v13')
    assert b'guarded_archive_blob' in patched['archive.py']
    for name in module.PINS:
        (tmp_path / name).write_bytes((CODE / 'v13' / name).read_bytes())
    (tmp_path / 'store.py').write_bytes(b'changed')
    with pytest.raises(ValueError, match='store.py'):
        module.build_sources(tmp_path)


def test_guard_rejects_changed_source_pins(runtime, monkeypatch):
    ref, path = put_source(runtime)
    monkeypatch.setitem(guard.SOURCE_PINS, 'store.py', {'0' * 64})
    with pytest.raises(ValueError, match='source changed'):
        guard.archive_blob(runtime.store, ref['sha256'], future)
    assert path.exists()


def test_materialized_real_archive_tests_and_disappearing_candidate(tmp_path):
    spec = importlib.util.spec_from_file_location('archive_guard_materializer', CODE / 'scripts/archive_reader_guard_integration_candidate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    for name, data in module.build_sources(CODE / 'v13').items():
        (tmp_path / 'v13' / name).write_bytes(data)
    shutil.copy(CODE / 'tests/test_archive.py', tmp_path / 'test_archive.py')
    (tmp_path / 'test_archive_disappearing.py').write_text('''\
from pathlib import Path
from v13 import archive
from v13.runtime import Runtime

def test_missing_blob_between_candidate_and_stat(tmp_path, monkeypatch):
    r = Runtime(tmp_path); r.sleep.cycle.set_policy('enabled', 'off')
    try:
        ref = r.store.source('source ' * 200, 'USER'); h = ref['sha256']
        (r.home / 'data/blobs' / h).unlink()
        monkeypatch.setattr(archive, 'candidates', lambda *a, **kw: [h])
        assert archive.run(r.store)['counts'] == {'IO_ERROR': 1}
    finally: r.close()
''')
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'test_archive.py', 'test_archive_disappearing.py'],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '5 passed' in result.stdout
