"""Explicit, local RECORD imports on the existing G13 worker; never a trainer.

Grants cover specific staged preview files, not a repository or future rows.
Quotas count charged payload/receipt bytes, including failed attempts; existing
previews, SQLite/WAL overhead and other subsystems are outside this quota.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import threading
import time

from . import dataset_probe_candidate as probe
from .agi.base import StateBox
from .common import dumps
from .source_read_budget_candidate import Budget, ReadBudgetExceeded
from .store import Store

ACTION = 'import_dataset_idle'
HUMAN = 'EXPLICIT_HUMAN'
KIND = 'EXTERNAL_DATASET'
KEY = 'DATASET_IDLE_RECORD_V1'
REVISION = 'dataset-idle-record-v1'
SCOPE = 'LOCAL_DATASET_PREVIEW_RECORD_ONLY'
LIMITS = {'interval_s': (30, 86400), 'min_idle_s': (0, 86400),
          'daily_rows': (1, 32), 'daily_bytes': (1, 1024 * 1024),
          'row_bytes': (1, 16384), 'total_rows': (1, 256),
          'total_bytes': (1, 8 * 1024 * 1024), 'deadline_ms': (50, 2000)}
DEFAULTS = dict(interval_s=300, min_idle_s=300, daily_rows=8,
                daily_bytes=128 * 1024, row_bytes=8192, total_rows=64,
                total_bytes=1024 * 1024, deadline_ms=500)
QUOTAS = ('daily_rows', 'daily_bytes', 'row_bytes', 'total_rows', 'total_bytes')
MAX_ADMISSIONS = 16
MAX_OFFSETS = 16
MAX_METADATA = 256 * 1024
RECEIPT_BYTES = 2048
HEX = re.compile(r'[0-9a-f]{64}\Z')
FIELD = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,63}\Z')


class ImportRefused(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _hash(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def _empty():
    return dict(enabled=False, config=dict(DEFAULTS), admissions={}, order=[],
                day=None, last_attempt=None, day_rows=0, day_bytes=0,
                charged_rows=0, charged_bytes=0, imported_rows=0, imported_bytes=0,
                reservation=0, last_event=None, last_result=None, history=[])


def _box(store):
    return StateBox(store, KEY, REVISION, _empty)


def box(runtime):
    return _box(runtime.store)


def _validate(state):
    if type(state) is not dict or set(state) != set(_empty()) | {'revision'} or state['revision'] != REVISION:
        raise ImportRefused('invalid import policy fields')
    cfg = state['config']
    if type(cfg) is not dict or set(cfg) != set(LIMITS):
        raise ImportRefused('invalid import configuration')
    if any(not _integer(cfg[k], *bounds) for k, bounds in LIMITS.items()):
        raise ImportRefused('invalid import budget')
    if (type(state['enabled']) is not bool or type(state['admissions']) is not dict
            or type(state['order']) is not list or len(state['order']) > MAX_ADMISSIONS
            or any(not _hash(key) for key in state['order'])
            or len(set(state['order'])) != len(state['order'])
            or set(state['order']) != set(state['admissions'])):
        raise ImportRefused('invalid import admissions')
    if state['day'] is not None:
        if type(state['day']) is not str:
            raise ImportRefused('invalid import day')
        datetime.strptime(state['day'], '%Y-%m-%d')
    last = state['last_attempt']
    if last is not None and (type(last) not in (int, float) or not math.isfinite(last) or last < 0):
        raise ImportRefused('invalid import timestamp')
    for key, cap in (('day_rows', 32), ('day_bytes', LIMITS['daily_bytes'][1]),
                     ('charged_rows', 256), ('charged_bytes', LIMITS['total_bytes'][1]),
                     ('imported_rows', 256), ('imported_bytes', LIMITS['total_bytes'][1]),
                     ('reservation', 10**9)):
        if not _integer(state[key], 0, cap):
            raise ImportRefused('invalid import accounting')
    if (state['last_event'] is not None and (type(state['last_event']) is not str or not 1 <= len(state['last_event']) <= 160)
            or state['last_result'] is not None and type(state['last_result']) is not dict
            or type(state['history']) is not list or len(state['history']) > 8
            or any(type(row) is not dict for row in state['history'])):
        raise ImportRefused('invalid import result metadata')
    charged_rows = charged_bytes = imported_rows = imported_bytes = 0
    for grant in state['admissions'].values():
        if type(grant) is not dict or set(grant) != {'dataset_id', 'stage_dir', 'directory', 'field', 'catalog_sha256',
                'entry', 'entry_sha256', 'quotas', 'rows', 'cursor', 'active', 'revoked_at', 'charged_rows', 'charged_bytes'}:
            raise ImportRefused('invalid record grant')
        quotas = grant['quotas']
        if (type(quotas) is not dict or set(quotas) != set(QUOTAS)
                or any(not _integer(quotas[k], *LIMITS[k]) for k in QUOTAS)
                or type(grant['dataset_id']) is not str or not re.fullmatch(r'[a-z0-9_]{1,80}', grant['dataset_id'])
                or type(grant['stage_dir']) is not str or not Path(grant['stage_dir']).is_absolute()
                or not 1 <= len(grant['stage_dir']) <= 1024 or '\0' in grant['stage_dir']
                or type(grant['directory']) is not list or len(grant['directory']) != 2
                or any(not _integer(x, 0, 2**64-1) for x in grant['directory'])
                or type(grant['field']) is not str or not FIELD.fullmatch(grant['field'])
                or not _hash(grant['catalog_sha256']) or type(grant['entry']) is not dict
                or not _hash(grant['entry_sha256']) or _sha(_json(grant['entry'])) != grant['entry_sha256']
                or type(grant['active']) is not bool
                or not _integer(grant['charged_rows'], 0, 256)
                or not _integer(grant['charged_bytes'], 0, LIMITS['total_bytes'][1])):
            raise ImportRefused('invalid record grant binding')
        if (grant['active'] and grant['revoked_at'] is not None or not grant['active'] and
                (type(grant['revoked_at']) not in (int, float) or not math.isfinite(grant['revoked_at']))):
            raise ImportRefused('invalid record revocation')
        rows = grant['rows']
        if type(rows) is not list or not 1 <= len(rows) <= MAX_OFFSETS or not _integer(grant['cursor'], 0, len(rows)):
            raise ImportRefused('invalid record cursor')
        offsets = set()
        for index, row in enumerate(rows):
            if (type(row) is not dict or set(row) != {'offset', 'row_sha256', 'response_sha256', 'field_sha256', 'bytes',
                    'file_sha256', 'file_identity', 'source_ref', 'event_id', 'imported_at'}
                    or not _integer(row['offset'], 0, probe.MAX_OFFSET) or row['offset'] in offsets
                    or any(not _hash(row[k]) for k in ('row_sha256', 'response_sha256', 'field_sha256', 'file_sha256'))
                    or not _integer(row['bytes'], 1, min(quotas['row_bytes'], LIMITS['row_bytes'][1]))
                    or type(row['file_identity']) is not list or len(row['file_identity']) != 5
                    or any(not _integer(x, 0, 2**64-1) for x in row['file_identity'])
                    or row['file_identity'][2] > probe.MAX_RESPONSE + 4096):
                raise ImportRefused('invalid record row binding')
            offsets.add(row['offset'])
            ref = row['source_ref']
            if index < grant['cursor']:
                if (type(ref) is not dict or set(ref) != {'source_id', 'sha256', 'char_start', 'char_end', 'modality'}
                        or type(ref['source_id']) is not str or not 1 <= len(ref['source_id']) <= 160
                        or ref['sha256'] != row['field_sha256'] or not _integer(ref['char_start'], 0, 0)
                        or not _integer(ref['char_end'], 1, LIMITS['row_bytes'][1]) or ref['modality'] != 'text'
                        or type(row['event_id']) is not str or not 1 <= len(row['event_id']) <= 160
                        or type(row['imported_at']) not in (int, float) or not math.isfinite(row['imported_at'])):
                    raise ImportRefused('invalid imported source receipt')
                imported_bytes += row['bytes']
            elif any(row[k] is not None for k in ('source_ref', 'event_id', 'imported_at')):
                raise ImportRefused('uncommitted record has a source receipt')
        charged_rows += grant['charged_rows']; charged_bytes += grant['charged_bytes']
        imported_rows += grant['cursor']
    if (charged_rows != state['charged_rows'] or charged_bytes != state['charged_bytes']
            or imported_rows != state['imported_rows'] or imported_bytes != state['imported_bytes']
            or imported_rows > charged_rows or imported_bytes > charged_bytes
            or len(_json(state)) > MAX_METADATA):
        raise ImportRefused('invalid or oversized import accounting')


def _load(store):
    state, version = _box(store).load()
    _validate(state)
    return state, version


def _change(store, fn):
    def change(state):
        _validate(state)
        result = fn(state)
        _validate(state)
        return result
    return _box(store).mutate(change)


class _JoinedStore:
    """Reuse the actual composed Store methods in the caller's transaction."""
    def __init__(self, store, connection):
        if type(store) is not Store or connection is not store.db or not connection.in_transaction:
            raise ImportRefused('actual Store transaction required')
        self.store, self.connection = store, connection
    def __getattr__(self, name):
        return getattr(self.store, name)
    @contextmanager
    def tx(self):
        if self.connection is not self.store.db or not self.connection.in_transaction:
            raise ImportRefused('record transaction ended')
        yield self.connection
    def source(self, text, kind):
        return type(self.store).source(self, text, kind)
    def set_state(self, key, payload, expected=None):
        return type(self.store).set_state(self, key, payload, expected)


