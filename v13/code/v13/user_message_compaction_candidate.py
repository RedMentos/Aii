"""Explicit bounded USER-message deduplication against verified source blobs.

Used only by the composed review Runtime. Assistant/teacher text, source bytes,
message IDs and provenance stay intact. Logical bytes saved are not a VACUUM,
physical file-size reduction, secure erasure or an unlimited-memory claim.
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
import zlib

from .agi.base import StateBox
from .common import dumps
from .source_read_budget_candidate import Budget, ReadBudgetExceeded
from .store import Store

ACTION = 'compact_user_messages'
KEY = 'USER_MESSAGE_COMPACTION_V1'
REVISION = 'user-message-compaction-v1'
TABLE = 'compacted_user_messages_v1'
STORE_SHA256 = 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980'
HUMAN = 'EXPLICIT_HUMAN'
MAX_BYTES = 65536
MAX_CHARS = 65536
PREFIX_CHARS = 4096
MAX_PREFIX_BYTES = 4 * PREFIX_CHARS
MAX_ENTRIES = 8192
SCAN_ROWS = 16
CONFIG = {'interval_s': (60, 86400), 'min_idle_s': (0, 86400),
          'min_age_s': (86400, 3650 * 86400), 'keep_turns': (2, 128),
          'daily_attempts': (1, 64), 'ref_bytes': (65536, 16 * 1024 * 1024)}
HEX = re.compile(r'[0-9a-f]{64}\Z')


class CompactionError(ValueError):
    pass


def _hash(value):
    return hashlib.sha256(value if type(value) is bytes else value.encode('utf-8')).hexdigest()


def _json(value):
    def pairs(items):
        result = {}
        for key, entry in items:
            if key in result:
                raise CompactionError('duplicate message metadata key')
            result[key] = entry
        return result
    try:
        return json.loads(value, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(CompactionError('nonfinite metadata')))
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise CompactionError('invalid message metadata') from exc


def _check_store(store):
    if type(store) is not Store or _hash((Path(__file__).resolve().parent / 'store.py').read_bytes()) != STORE_SHA256:
        raise CompactionError('reviewed Store required for user-message compaction')


def _empty():
    return dict(enabled=False, interval_s=300, min_idle_s=300, min_age_s=30 * 86400,
                keep_turns=4, daily_attempts=8, ref_bytes=2 * 1024 * 1024,
                last_attempt=None, day=None, reserved_today=0, reservation=0,
                last_event=None, cursor=0, last_result=None)


def box(runtime):
    return StateBox(runtime.store, KEY, REVISION, _empty)


def _load(runtime):
    state, version = box(runtime).load()
    if type(state) is not dict or set(state) != set(_empty()) | {'revision'}:
        raise CompactionError('invalid compaction policy fields')
    for key, (low, high) in CONFIG.items():
        if type(state[key]) is not int or not low <= state[key] <= high:
            raise CompactionError('invalid compaction budget: ' + key)
    if (type(state['enabled']) is not bool
            or type(state['reserved_today']) is not int or not 0 <= state['reserved_today'] <= 64
            or type(state['reservation']) is not int or not 0 <= state['reservation'] <= 10**9
            or type(state['cursor']) is not int or not 0 <= state['cursor'] <= 2**63 - 1
            or state['last_attempt'] is not None and (type(state['last_attempt']) not in (int, float)
                 or not math.isfinite(state['last_attempt']) or state['last_attempt'] < 0)
            or state['day'] is not None and (type(state['day']) is not str
                 or not re.fullmatch(r'\d{4}-\d\d-\d\d', state['day']))
            or state['last_event'] is not None and (type(state['last_event']) is not str or len(state['last_event']) > 160)
            or state['last_result'] is not None and (type(state['last_result']) is not dict
                 or len(dumps(state['last_result'])) > 4096)):
        raise CompactionError('invalid compaction policy state')
    return state, version


def _now():
    now = time.time()
    if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
        raise CompactionError('invalid compaction clock')
    return float(now), datetime.fromtimestamp(now, timezone.utc).date().isoformat()


def _has_table(store):
    return store.one("SELECT 1 AS present FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)) is not None


def _schema(store):
    _check_store(store)
    with store.tx() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS compacted_user_messages_v1(
            message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
            session_id TEXT NOT NULL,event_id TEXT NOT NULL,source_id TEXT NOT NULL,
            source_ref TEXT NOT NULL,original_sha256 TEXT NOT NULL,byte_count INTEGER NOT NULL,
            char_count INTEGER NOT NULL,metadata_sha256 TEXT NOT NULL,event_sha256 TEXT NOT NULL,
            event_generation TEXT NOT NULL,prefix BLOB,prefix_sha256 TEXT NOT NULL,created REAL NOT NULL)''')
        conn.execute('CREATE INDEX IF NOT EXISTS compacted_user_messages_source_v1 ON compacted_user_messages_v1(source_id)')
        # A derived search prefix never outlives explicit source revocation.
        conn.execute('''CREATE TRIGGER IF NOT EXISTS compacted_user_messages_revoke_v1
            AFTER UPDATE OF deleted ON sources WHEN NEW.deleted=1 BEGIN
            UPDATE compacted_user_messages_v1 SET prefix=NULL WHERE source_id=NEW.id; END''')


@contextmanager
def _joined(store, budget):
    """Join an already-owned Store transaction; otherwise use a bounded read fence."""
    acquired = False
    try:
        while not acquired:
            budget.check()
            wait = .02 if budget.deadline is None else max(0., min(.02, budget.deadline - budget.clock()))
            acquired = store.mutex.acquire(timeout=wait)
        budget.check()
        if store.db.in_transaction:
            yield store.db
            budget.check()
        else:
            with budget.transaction(store) as conn:
                yield conn
    finally:
        if acquired:
            store.mutex.release()


def _record(store, mid):
    if not _has_table(store):
        return None
    return store.one('''SELECT message_id,session_id,event_id,source_id,
        substr(source_ref,1,2049) AS source_ref,original_sha256,byte_count,char_count,
        metadata_sha256,event_sha256,event_generation,
        substr(prefix,1,?) AS prefix,prefix_sha256,created FROM compacted_user_messages_v1 WHERE message_id=?''',
                     (MAX_PREFIX_BYTES + 257, mid))


def _binding(store, row, record=None):
    if (type(row) is not dict or row.get('role') != 'user' or row.get('status') != 'FINAL'
            or type(row.get('id')) is not int or type(row.get('metadata')) is not str
            or len(row['metadata']) > 16384):
        raise CompactionError('user message binding invalid')
    event = store.one('''SELECT e.id,e.session_id,e.source_id,e.generation_id,
        substr(e.packet,1,16385) AS packet,s.hash,s.bytes,s.chars,s.kind,s.deleted,s.created
        FROM events e JOIN sources s ON s.id=e.source_id WHERE e.id=?''', (row['event_id'],))
    if (event is None or event['session_id'] != row['session_id'] or event['kind'] != 'USER'
            or event['deleted'] != 0 or type(event['packet']) is not str or len(event['packet']) > 16384
            or type(event['bytes']) is not int or not 1 <= event['bytes'] <= MAX_BYTES
            or type(event['chars']) is not int or not 1 <= event['chars'] <= MAX_CHARS):
        raise CompactionError('user event source unavailable or outside compaction bounds')
    envelope = _json(event['packet']);metadata = _json(row['metadata'])
    ref = envelope.get('source_ref') if type(envelope) is dict else None
    if (type(ref) is not dict or set(ref) != {'source_id', 'sha256', 'modality', 'char_start', 'char_end'}
            or type(metadata) is not dict or metadata.get('source_ref') != ref
            or ref.get('source_id') != event['source_id'] or ref.get('sha256') != event['hash']
            or type(ref.get('sha256')) is not str or not HEX.fullmatch(ref['sha256'])
            or ref.get('modality') != 'text' or type(ref.get('char_start')) is not int or ref['char_start'] != 0
            or type(ref.get('char_end')) is not int or ref['char_end'] != event['chars']
            or envelope.get('event_id') != row['event_id'] or envelope.get('authority') != 'AUTHORITATIVE'
            or envelope.get('kind') != 'USER_TEXT' or envelope.get('brain_generation_id') != event['generation_id']):
        raise CompactionError('user event/metadata source binding changed')
    if record is not None:
        if (row['text'] != '' or record['message_id'] != row['id'] or record['session_id'] != row['session_id']
                or record['event_id'] != row['event_id'] or record['source_id'] != ref['source_id']
                or len(record['source_ref']) > 2048 or _json(record['source_ref']) != ref
                or record['original_sha256'] != ref['sha256'] or record['byte_count'] != event['bytes']
                or record['char_count'] != event['chars'] or record['event_generation'] != event['generation_id']
                or record['metadata_sha256'] != _hash(row['metadata']) or record['event_sha256'] != _hash(event['packet'])):
            raise CompactionError('compacted user message receipt changed')
    return event, ref


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _source_text(store, event, ref, budget, archive_only=False):
    """Small full verification, without starting a nested SQLite transaction."""
    directory = os.open(store.home / 'data/blobs', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        key = ref['sha256'];name = key
        if archive_only:
            try:
                os.stat(key, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise CompactionError('user source is not exclusively archived')
            name = key + '.z'
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        except FileNotFoundError:
            if archive_only:
                raise
            name = key + '.z'
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        first = os.fstat(fd)
        if not stat.S_ISREG(first.st_mode) or not 0 < first.st_size <= MAX_BYTES:
            raise CompactionError('source file exceeds small compaction read budget')
        chunks = [];size = 0
        while True:
            budget.check()
            part = os.read(fd, min(16384, MAX_BYTES - size + 1))
            if not part:
                break
            chunks.append(part);size += len(part)
            if size > MAX_BYTES:
                raise CompactionError('source file grew beyond compaction budget')
        raw = b''.join(chunks)
        if name.endswith('.z'):
            decoder = zlib.decompressobj();decoded = decoder.decompress(raw, MAX_BYTES + 1)
            if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data or len(decoded) > MAX_BYTES:
                raise CompactionError('source archive is truncated, oversized or has trailing data')
            raw = decoded
        if len(raw) != event['bytes'] or _hash(raw) != ref['sha256']:
            raise CompactionError('compaction source bytes do not match')
        value = raw.decode('utf-8', 'strict')
        if len(value) != event['chars']:
            raise CompactionError('compaction source character count does not match')
        if (_identity(first) != _identity(os.fstat(fd))
                or _identity(first) != _identity(os.stat(name, dir_fd=directory, follow_symlinks=False))):
            raise CompactionError('compaction source file changed')
        budget.check()
        return value
    except (OSError, UnicodeError, zlib.error) as exc:
        raise CompactionError('compaction source cannot be verified') from exc
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def hydrate_row(store, row, *, budget=None):
    """Reconstruct one marked USER row from its actual live source; never write text."""
    if row is None or row.get('role') != 'user' or type(row.get('id')) is not int:
        return row
    if not _has_table(store):
        return row
    budget = budget or Budget(time.monotonic()+.25)
    budget.check();_check_store(store)
    with _joined(store, budget):
        record = _record(store, row['id'])
        if record is None:
            return row
        current = store.one('SELECT * FROM messages WHERE id=?', (row['id'],))
        if current is None or any(key in row and row[key] != current[key]
                                  for key in ('session_id', 'event_id', 'role', 'status', 'metadata')):
            raise CompactionError('selected user message changed')
        event, ref = _binding(store, current, record)
        value = _source_text(store, event, ref, budget)
        if row.get('text') not in ('', value):
            raise CompactionError('caller user text differs from compacted source')
        _binding(store, current, _record(store, row['id']))
        return dict(row, text=value)


def hydrate_rows(store, rows, *, budget=None):
    if not _has_table(store):
        return rows
    budget = budget or Budget(time.monotonic()+.25)
    result = []
    for row in rows:
        try:
            result.append(hydrate_row(store, row, budget=budget))
        except (CompactionError, ReadBudgetExceeded):
            result.append(dict(row, text='', text_unavailable=True))
    return result


def user_event(store, event_id, session=None):
    sql = "SELECT * FROM messages WHERE event_id=? AND role='user'"
    args = [event_id]
    if session is not None:
        sql += ' AND session_id=?';args.append(session)
    rows = store.rows(sql + ' ORDER BY id LIMIT 2', args)
    if len(rows) != 1:
        return None
    try:
        return hydrate_row(store, rows[0])
    except (CompactionError, ReadBudgetExceeded):
        return None


def search_prefix(store, message_id, plain_prefix, *, budget=None):
    """Search-only derived prefix; model delivery still verifies the actual span."""
    _check_store(store);budget = budget or Budget()
    with _joined(store, budget):
        record = _record(store, message_id)
        if record is None:
            return plain_prefix
        row = store.one('SELECT * FROM messages WHERE id=?', (message_id,))
        _binding(store, row, record)
        raw = record['prefix']
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_PREFIX_BYTES + 256:
            raise CompactionError('compacted search prefix unavailable')
        decoder = zlib.decompressobj()
        try:
            decoded = decoder.decompress(raw, MAX_PREFIX_BYTES + 1)
            if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
                raise CompactionError('compacted prefix encoding invalid')
            value = decoded.decode('utf-8', 'strict')
        except (UnicodeError, zlib.error) as exc:
            raise CompactionError('compacted prefix encoding invalid') from exc
        if (len(value) != min(PREFIX_CHARS, record['char_count'])
                or len(decoded) > MAX_PREFIX_BYTES or _hash(decoded) != record['prefix_sha256']):
            raise CompactionError('compacted prefix content changed')
        budget.check()
        return value


def _usage(store):
    if not _has_table(store):
        return {'entries': 0, 'ref_payload_bytes': 0}
    row = store.one('''SELECT COUNT(*) AS entries,COALESCE(SUM(length(source_ref)+COALESCE(length(prefix),0)
        +length(session_id)+length(event_id)+length(source_id)+length(event_generation)+320),0)
        AS ref_payload_bytes FROM compacted_user_messages_v1''')
    return row


def _safety(runtime):
    from .inputs import paused
    if (runtime.paused or runtime.store.queue_paused() or runtime.stop.is_set() or runtime.cancel_event.is_set()
            or paused(runtime.store, 'training')):
        return 'PAUSED_OR_CANCELLED'
    if runtime.current not in (None, 'sleep') or runtime.store.queue_stats()['count'] or not runtime.jobs.empty():
        return 'USER_OR_JOB_WAITING'
    if runtime.guard.state != 'NORMAL':
        return 'RESOURCES'
    return None


def _due(state, now, day):
    if not state['enabled']:
        return 'OFF'
    if state['last_attempt'] is not None and now < state['last_attempt']:
        return 'CLOCK_ROLLBACK'
    if state['day'] == day and state['reserved_today'] >= state['daily_attempts']:
        return 'DAILY_BUDGET'
    if state['last_attempt'] is not None and now - state['last_attempt'] < state['interval_s']:
        return 'COOLDOWN'
    if state['reservation'] >= 10**9:
        return 'RESERVATION_CAPACITY'
    return None


def set_enabled(runtime, enabled, authority='SYSTEM'):
    if type(enabled) is not bool:
        raise ValueError('compaction switch requires boolean')
    if enabled and authority != HUMAN:
        raise PermissionError('explicit local compaction activation required')
    _load(runtime)
    if enabled:
        _schema(runtime.store)
    box(runtime).mutate(lambda state: state.update(enabled=enabled))
    return status(runtime)


def configure(runtime, overrides, authority='SYSTEM'):
    if authority != HUMAN:
        raise PermissionError('explicit local compaction configuration required')
    if type(overrides) is not dict or any(key not in CONFIG for key in overrides):
        raise ValueError('invalid compaction configuration keys')
    for key, value in overrides.items():
        low, high = CONFIG[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError('invalid compaction configuration: ' + key)
    _load(runtime);box(runtime).mutate(lambda state: state.update(overrides))
    return status(runtime)


def _owner(runtime, event):
    if (type(event) is not dict or runtime.current != 'sleep'
            or threading.current_thread() is not runtime.worker):
        raise PermissionError('actual compaction coordinator worker required')
    actual = [item for item in runtime.sleep.scheduler.pending() if item.get('id') == event.get('id')]
    if (len(actual) != 1 or actual[0].get('status') != 'DISPATCHED' or actual[0].get('action') != ACTION
            or actual[0].get('origin') not in ('USER', 'SYSTEM')
            or any(event.get(key) != actual[0].get(key) for key in ('action', 'origin'))
            or actual[0].get('expires') is not None and time.time() >= actual[0]['expires']):
        raise PermissionError('actual dispatched compaction event required')


def _compact(runtime, state, budget):
    store = runtime.store;now, _ = _now()
    keep = max(state['keep_turns'], min(256, int(runtime.cfg.get('history_turns', 6)) + 2))
    # This mutation must own its complete rollback boundary. Reader hydration
    # may join a caller transaction; ref insertion/text CAS must never do so.
    with budget.transaction(store) as conn:
        usage = _usage(store)
        if usage['entries'] >= MAX_ENTRIES or usage['ref_payload_bytes'] >= state['ref_bytes']:
            return {'status': 'REF_BUDGET', 'compacted': False}
        rows = store.rows('''SELECT m.* FROM messages m JOIN events e ON e.id=m.event_id
            JOIN sources s ON s.id=e.source_id WHERE m.id>? AND m.role='user' AND m.status='FINAL'
            AND m.text<>'' AND length(CAST(m.text AS BLOB)) BETWEEN 1024 AND ?
            AND m.created<? AND s.created<? AND s.kind='USER' AND s.deleted=0 AND s.bytes<=?
            AND m.session_id=e.session_id
            AND NOT EXISTS(SELECT 1 FROM compacted_user_messages_v1 c WHERE c.message_id=m.id)
            AND NOT EXISTS(SELECT 1 FROM memories a WHERE a.event_id=m.event_id AND a.active=1)
            AND m.id NOT IN(SELECT n.id FROM messages n WHERE n.session_id=m.session_id AND n.role='user'
                ORDER BY n.id DESC LIMIT ?) ORDER BY m.id LIMIT ?''',
            (state['cursor'], MAX_BYTES, now - state['min_age_s'], now - state['min_age_s'], MAX_BYTES, keep, SCAN_ROWS))
        if not rows:
            return {'status': 'NO_CANDIDATE', 'compacted': False, 'cursor': 0}
        cursor = rows[-1]['id']
        for row in rows:
            budget.check()
            try:
                event, ref = _binding(store, row)
                value = _source_text(store, event, ref, budget, archive_only=True)
                if value != row['text']:
                    continue
            except CompactionError:
                continue
            prefix = value[:PREFIX_CHARS].encode('utf-8');encoded = zlib.compress(prefix, 6)
            values = (row['id'], row['session_id'], row['event_id'], ref['source_id'], dumps(ref), ref['sha256'],
                      event['bytes'], event['chars'], _hash(row['metadata']), _hash(event['packet']),
                      event['generation_id'], encoded, _hash(prefix), now)
            size = len(values[4]) + len(encoded) + sum(len(values[i]) for i in (1, 2, 3, 10)) + 320
            if event['bytes'] <= size:
                continue
            if usage['ref_payload_bytes'] + size > state['ref_bytes']:
                return {'status': 'REF_BUDGET', 'compacted': False, 'cursor': cursor}
            current = store.one('SELECT * FROM messages WHERE id=?', (row['id'],))
            latest, latest_ref = _binding(store, current)
            if current != row or latest != event or latest_ref != ref:
                raise CompactionError('user row changed before compaction publication')
            if _source_text(store, latest, latest_ref, budget, archive_only=True) != value:
                raise CompactionError('user archive changed before compaction publication')
            budget.check()
            conn.execute('INSERT INTO compacted_user_messages_v1 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
            changed = conn.execute("UPDATE messages SET text='' WHERE id=? AND text=? AND metadata=? "
                                   "AND role='user' AND status='FINAL' AND event_id=? AND session_id=?",
                                   (row['id'], value, row['metadata'], row['event_id'], row['session_id'])).rowcount
            if changed != 1:
                raise CompactionError('user-message compaction CAS failed')
            budget.check()
            return {'status': 'COMPACTED', 'compacted': True, 'message_id': row['id'],
                    'source_sha256': ref['sha256'], 'logical_text_bytes_removed': event['bytes'],
                    'ref_payload_bytes': size, 'cursor': row['id']}
        return {'status': 'NO_VERIFIED_ARCHIVE', 'compacted': False, 'cursor': cursor}


def step(runtime, event):
    _check_store(runtime.store);_owner(runtime, event)
    state, _ = _load(runtime);now, day = _now()
    reason = _safety(runtime) or _due(state, now, day)
    if reason is None and event['origin'] == 'SYSTEM' and runtime.sleep.idle_seconds() < state['min_idle_s']:
        reason = 'MIN_IDLE'
    if reason:
        result = {'status': 'SKIPPED_' + reason, 'compacted': False, 'event_id': event['id']}
        box(runtime).mutate(lambda current: current.update(last_result=result))
        return result
    def reserve(current):
        if _due(current, now, day) or current['last_event'] == event['id']:
            raise CompactionError('compaction reservation no longer available')
        current['reserved_today'] = (current['reserved_today'] if current['day'] == day else 0) + 1
        current['day'] = day;current['last_attempt'] = now;current['reservation'] += 1
        current['last_event'] = event['id']
        return dict(current)
    reserved = box(runtime).mutate(reserve)
    def continuing():
        try:
            _owner(runtime, event)
            current, _ = _load(runtime)
            return (_safety(runtime) is None and current['enabled']
                    and current['reservation'] == reserved['reservation'] and current['last_event'] == event['id']
                    and all(current[key] == reserved[key] for key in CONFIG))
        except (PermissionError, ValueError):
            return False
    try:
        budget = Budget(time.monotonic() + .5, continuing)
        result = _compact(runtime, reserved, budget)
    except OSError as exc:
        result = {'status': 'UNKNOWN_IO_OUTCOME', 'compacted': None,
                  'error': type(exc).__name__, 'outcome': 'UNKNOWN_AFTER_IO_ERROR'}
    except ValueError as exc:
        result = {'status': 'UNAVAILABLE', 'compacted': False, 'error': type(exc).__name__}
    result['event_id'] = event['id']
    def finish(current):
        if current['reservation'] != reserved['reservation'] or current['last_event'] != event['id']:
            raise CompactionError('compaction reservation changed')
        current['last_result'] = {key: value for key, value in result.items() if key != 'cursor'}
        current['cursor'] = result.get('cursor', current['cursor'])
    box(runtime).mutate(finish)
    return result


def maybe_post(runtime):
    state, _ = _load(runtime);now, day = _now()
    if (_safety(runtime) or _due(state, now, day) or not runtime.idle()
            or runtime.sleep.idle_seconds() < state['min_idle_s']):
        return None
    return runtime.sleep.scheduler.post('TIMER', origin='SYSTEM', action=ACTION,
        dedup='compact-user-messages', ttl=max(60, state['interval_s']))


def status(runtime):
    state, _ = _load(runtime);now, day = _now()
    return {'enabled': state['enabled'], 'config': {key: state[key] for key in CONFIG},
            'blocked_reason': _safety(runtime) or _due(state, now, day),
            'reserved_today': state['reserved_today'] if state['day'] == day else 0,
            'usage': _usage(runtime.store), 'last_result': state['last_result'],
            'scope': 'OLD_FINAL_USER_TEXT_SOURCE_DEDUPLICATION', 'training_authority': 0,
            'physical_file_bytes_saved_measured': False, 'whole_system_complete': False}


def operator(runtime, args):
    if args in ([], ['status']):
        return dumps(status(runtime))
    if args in (['on'], ['off']):
        return dumps(set_enabled(runtime, args == ['on'], HUMAN))
    if args and args[0] == 'cfg':
        values = {}
        for item in args[1:]:
            key, value = item.split('=', 1)
            if key in values:
                raise ValueError('duplicate compaction configuration')
            values[key] = json.loads(value)
        return dumps(configure(runtime, values, HUMAN))
    if args == ['step']:
        state, _ = _load(runtime)
        if not state['enabled']:
            raise ValueError('enable user-message compaction explicitly first')
        event_id = runtime.sleep.scheduler.post('TIMER', origin='USER', action=ACTION,
            dedup='compact-user-messages', ttl=max(60, state['interval_s']))
        runtime.wake.set()
        return dumps({'scheduled': event_id, 'action': ACTION})
    raise ValueError(':archive compact [status|on|off|step|cfg key=value]')
