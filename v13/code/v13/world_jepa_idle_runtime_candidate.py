"""Bounded, explicitly enabled World-JEPA work on the existing G13 worker.

Only used by the hash-bound integrated review copy. Private numeric World
training is distinct from native model learning, dataset admission and tools.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import threading
import time
import weakref

from . import online_world_policy as policy
from .agi.base import StateBox
from .common import dumps

AUTHORITY = 'IDLE_SCHEDULER'
ACTION = 'learn_world_jepa_idle'
KEY = 'WORLD_JEPA_IDLE_POLICY_V1'
REVISION = 'world-jepa-idle-policy-v1'
SCOPE = 'NUMERIC_WORLD_JEPA_PRIVATE'
HISTORY = 8
CONFIG = {'interval_s': (30, 86400), 'min_idle_s': (0, 86400),
          'daily_steps': (1, 32), 'max_rows': (16, 128)}
OWNERS = weakref.WeakKeyDictionary()


def _empty():
    return {'enabled': False, 'interval_s': 300, 'min_idle_s': 300,
            'daily_steps': 8, 'max_rows': 64, 'last_attempt': None,
            'day': None, 'reserved_today': 0, 'reservation': 0,
            'last_event': None, 'last_result': None, 'history': [],
            'quarantined': False}


def box(runtime):
    return StateBox(runtime.store, KEY, REVISION, _empty)


def _load(runtime):
    state, version = box(runtime).load()
    if type(state) is not dict or set(state) != set(_empty()) | {'revision'}:
        raise ValueError('invalid idle World policy fields')
    for key, (low, high) in CONFIG.items():
        if type(state[key]) is not int or not low <= state[key] <= high:
            raise ValueError('invalid idle World budget: ' + key)
    if (type(state['enabled']) is not bool or type(state['quarantined']) is not bool
            or type(state['reserved_today']) is not int or not 0 <= state['reserved_today'] <= 32
            or type(state['reservation']) is not int or not 0 <= state['reservation'] <= 10**9
            or (state['last_event'] is not None and (type(state['last_event']) is not str or not 1 <= len(state['last_event']) <= 160))
            or (state['last_attempt'] is not None and (type(state['last_attempt']) not in (int, float)
                or not math.isfinite(state['last_attempt']) or state['last_attempt'] < 0))
            or (state['day'] is not None and (type(state['day']) is not str or len(state['day']) != 10))
            or type(state['history']) is not list or len(state['history']) > HISTORY
            or any(type(row) is not dict for row in state['history'])
            or (state['last_result'] is not None and type(state['last_result']) is not dict)):
        raise ValueError('invalid idle World policy state')
    # Metadata stays small even if a corrupted state contains nested values.
    if len(json.dumps(state, allow_nan=False)) > 16384:
        raise ValueError('oversized idle World policy metadata')
    if state['day'] is not None:
        datetime.strptime(state['day'], '%Y-%m-%d')
    return state, version


def _now():
    value = time.time()
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid idle World clock')
    day = datetime.fromtimestamp(value, timezone.utc).date().isoformat()
    return float(value), day


def _due(state, now, day):
    last = state['last_attempt']
    if last is not None and now < last:
        return 'CLOCK_ROLLBACK'
    used = state['reserved_today'] if state['day'] == day else 0
    if used >= state['daily_steps']:
        return 'DAILY_BUDGET'
    if last is not None and now - last < state['interval_s']:
        return 'COOLDOWN'
    if state['reservation'] >= 10**9:
        return 'RESERVATION_CAPACITY'
    return None


def _limits(state):
    return tuple(state[key] for key in CONFIG)


def set_enabled(runtime, value, authority='SYSTEM'):
    if type(value) is not bool:
        raise ValueError('idle World switch requires boolean')
    if value and authority != policy.HUMAN:
        raise PermissionError('explicit human idle World activation required')
    _load(runtime)
    def change(state):
        if value and state['quarantined']:
            raise ValueError('idle World quarantined; explicit recover required')
        state['enabled'] = value
    box(runtime).mutate(change)
    return status(runtime)


def configure(runtime, overrides, authority='SYSTEM'):
    if authority != policy.HUMAN:
        raise PermissionError('explicit human idle World configuration required')
    if type(overrides) is not dict or any(key not in CONFIG for key in overrides):
        raise ValueError('invalid idle World configuration keys')
    for key, value in overrides.items():
        low, high = CONFIG[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError('invalid idle World configuration: ' + key)
    _load(runtime)
    box(runtime).mutate(lambda state: state.update(overrides))
    return status(runtime)


def _blocked(runtime, state):
    if not state['enabled']:
        return 'OFF'
    if state['quarantined'] or getattr(runtime, '_world_jepa_quarantined', False):
        return 'QUARANTINED'
    return policy.safety_blocked(runtime)


def _event(runtime, event_id):
    events = runtime.sleep.scheduler.pending()
    matches = [row for row in events if row.get('id') == event_id]
    if len(matches) != 1:
        return None
    row = matches[0]
    if (row.get('action') != ACTION or row.get('status') != 'DISPATCHED'
            or row.get('origin') not in ('USER', 'SYSTEM')):
        return None
    if row.get('expires') is not None and time.time() >= row['expires']:
        return None
    return row


@contextmanager
def owner(runtime, event):
    if type(event) is not dict or runtime.current != 'sleep' or runtime in OWNERS:
        raise PermissionError('actual idle World worker owner required')
    actual = _event(runtime, event.get('id'))
    if actual is None or any(event.get(key) != actual.get(key) for key in ('action', 'origin')):
        raise PermissionError('actual dispatched idle World event required')
    marker = {'event_id': actual['id'], 'reservation': None, 'limits': None,
              'thread_id': threading.get_ident(), 'update_used': False,
              'operations': frozenset(('update', 'save', 'restore'))}
    OWNERS[runtime] = marker
    try:
        yield marker
    finally:
        OWNERS.pop(runtime, None)


def scope_blocked(runtime, operation='update'):
    if operation not in ('update', 'save', 'restore'):
        return 'OPERATION'
    marker = OWNERS.get(runtime)
    if (marker is None or runtime.current != 'sleep' or operation not in marker['operations']
            or marker['thread_id'] != threading.get_ident()):
        return 'OWNER_REQUIRED'
    event = _event(runtime, marker['event_id'])
    if event is None:
        return 'OWNER_REQUIRED'
    state, _ = _load(runtime)
    reason = _blocked(runtime, state)
    if reason:
        return reason
    if event['origin'] == 'SYSTEM' and runtime.sleep.idle_seconds() < state['min_idle_s']:
        return 'MIN_IDLE'
    if (marker['reservation'] is None or state['reservation'] != marker['reservation']
            or state['last_event'] != marker['event_id']):
        return 'RESERVATION_REQUIRED'
    if _limits(state) != marker['limits']:
        return 'POLICY_CHANGED'
    if operation == 'update' and marker['update_used']:
        return 'UPDATE_ALREADY_USED'
    return None


def require_owner(runtime, operation='update'):
    reason = scope_blocked(runtime, operation)
    if reason:
        raise PermissionError('idle World unavailable: ' + reason)


def validate_update(runtime, steps, limit):
    require_owner(runtime, 'update')
    state, _ = _load(runtime)
    if type(steps) is not int or steps != 1 or type(limit) is not int or not 16 <= limit <= state['max_rows']:
        raise ValueError('idle World update exceeds reserved one-step/row budget')


def claim_update(runtime, steps, limit):
    validate_update(runtime, steps, limit)
    OWNERS[runtime]['update_used'] = True


def _reserve(runtime, event, marker):
    _load(runtime)
    now, day = _now()
    def reserve(state):
        reason = _blocked(runtime, state)
        if reason:
            return reason
        if event['origin'] == 'SYSTEM' and runtime.sleep.idle_seconds() < state['min_idle_s']:
            return 'MIN_IDLE'
        if state['last_event'] == event['id']:
            return 'EVENT_ALREADY_RESERVED'
        reason = _due(state, now, day)
        if reason:
            return reason
        state['reserved_today'] = (state['reserved_today'] if state['day'] == day else 0) + 1
        state['day'], state['last_attempt'], state['last_event'] = day, now, event['id']
        state['reservation'] += 1
        return {'reservation': state['reservation'], 'limits': _limits(state), 'max_rows': state['max_rows']}
    result = box(runtime).mutate(reserve)
    if type(result) is dict:
        marker.update(reservation=result['reservation'], limits=result['limits'])
    return result


def _finish(runtime, event, result):
    try:
        now, _ = _now()
    except (ValueError, OverflowError, OSError):
        now = _load(runtime)[0]['last_attempt']
    allowed = ('status', 'trained', 'persisted', 'steps', 'source_sha256', 'error',
               'checkpoint_outcome', 'blocked_reason', 'quarantined')
    record = {key: result[key] for key in allowed if key in result}
    record.update(event_id=event.get('id'), at=now)
    def save(state):
        if result.get('quarantined'):
            state['quarantined'] = True
        state['last_result'] = record
        state['history'] = (state['history'] + [record])[-HISTORY:]
    box(runtime).mutate(save)
    return dict(result, scope=SCOPE, active_model_promoted=False)


def _model_state(runtime):
    model = getattr(runtime, '_world_jepa_online', None)
    return model, getattr(model, '_fit_steps', None)


def step(runtime, event):
    with owner(runtime, event) as marker:
        reserved = _reserve(runtime, event, marker)
        if type(reserved) is str:
            return _finish(runtime, event, {'status': 'SKIPPED_' + reserved,
                'blocked_reason': reserved, 'trained': False, 'persisted': False})
        before, old_steps = _model_state(runtime)
        save_started = False
        try:
            if before is None and (Path(runtime.home) / 'world_jepa_lineage/manifest.json').exists():
                runtime.world_jepa_restore(authority=AUTHORITY)
            before, old_steps = _model_state(runtime)
            result = runtime.world_jepa_update(steps=1, limit=reserved['max_rows'], authority=AUTHORITY)
            if not result.get('trained'):
                return _finish(runtime, event, {'status': result.get('status', 'SKIPPED_UPDATE'),
                    'trained': False, 'persisted': False})
            require_owner(runtime, 'save')
            save_started = True
            saved = runtime.world_jepa_save(authority=AUTHORITY)
            if saved.get('persisted') is not True:
                raise ValueError('idle World save was not confirmed')
            _, steps = _model_state(runtime)
            return _finish(runtime, event, {'status': 'UPDATED', 'trained': True, 'persisted': True,
                'steps': steps, 'source_sha256': result.get('source_sha256'),
                'checkpoint_outcome': 'CONFIRMED_PRIVATE'})
        except BaseException as exc:
            current, steps = _model_state(runtime)
            changed = current is not before or steps != old_steps
            quarantined = changed or getattr(runtime, '_world_jepa_quarantined', False)
            if quarantined:
                runtime._world_jepa_quarantined = True
            outcome = {'status': 'SAVE_UNCERTAIN_QUARANTINED' if save_started else 'BLOCKED_INPUT',
                       'trained': bool(changed), 'persisted': None if save_started else False,
                       'error': type(exc).__name__, 'quarantined': bool(quarantined),
                       'checkpoint_outcome': 'UNKNOWN_AFTER_SAVE_ERROR' if save_started else 'NOT_ATTEMPTED'}
            result = _finish(runtime, event, outcome)
            if not isinstance(exc, Exception):
                raise
            return result


def maybe_post(runtime):
    state, _ = _load(runtime)
    if _blocked(runtime, state) or not runtime.idle():
        return None
    now, day = _now()
    if _due(state, now, day) or runtime.sleep.idle_seconds() < state['min_idle_s']:
        return None
    return runtime.sleep.scheduler.post('TIMER', origin='SYSTEM', action=ACTION,
        dedup='idle-world-jepa', ttl=max(60, state['interval_s']))


def status(runtime):
    state, _ = _load(runtime)
    now, day = _now()
    reason = _blocked(runtime, state) or _due(state, now, day)
    return {'scope': SCOPE, 'enabled': state['enabled'],
            'config': {key: state[key] for key in CONFIG}, 'blocked_reason': reason,
            'reserved_today': state['reserved_today'] if state['day'] == day else 0,
            'last_result': state['last_result'], 'quarantined': state['quarantined'],
            'training_authority': 'ACTUAL_DISPATCHED_JOB_ONLY', 'active_model_promoted': False}


def recover(runtime, authority='SYSTEM'):
    if authority != policy.HUMAN:
        raise PermissionError('explicit human idle World recovery required')
    _load(runtime)
    runtime.require_idle()
    result = runtime.world_jepa_restore(authority=policy.HUMAN)
    box(runtime).mutate(lambda state: state.update(quarantined=False))
    return dict(result, scope=SCOPE, idle_quarantine_cleared=True)


def operator(runtime, args):
    if not args or args == ['status']:
        return dumps(status(runtime))
    if args in (['on'], ['off']):
        return dumps(set_enabled(runtime, args[0] == 'on', policy.HUMAN))
    if args == ['recover']:
        return dumps(recover(runtime, policy.HUMAN))
    if args == ['step']:
        state, _ = _load(runtime)
        if not state['enabled']:
            raise ValueError('enable idle World explicitly before requesting a step')
        event_id = runtime.sleep.scheduler.post('TIMER', origin='USER', action=ACTION,
            dedup='idle-world-jepa', ttl=max(60, state['interval_s']))
        runtime.wake.set()
        return dumps({'scheduled': event_id, 'scope': SCOPE})
    if args and args[0] == 'cfg':
        overrides = {}
        for field in args[1:]:
            key, value = field.split('=', 1)
            if key in overrides:
                raise ValueError('duplicate idle World setting')
            overrides[key] = json.loads(value)
        return dumps(configure(runtime, overrides, policy.HUMAN))
    raise ValueError(':learning idle [status|on|off|step|recover|cfg key=value]')