def _now():
    value = time.time()
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ImportRefused('invalid import clock')
    return float(value), datetime.fromtimestamp(value, timezone.utc).date().isoformat()


def _safety(runtime):
    if runtime.paused or runtime.store.queue_paused() or runtime.stop.is_set() or runtime.cancel_event.is_set():
        return 'PAUSED_OR_CANCELLED'
    if runtime.current not in (None, 'sleep') or runtime.store.queue_stats()['count'] or not runtime.jobs.empty():
        return 'USER_OR_JOB_WAITING'
    if runtime.guard.state != 'NORMAL':
        return 'RESOURCES'
    # RECORD ingestion neither requires a learning mode nor consumes training
    # rights. Existing G13 gates still enforce quiet hours, pause/burnout and
    # SELF initiative; this module only posts configured SYSTEM or USER events.
    return None


def _owner(runtime, event):
    if (type(event) is not dict or runtime.current != 'sleep'
            or threading.current_thread() is not runtime.worker):
        raise PermissionError('actual dispatched record-import worker required')
    matches = [row for row in runtime.sleep.scheduler.pending() if row.get('id') == event.get('id')]
    if len(matches) != 1:
        raise PermissionError('actual dispatched record-import event required')
    actual = matches[0]
    if (actual.get('action') != ACTION or actual.get('status') != 'DISPATCHED'
            or actual.get('origin') not in ('USER', 'SYSTEM')
            or any(event.get(k) != actual.get(k) for k in ('action', 'origin'))
            or actual.get('expires') is not None and time.time() >= actual['expires']):
        raise PermissionError('actual dispatched record-import event required')


