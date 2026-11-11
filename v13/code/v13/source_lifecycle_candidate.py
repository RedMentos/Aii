"""Review-only helpers for source/forget serialization on a trusted blob directory.

Callers must use the same Store SQLite write lock for source creation,
archive publication, restore, and cleanup. This module is not wired into the
frozen runtime. Filesystem and SQLite do not form one crash-atomic transaction.
"""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import zlib

from .store import Store
from . import vision
from .common import digest, dumps, now, uid

CHUNK = 64 * 1024
READER_LIMIT = 64 * 1024 * 1024
AT_EMPTY_PATH = 0x1000


def _key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('invalid source hash')
    return value


def _store(value):
    if type(value) is not Store:
        raise ValueError('reviewed Store instance required')


def _directory(path):
    if not all(hasattr(os, name) for name in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')):
        raise OSError('safe blob directory operations unavailable')
    return os.open(Path(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        size = os.write(fd, view)
        if size <= 0:
            raise OSError('short blob write')
        view = view[size:]


def _tmpfile(dir_fd):
    if not hasattr(os, 'O_TMPFILE'):
        raise OSError('anonymous temporary files unavailable')
    # No fallback to a visible temporary name: a crash must not leave another
    # untracked copy that a later forget would miss.
    return os.open('.', os.O_RDWR | os.O_TMPFILE, 0o600, dir_fd=dir_fd)


def _link_anonymous(fd, dir_fd, name):
    """Atomically link an anonymous inode, refusing to overwrite an existing name."""
    try:
        linkat = ctypes.CDLL(None, use_errno=True).linkat
    except (AttributeError, OSError) as exc:
        raise OSError('linkat unavailable') from exc
    linkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    linkat.restype = ctypes.c_int
    if linkat(fd, b'', dir_fd, os.fsencode(name), AT_EMPTY_PATH) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), name)


def _hash_fd(fd, limit):
    os.lseek(fd, 0, os.SEEK_SET)
    hasher = hashlib.sha256()
    total = 0
    while True:
        data = os.read(fd, min(CHUNK, limit - total + 1))
        if not data:
            return hasher.hexdigest(), total
        total += len(data)
        if total > limit:
            raise ValueError('blob exceeds declared size')
        hasher.update(data)


def _verify_open_named(dir_fd, name, fd, expected_hash, expected_size):
    first = os.fstat(fd)
    if not stat.S_ISREG(first.st_mode) or first.st_size != expected_size:
        raise ValueError('blob is not a regular file of the expected size')
    actual_hash, count = _hash_fd(fd, expected_size)
    last = os.fstat(fd)
    named = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    if (count != expected_size or actual_hash != expected_hash
            or _identity(first) != _identity(last) or _identity(last) != _identity(named)):
        raise ValueError('blob content or identity mismatch')


def _open_existing(dir_fd, name):
    return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)


def _verify_linked(dir_fd, name, fd, expected_hash, expected_size):
    """Verify the published name and descriptor both still identify the bytes."""
    _verify_open_named(dir_fd, name, fd, expected_hash, expected_size)
    return _identity(os.fstat(fd))


def _check_linked_identity(dir_fd, name, fd, verified):
    info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode) or _identity(info) != verified
            or _identity(os.fstat(fd)) != verified):
        raise ValueError('published blob changed')