def _identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _file_bytes(directory, filename, budget):
    budget.check()
    flags = ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')
    if not all(hasattr(os, flag) for flag in flags):
        raise ImportRefused('safe local preview reading unsupported')
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    file_fd = None
    try:
        directory_identity = list((os.fstat(directory_fd).st_dev, os.fstat(directory_fd).st_ino))
        file_fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        first = os.fstat(file_fd)
        if not stat.S_ISREG(first.st_mode) or first.st_size > probe.MAX_RESPONSE + 4096:
            raise ImportRefused('preview is not a bounded regular file')
        chunks = []; size = 0
        while True:
            budget.check()
            chunk = os.read(file_fd, min(65536, probe.MAX_RESPONSE + 4097 - size))
            if not chunk:
                break
            chunks.append(chunk); size += len(chunk)
            if size > probe.MAX_RESPONSE + 4096:
                raise ImportRefused('preview exceeded file budget')
        final = os.fstat(file_fd)
        named = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        if _identity(first) != _identity(final) or _identity(final) != _identity(named) or size != first.st_size:
            raise ImportRefused('preview changed during read')
        budget.check()
        return b''.join(chunks), _identity(final), directory_identity
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(directory_fd)


def _preview(dataset_id, directory, offset, field, byte_limit, budget):
    entries = probe.load_catalog()
    entry = entries.get(dataset_id)
    if entry is None or entry['access'] != 'PROBE':
        raise ImportRefused('dataset is unknown or held')
    budget.check()
    value = probe.read_staged(dataset_id, directory, offset)  # Never fetch or stage.
    budget.check()
    raw, identity, directory_identity = _file_bytes(directory, probe._filename(entry, offset), budget)
    if probe._loads(raw) != value:
        raise ImportRefused('preview changed between checked reads')
    text = value['row'].get(field)
    if type(text) is not str or not text.strip() or not 1 <= len(text.encode('utf-8')) <= byte_limit:
        raise ImportRefused('selected field is not a small nonempty text')
    row = dict(offset=offset, row_sha256=value['row_sha256'], response_sha256=value['response_sha256'],
               field_sha256=_sha(text.encode('utf-8')), bytes=len(text.encode('utf-8')),
               file_sha256=_sha(raw), file_identity=identity,
               source_ref=None, event_id=None, imported_at=None)
    return entry, text, row, directory_identity


def configure(runtime, overrides, authority='SYSTEM'):
    if authority != HUMAN:
        raise PermissionError('explicit record-import configuration required')
    if type(overrides) is not dict or any(k not in LIMITS or not _integer(v, *LIMITS[k]) for k, v in overrides.items()):
        raise ImportRefused('invalid record-import configuration')
    _change(runtime.store, lambda state: state['config'].update(overrides))
    return status(runtime)


def admit_record(runtime, dataset_id, stage_dir, offsets=(0,), field='text', quotas=None, authority='SYSTEM'):
    if authority != HUMAN:
        raise PermissionError('explicit local dataset selection required')
    runtime.require_idle()
    if _safety(runtime):
        raise ImportRefused('record admission requires idle normal resources')
    if (type(offsets) not in (list, tuple) or not 1 <= len(offsets) <= MAX_OFFSETS
            or any(not _integer(x, 0, probe.MAX_OFFSET) for x in offsets) or len(set(offsets)) != len(offsets)
            or type(field) is not str or not FIELD.fullmatch(field)):
        raise ImportRefused('select bounded unique offsets and one text field')
    directory = str(Path(stage_dir).expanduser().absolute())
    if len(directory) > 1024 or '\0' in directory:
        raise ImportRefused('invalid local preview directory')
    state, _ = _load(runtime.store)
    cfg = state['config']; limits = {k: cfg[k] for k in QUOTAS}
    if quotas is not None:
        if type(quotas) is not dict or any(k not in QUOTAS or not _integer(v, *LIMITS[k]) or v > cfg[k]
                                            for k, v in quotas.items()):
            raise ImportRefused('grant quotas may only narrow current import limits')
        limits.update(quotas)
    budget = Budget(time.monotonic() + 2., lambda: _safety(runtime) is None)
    rows = []; first_directory = None
    for offset in offsets:
        entry, _, row, directory_identity = _preview(dataset_id, directory, offset, field, limits['row_bytes'], budget)
        if first_directory is not None and directory_identity != first_directory:
            raise ImportRefused('preview directory changed during admission')
        first_directory = directory_identity
        rows.append(row)
    grant = dict(dataset_id=dataset_id, stage_dir=directory, directory=directory_identity, field=field,
                 catalog_sha256=probe.CATALOG_SHA256, entry=entry, entry_sha256=_sha(_json(entry)),
                 quotas=limits, rows=rows, cursor=0, active=True, revoked_at=None, charged_rows=0, charged_bytes=0)
    admission_id = _sha(_json(grant))
    def put(current):
        if admission_id in current['admissions']:
            if not current['admissions'][admission_id]['active']:
                raise ImportRefused('this selection was revoked; no automatic re-admission')
            return admission_id
        if len(current['order']) >= MAX_ADMISSIONS:
            raise ImportRefused('record admission capacity reached; nothing was removed')
        current['admissions'][admission_id] = grant
        current['order'].append(admission_id)
        return admission_id
    _change(runtime.store, put)
    return dict(admission_id=admission_id, rows=len(rows), enabled=state['enabled'],
                purpose='PREVIEW_ONLY', training_authority=0, scope=SCOPE)