def verify_or_create_blob(path, data, expected_hash):
    """Verify existing exact bytes, or create without replacing an existing name.

    Caller holds the Store write transaction covering both publication and its
    source-row insert. A later failed/aborted DB commit can leave an orphaned
    final blob, as filesystem publication and SQLite commit are not atomic.
    """
    expected_hash = _key(expected_hash)
    if type(data) is not bytes or hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError('data does not match expected hash')
    path = Path(path)
    if path.name != expected_hash:
        raise ValueError('blob path does not match expected hash')
    dir_fd = _directory(path.parent)
    tmp_fd = None
    try:
        try:
            existing_fd = _open_existing(dir_fd, expected_hash)
        except FileNotFoundError:
            existing_fd = None
        if existing_fd is not None:
            try:
                _verify_open_named(dir_fd, expected_hash, existing_fd, expected_hash, len(data))
            finally:
                os.close(existing_fd)
            return 'EXISTING'
        tmp_fd = _tmpfile(dir_fd)
        _write_all(tmp_fd, data)
        os.fsync(tmp_fd)
        if os.fstat(tmp_fd).st_size != len(data) or _hash_fd(tmp_fd, len(data)) != (expected_hash, len(data)):
            raise ValueError('prepared blob failed verification')
        try:
            _link_anonymous(tmp_fd, dir_fd, expected_hash)
        except FileExistsError:
            # A non-cooperating writer won the name. Never replace it.
            existing_fd = _open_existing(dir_fd, expected_hash)
            try:
                _verify_open_named(dir_fd, expected_hash, existing_fd, expected_hash, len(data))
            finally:
                os.close(existing_fd)
            return 'EXISTING'
        verified = _verify_linked(dir_fd, expected_hash, tmp_fd, expected_hash, len(data))
        os.fsync(dir_fd)
        _check_linked_identity(dir_fd, expected_hash, tmp_fd, verified)
        return 'CREATED'
    finally:
        if tmp_fd is not None:
            os.close(tmp_fd)
        os.close(dir_fd)


def cleanup_unreferenced(store, source_id):
    """Remove both forms only after committed deletion and a locked live check.

    Returns REMOVED if both names are absent, PRESERVED_LIVE if any other row
    may still reference the hash. On I/O/interrupt failure, partial deletion is
    possible; a caller may retry. No whole-device/backups deletion is implied.
    """
    _store(store)
    if not isinstance(source_id, str) or not source_id:
        raise ValueError('invalid source id')
    with store.tx() as conn:
        source = conn.execute('SELECT hash,deleted FROM sources WHERE id=?', (source_id,)).fetchone()
        if source is None or source['deleted'] != 1:
            raise ValueError('source is not committed deleted')
        key = _key(source['hash'])
        # Unknown deleted values are conservatively treated as references.
        if conn.execute('SELECT 1 FROM sources WHERE hash=? AND deleted<>1 LIMIT 1', (key,)).fetchone():
            return 'PRESERVED_LIVE'
        dir_fd = _directory(store.home / 'data/blobs')
        try:
            names = (key, key + '.z')
            for name in names:
                try:
                    info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('unsafe non-regular blob entry')
            for name in names:
                try:
                    os.unlink(name, dir_fd=dir_fd)
                except FileNotFoundError:
                    pass
            os.fsync(dir_fd)
            return 'REMOVED'
        finally:
            os.close(dir_fd)


def _decode_archive_to_fd(archive_fd, out_fd, expected_hash, expected_size):
    initial = os.fstat(archive_fd)
    if not stat.S_ISREG(initial.st_mode) or initial.st_size > READER_LIMIT:
        raise ValueError('archive is not a bounded regular file')
    decoder = zlib.decompressobj()
    hasher = hashlib.sha256()
    n_input = n_output = 0
    while True:
        data = os.read(archive_fd, min(CHUNK, READER_LIMIT - n_input + 1))
        if not data:
            break
        n_input += len(data)
        if n_input > READER_LIMIT:
            raise ValueError('archive input limit exceeded')
        if decoder.eof:
            raise ValueError('trailing archive data')
        while data:
            old = len(data)
            value = decoder.decompress(data, min(CHUNK, expected_size - n_output + 1))
            data = decoder.unconsumed_tail
            n_output += len(value)
            if n_output > expected_size:
                raise ValueError('archive output exceeds source size')
            hasher.update(value)
            _write_all(out_fd, value)
            if decoder.eof:
                if decoder.unused_data or data:
                    raise ValueError('trailing archive data')
                break
            if not value and len(data) >= old:
                raise ValueError('archive decoder made no progress')
    if not decoder.eof or n_output != expected_size or hasher.hexdigest() != expected_hash:
        raise ValueError('archive corrupt or source hash mismatch')
    if _identity(os.fstat(archive_fd)) != _identity(initial):
        raise ValueError('archive changed while reading')
    return initial


def restore(store, key):
    """Restore an active, verified <=64 MiB archive under the source write lock.

    An intact plain blob returns ALREADY_PLAIN. A conflicting/corrupt plain
    blob or unsupported anonymous staging raises without replacing it. A valid
    new plain blob is linked without overwrite before the old archive is
    removed. Blocks cooperating DB writers for the full scan and is not a
    background-ready, cancellable, or device-measured path.
    """
    _store(store)
    key = _key(key)
    status = None
    with store.tx() as conn:
        rows = conn.execute('SELECT bytes,deleted FROM sources WHERE hash=?', (key,)).fetchall()
        if not rows or any(r['deleted'] not in (0, 1) for r in rows):
            raise ValueError('invalid source lifecycle state')
        live = [r for r in rows if r['deleted'] == 0]
        if not live:
            raise ValueError('no live source to restore')
        sizes = {r['bytes'] for r in live}
        if len(sizes) != 1 or type(next(iter(sizes))) is not int:
            raise ValueError('source size metadata mismatch')
        size = next(iter(sizes))
        if size < 0 or size > READER_LIMIT:
            raise ValueError('source exceeds reviewed reader limit')
        dir_fd = _directory(store.home / 'data/blobs')
        archive_fd = tmp_fd = None
        try:
            try:
                plain_fd = _open_existing(dir_fd, key)
            except FileNotFoundError:
                plain_fd = None
            if plain_fd is not None:
                try:
                    _verify_open_named(dir_fd, key, plain_fd, key, size)
                finally:
                    os.close(plain_fd)
                return 'ALREADY_PLAIN'
            try:
                archive_fd = _open_existing(dir_fd, key + '.z')
            except FileNotFoundError as exc:
                raise ValueError('no archive for live source') from exc
            tmp_fd = _tmpfile(dir_fd)
            try:
                archive_info = _decode_archive_to_fd(archive_fd, tmp_fd, key, size)
            except zlib.error as exc:
                raise ValueError('archive corrupt') from exc
            os.fsync(tmp_fd)
            if os.fstat(tmp_fd).st_size != size or _hash_fd(tmp_fd, size) != (key, size):
                raise ValueError('prepared restored blob failed verification')
            named_archive = os.stat(key + '.z', dir_fd=dir_fd, follow_symlinks=False)
            if (_identity(named_archive) != _identity(archive_info)
                    or _identity(os.fstat(archive_fd)) != _identity(archive_info)):
                raise ValueError('archive changed before publication')
            _link_anonymous(tmp_fd, dir_fd, key)
            verified_plain = _verify_linked(dir_fd, key, tmp_fd, key, size)
            # Archive remains intact until the new plain directory entry is durable.
            os.fsync(dir_fd)
            _check_linked_identity(dir_fd, key, tmp_fd, verified_plain)
            named_archive = os.stat(key + '.z', dir_fd=dir_fd, follow_symlinks=False)
            if (_identity(named_archive) != _identity(archive_info)
                    or _identity(os.fstat(archive_fd)) != _identity(archive_info)):
                raise ValueError('archive changed after publication')
            os.unlink(key + '.z', dir_fd=dir_fd)
            os.fsync(dir_fd)
            status = 'RESTORED'
        finally:
            if tmp_fd is not None:
                os.close(tmp_fd)
            if archive_fd is not None:
                os.close(archive_fd)
            os.close(dir_fd)
    if status == 'RESTORED':
        store.log('archive_restore', None, {'hash': key})
    return status