def set_enabled(runtime, value, authority='SYSTEM'):
    if type(value) is not bool:
        raise ImportRefused('record-import switch requires boolean')
    if value and authority != HUMAN:
        raise PermissionError('explicit record-import activation required')
    _change(runtime.store, lambda state: state.update(enabled=value))
    return status(runtime)


def _next(state):
    for key in state['order']:
        grant = state['admissions'][key]
        if grant['active'] and grant['cursor'] < len(grant['rows']):
            return key, grant, grant['rows'][grant['cursor']]
    return None


def _due(state, now, day):
    if state['last_attempt'] is not None and now < state['last_attempt']:
        return 'CLOCK_ROLLBACK'
    if state['last_attempt'] is not None and now - state['last_attempt'] < state['config']['interval_s']:
        return 'COOLDOWN'
    pending = _next(state)
    if pending is None:
        return 'NO_PENDING_RECORDS'
    _, grant, row = pending
    cfg = state['config']; limits = {k: min(cfg[k], grant['quotas'][k]) for k in QUOTAS}
    cost = row['bytes'] + RECEIPT_BYTES
    day_rows, day_bytes = (state['day_rows'], state['day_bytes']) if state['day'] == day else (0, 0)
    if row['bytes'] > limits['row_bytes']:
        return 'ROW_QUOTA'
    if day_rows >= limits['daily_rows'] or day_bytes + cost > limits['daily_bytes']:
        return 'DAILY_QUOTA'
    if (state['charged_rows'] >= cfg['total_rows'] or state['charged_bytes'] + cost > cfg['total_bytes']
            or grant['charged_rows'] >= grant['quotas']['total_rows']
            or grant['charged_bytes'] + cost > grant['quotas']['total_bytes']):
        return 'TOTAL_QUOTA'
    if state['reservation'] >= 10**9:
        return 'RESERVATION_CAPACITY'
    return None


def _reserve(runtime, event):
    now, day = _now()
    def reserve(state):
        reason = 'OFF' if not state['enabled'] else _safety(runtime)
        if not reason and event['origin'] == 'SYSTEM' and runtime.sleep.idle_seconds() < state['config']['min_idle_s']:
            reason = 'MIN_IDLE'
        if reason:
            return reason
        if state['last_event'] == event['id']:
            return 'EVENT_ALREADY_RESERVED'
        reason = _due(state, now, day)
        if reason:
            return reason
        key, grant, row = _next(state); cost = row['bytes'] + RECEIPT_BYTES
        if state['day'] != day:
            state['day_rows'] = state['day_bytes'] = 0
        state['day'] = day; state['last_attempt'] = now; state['last_event'] = event['id']
        state['day_rows'] += 1; state['day_bytes'] += cost
        state['charged_rows'] += 1; state['charged_bytes'] += cost; state['reservation'] += 1
        grant['charged_rows'] += 1; grant['charged_bytes'] += cost
        return dict(admission_id=key, cursor=grant['cursor'], reservation=state['reservation'])
    return _change(runtime.store, reserve)


def _record(state, event, result):
    record = dict(result, event_id=event['id'], purpose='PREVIEW_ONLY',
                  training_authority=0, weights_updated=False, scope=SCOPE)
    state['last_result'] = record
    state['history'] = (state['history'] + [record])[-8:]
    return record


def _finish(runtime, event, result):
    return _change(runtime.store, lambda state: _record(state, event, result))


def _check_grant(grant, budget):
    if grant['catalog_sha256'] != probe.CATALOG_SHA256:
        raise ImportRefused('record catalog binding changed')
    entry = probe.load_catalog().get(grant['dataset_id'])
    if entry != grant['entry'] or _sha(_json(entry)) != grant['entry_sha256']:
        raise ImportRefused('record revision or catalog entry changed')
    row = grant['rows'][grant['cursor']]
    _, text, current, directory = _preview(grant['dataset_id'], grant['stage_dir'], row['offset'],
                                          grant['field'], grant['quotas']['row_bytes'], budget)
    if directory != grant['directory'] or any(current[k] != row[k] for k in current if k not in ('source_ref', 'event_id', 'imported_at')):
        raise ImportRefused('admitted preview file or selected field changed')
    return text


def _commit(runtime, event, reservation, budget):
    with runtime.lock:
        budget.check()
        with budget.transaction(runtime.store) as connection:
            joined = _JoinedStore(runtime.store, connection)
            state, version = _load(joined)
            _owner(runtime, event)
            key = reservation['admission_id']; grant = state['admissions'][key]
            if (not state['enabled'] or not grant['active'] or state['last_event'] != event['id']
                    or state['reservation'] != reservation['reservation'] or grant['cursor'] != reservation['cursor']):
                raise ImportRefused('record permission or reservation changed')
            text = _check_grant(grant, budget)
            row = grant['rows'][grant['cursor']]
            for previous in grant['rows'][:grant['cursor']]:
                ref = previous['source_ref']
                source = joined.one('SELECT kind,deleted FROM sources WHERE id=?', (ref['source_id'],))
                if not source or source['kind'] != KIND or source['deleted'] or _sha(joined.read_source(ref).encode()) != previous['field_sha256']:
                    raise ImportRefused('previous imported source was revoked or changed')
                budget.check()
            ref = joined.source(text, KIND)
            if ref['sha256'] != row['field_sha256'] or joined.read_source(ref) != text:
                raise ImportRefused('external source publication did not match the admitted field')
            budget.check()
            row.update(source_ref=ref, event_id=event['id'], imported_at=_now()[0])
            grant['cursor'] += 1; state['imported_rows'] += 1; state['imported_bytes'] += row['bytes']
            result = _record(state, event, dict(status='IMPORTED', imported=True, persisted=True,
                             admission_id=key, offset=row['offset'], source_ref=ref, field_sha256=row['field_sha256']))
            _validate(state)
            joined.set_state(KEY, state, expected=version)
            return result


def step(runtime, event):
    _owner(runtime, event)
    reserved = _reserve(runtime, event)
    if type(reserved) is str:
        return _finish(runtime, event, dict(status='SKIPPED_' + reserved, blocked_reason=reserved,
                                           imported=False, persisted=False))
    cfg = _load(runtime.store)[0]['config']
    try:
        budget = Budget(time.monotonic() + cfg['deadline_ms'] / 1000., lambda: _safety(runtime) is None)
        return _commit(runtime, event, reserved, budget)
    except Exception as exc:
        # A source and its receipt/cursor share the transaction. If a wrapper
        # raises after COMMIT, the committed receipt remains authoritative.
        current, _ = _load(runtime.store)
        saved = current['last_result']
        if saved and saved.get('event_id') == event['id'] and saved.get('imported') is True:
            return dict(saved, status='IMPORTED_CONFIRMED_AFTER_ERROR')
        reason = str(exc) if isinstance(exc, ImportRefused) else 'CANCELLED_OR_DEADLINE' if isinstance(exc, ReadBudgetExceeded) else 'IMPORT_ERROR'
        return _finish(runtime, event, dict(status='BLOCKED_IMPORT', imported=False, persisted=False,
                       admission_id=reserved['admission_id'], blocked_reason=reason[:180], error=type(exc).__name__))