def _read_vision_state(conn):
    row = conn.execute('SELECT payload,version FROM states WHERE key=?', (vision.KEY,)).fetchone()
    if row is None:
        return {'revision': vision.REVISION, 'images': {}, 'projector': None, 'last': None}, 0
    if type(row['version']) is not int or row['version'] < 1:
        raise ValueError('invalid vision state version')
    try:
        state = json.loads(row['payload'])
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid vision state') from exc
    if not state:
        state = {'revision': vision.REVISION, 'images': {}, 'projector': None, 'last': None}
    if not isinstance(state, dict) or not isinstance(state.get('images'), dict):
        raise ValueError('invalid vision image registry')
    return state, row['version']


def _write_vision_state(conn, state, version):
    conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                 (vision.KEY, version + 1, dumps(state)))


def _vision_ref(record, source_id):
    if not isinstance(record, dict) or not isinstance(record.get('ref'), dict):
        raise ValueError('invalid vision image record')
    ref = record['ref']
    if (not isinstance(source_id, str) or not source_id or ref.get('source_id') != source_id
            or ref.get('modality') != 'image'):
        raise ValueError('invalid vision source reference')
    _key(ref.get('sha256'))
    return ref


class _VersionedVisionState(dict):
    """A normal visible mapping carrying its read version outside its keys."""
    __slots__ = ('_vision_store', '_vision_version')

    def __init__(self, value, store, version):
        super().__init__(value)
        self._vision_store = store
        self._vision_version = version


def load_vision_state(store):
    """Read the original visible mapping with a private Store/version binding."""
    _store(store)
    state, version = store.state(vision.KEY, None)
    if type(version) is not int or version < 0:
        raise ValueError('invalid vision state version')
    if state is None or state == {}:
        state = {'revision': vision.REVISION, 'images': {}, 'projector': None, 'last': None}
    if not isinstance(state, dict) or not isinstance(state.get('images'), dict):
        raise ValueError('invalid vision image registry')
    return _VersionedVisionState(state, store, version)


def _validate_vision_write(conn, state):
    """Reject source/caption references to forgotten or mismatched images."""
    images = state.get('images')
    if not isinstance(images, dict):
        raise ValueError('invalid vision image registry')
    for sid, record in images.items():
        ref = _vision_ref(record, sid)
        source = conn.execute('SELECT hash,kind,deleted FROM sources WHERE id=?', (sid,)).fetchone()
        if source is None or source['deleted'] != 0 or source['kind'] != 'IMAGE' or source['hash'] != ref['sha256']:
            raise ValueError('vision registry references a non-live image source')
        captions = record.get('captions')
        if not isinstance(captions, list):
            raise ValueError('invalid image captions')
        for caption in captions:
            caption_ref = caption.get('source_ref') if isinstance(caption, dict) else None
            if (not isinstance(caption_ref, dict) or caption_ref.get('source_id') != sid
                    or caption_ref.get('sha256') != ref['sha256'] or caption_ref.get('modality') != 'image'):
                raise ValueError('image caption references a non-live source')
    projector = state.get('projector')
    if projector:
        if not isinstance(projector, dict) or not isinstance(projector.get('captions'), dict):
            raise ValueError('invalid vision projector captions')
        for key in projector['captions']:
            if not isinstance(key, str) or ':' not in key or key.split(':', 1)[0] not in images:
                raise ValueError('projector caption references a non-live image source')


def save_vision_state(store, state):
    """Save only the exact read version; reject stale or unbound mappings.

    Like the original vision.save, return None. A successful save advances
    this mapping's private version, so sequential reuse stays supported.
    """
    _store(store)
    if (type(state) is not _VersionedVisionState or state._vision_store is not store
            or type(state._vision_version) is not int or state._vision_version < 0):
        raise ValueError('versioned vision state from this Store required')
    with store.tx() as conn:
        row = conn.execute('SELECT version FROM states WHERE key=?', (vision.KEY,)).fetchone()
        current = row['version'] if row else 0
        if type(current) is not int or current < 0 or current != state._vision_version:
            raise ValueError('Stale state write')
        _validate_vision_write(conn, state)
        _write_vision_state(conn, state, current)
    state._vision_version = current + 1


def vision_ingest(store, data, cfg=vision.DEFAULTS, label=None):
    """Ingest/deduplicate an image and its registry row under one DB write lock.

    Other vision functions that independently read then save registry state
    must also be coordinated before claiming whole-module race freedom.
    """
    _store(store)
    if type(data) is not bytes:
        raise ValueError('image data must be bytes')
    image = vision.decode(data, cfg)
    width, height = image.size
    key = digest(data)
    with store.tx() as conn:
        state, version = _read_vision_state(conn)
        matches = []
        for sid, record in state['images'].items():
            ref = _vision_ref(record, sid)
            if ref['sha256'] == key:
                matches.append((sid, record))
        if len(matches) > 1:
            raise ValueError('ambiguous existing image records')
        sources = conn.execute("SELECT id,deleted FROM sources WHERE hash=? AND kind='IMAGE' "
                               "AND deleted<>1 LIMIT 3", (key,)).fetchall()
        if any(row['deleted'] != 0 for row in sources):
            raise ValueError('invalid image source lifecycle state')
        live_ids = [row['id'] for row in sources]
        if ((matches and (len(live_ids) != 1 or live_ids[0] != matches[0][0]))
                or (not matches and live_ids)):
            raise ValueError('image registry and live sources disagree')
        path = store.home / 'data/blobs' / key
        if matches:
            sid, record = matches[0]
            source = conn.execute('SELECT hash,kind,bytes,chars,deleted FROM sources WHERE id=?', (sid,)).fetchone()
            if (source is None or source['hash'] != key or source['kind'] != 'IMAGE'
                    or source['deleted'] != 0 or source['bytes'] != len(data) or source['chars'] != 0):
                raise ValueError('existing image record is not a live matching source')
            verify_or_create_blob(path, data, key)
            return record
        if len(state['images']) >= cfg['max_images']:
            raise ValueError('Zu viele Bilder im Lab; erst :image forget')
        sid = uid('src')
        verify_or_create_blob(path, data, key)
        conn.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,0)', (sid, key, 'IMAGE', len(data), 0, now()))
        ref = {'source_id': sid, 'sha256': key, 'char_start': 0, 'char_end': 0, 'modality': 'image'}
        record = {'ref': ref, 'size': [width, height], 'label': (label or '')[:80],
                  'regions': vision.boxes(width, height, cfg['grid']), 'captions': [], 'created': now()}
        state['images'][sid] = record
        _write_vision_state(conn, state, version)
        return record


def vision_forget(store, rec):
    """Atomically unregister an image, then safely retry blob cleanup if needed."""
    _store(store)
    if not isinstance(rec, dict) or not isinstance(rec.get('ref'), dict):
        raise ValueError('invalid vision image record')
    sid = rec['ref'].get('source_id')
    ref = _vision_ref(rec, sid)
    with store.tx() as conn:
        state, version = _read_vision_state(conn)
        source = conn.execute('SELECT hash,kind,deleted FROM sources WHERE id=?', (sid,)).fetchone()
        if (source is None or source['hash'] != ref['sha256'] or source['kind'] != 'IMAGE'
                or source['deleted'] not in (0, 1)):
            raise ValueError('image source does not match record')
        entry = state['images'].get(sid)
        if entry is None and source['deleted'] == 0:
            raise ValueError('active image source missing from registry')
        if entry is not None and _vision_ref(entry, sid)['sha256'] != ref['sha256']:
            raise ValueError('image registry does not match source')
        if entry is not None:
            del state['images'][sid]
        projector = state.get('projector')
        if projector:
            if not isinstance(projector, dict) or not isinstance(projector.get('captions'), dict):
                raise ValueError('invalid vision projector captions')
            if any(not isinstance(k, str) for k in projector['captions']):
                raise ValueError('invalid vision projector caption key')
            projector['captions'] = {k: v for k, v in projector['captions'].items()
                                     if k.split(':')[0] != sid}
        conn.execute('UPDATE sources SET deleted=1 WHERE id=?', (sid,))
        _write_vision_state(conn, state, version)
    cleanup_unreferenced(store, sid)
    return {'forgotten': sid}