def maybe_post(runtime):
    state, _ = _load(runtime.store)
    if not state['enabled'] or _safety(runtime) or not runtime.idle():
        return None
    if _due(state, *_now()) or runtime.sleep.idle_seconds() < state['config']['min_idle_s']:
        return None
    probe.load_catalog()  # A changed pinned catalog cannot enqueue work.
    return runtime.sleep.scheduler.post('TIMER', origin='SYSTEM', action=ACTION,
                                        dedup='dataset-record-import', ttl=max(60, state['config']['interval_s']))


def revoke(runtime, admission_id, authority='SYSTEM'):
    if authority != HUMAN:
        raise PermissionError('explicit record-import revocation required')
    now, _ = _now()
    with runtime.store.tx() as connection:
        joined = _JoinedStore(runtime.store, connection)
        def withdraw(state):
            if admission_id not in state['admissions']:
                raise ImportRefused('unknown record admission')
            grant = state['admissions'][admission_id]
            grant.update(active=False, revoked_at=now)
            for row in grant['rows'][:grant['cursor']]:
                ref = row['source_ref']
                connection.execute('UPDATE sources SET deleted=1 WHERE id=? AND hash=? AND kind=?',
                                   (ref['source_id'], ref['sha256'], KIND))
            return dict(admission_id=admission_id, active=False, files_deleted=False,
                        quota_refunded=False, training_authority=0, scope=SCOPE)
        return _change(joined, withdraw)


def status(runtime):
    state, _ = _load(runtime.store)
    reason = 'OFF' if not state['enabled'] else _safety(runtime) or _due(state, *_now())
    return dict(enabled=state['enabled'], config=state['config'], blocked_reason=reason,
                admissions=[dict(admission_id=key, dataset_id=state['admissions'][key]['dataset_id'],
                                 active=state['admissions'][key]['active'], imported=state['admissions'][key]['cursor'],
                                 selected=len(state['admissions'][key]['rows'])) for key in state['order']],
                charged_rows=state['charged_rows'], charged_bytes=state['charged_bytes'],
                imported_rows=state['imported_rows'], imported_bytes=state['imported_bytes'],
                last_result=state['last_result'], purpose='PREVIEW_ONLY', training_authority=0,
                weights_updated=False, scope=SCOPE,
                quota_scope='CHARGED_IMPORT_PAYLOAD_AND_RECEIPTS; NOT_EXISTING_PREVIEWS_OR_TOTAL_DEVICE')


def _options(fields, json_values=True):
    result = {}
    for field in fields:
        key, value = field.split('=', 1)
        if key in result:
            raise ImportRefused('duplicate record-import option')
        result[key] = json.loads(value) if json_values else value
    return result


def operator(runtime, args):
    if not args or args == ['status']:
        return dumps(status(runtime))
    if args in (['on'], ['off']):
        return dumps(set_enabled(runtime, args[0] == 'on', HUMAN))
    if args and args[0] == 'cfg':
        return dumps(configure(runtime, _options(args[1:]), HUMAN))
    if len(args) >= 3 and args[0] == 'admit':
        options = _options(args[3:], False)
        field = options.pop('field', 'text')
        offsets = [int(x) for x in options.pop('offsets', '0').split(',')]
        quotas = {k: json.loads(v) for k, v in options.items()}
        return dumps(admit_record(runtime, args[1], args[2], offsets, field, quotas, HUMAN))
    if len(args) == 2 and args[0] == 'revoke':
        return dumps(revoke(runtime, args[1], HUMAN))
    if args == ['step']:
        state, _ = _load(runtime.store)
        if not state['enabled']:
            raise ImportRefused('enable record import explicitly before requesting a step')
        event_id = runtime.sleep.scheduler.post('TIMER', origin='USER', action=ACTION,
                    dedup='dataset-record-import', ttl=max(60, state['config']['interval_s']))
        runtime.wake.set()
        return dumps(dict(scheduled=event_id, scope=SCOPE, training_authority=0))
    raise ImportRefused(':dataset [status|on|off|step|cfg key=value|admit ID DIR [offsets=0,1 field=text]|revoke ID]')
