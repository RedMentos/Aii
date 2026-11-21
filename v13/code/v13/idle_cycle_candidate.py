"""Opt-in rolling quota for existing idle jobs; no new learner or model rights.

Used only by the hash-bound Termux recovery candidate. The original per-input
budget remains the default. A sustained cycle is at most twelve existing jobs
per rolling hour, including retries, and never manufactures a user turn.
"""
from __future__ import annotations

import math

KEY = 'IDLE_CYCLE_POLICY_V1'
REVISION = 'idle-cycle-policy-v1'
WINDOW_SECONDS = 3600.0
MAX_PER_HOUR = 12
ALLOWED = frozenset({'sleep_full', 'sleep_a', 'sleep_b', 'sleep_c',
                     'wake_replay', 'learn_medium', 'learn_slow'})


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _load(store):
    state, version = store.state(KEY, None)
    if state is None:
        return {'revision': REVISION, 'enabled': False,
                'since': None, 'last_clock': None}, version
    if (type(state) is not dict or set(state) != {'revision', 'enabled', 'since', 'last_clock'}
            or state['revision'] != REVISION or type(state['enabled']) is not bool
            or any(v is not None and not _number(v) for v in (state['since'], state['last_clock']))
            or (state['enabled'] and (state['since'] is None or state['last_clock'] is None))):
        raise ValueError('Invalid idle-cycle policy')
    return state, version


def set_enabled(scheduler, value, authority='SYSTEM'):
    if authority != 'EXPLICIT_HUMAN':
        raise PermissionError('Idle cycle changes require explicit local operator action')
    if type(value) is not bool:
        raise ValueError('Idle cycle on|off')
    now = scheduler.clock()
    if not _number(now):
        raise ValueError('Invalid idle-cycle clock')
    with scheduler.s.mutex:
        state, version = _load(scheduler.s)
        previous = state['last_clock']
        if value and previous is not None and now < previous:
            raise ValueError('Idle cycle clock moved backwards')
        state.update(enabled=value, since=now if value and not state['enabled'] else state['since'],
                     last_clock=max(now, previous or 0))
        scheduler.s.set_state(KEY, state, expected=version)
    return value


def _quota(scheduler, state, *, remember_clock=False):
    """Read the dispatch ledger without trusting compact event history."""
    now = scheduler.clock()
    result = {'mode': 'ROLLING_HOUR', 'window_seconds': WINDOW_SECONDS,
              'limit': MAX_PER_HOUR, 'used': None, 'remaining': 0,
              'next_replenishment_at': None, 'blocked_reason': None}
    if not _number(now):
        return result | {'blocked_reason': 'INVALID_CLOCK'}
    if state['last_clock'] is not None and now < state['last_clock']:
        return result | {'blocked_reason': 'CLOCK_ROLLBACK'}
    try:
        from .inputs import pauses
        cap = pauses(scheduler.s)['burnout_budget']
        if type(cap) is not int or not 0 <= cap <= 1000:
            raise ValueError('invalid configured budget')
        result['limit'] = min(MAX_PER_HOUR, cap)
        ledger, _ = scheduler._load()
        times = ledger.get('dispatch_times')
        if times is None:
            # A truly empty queue has no lost dispatches. Historical dispatches
            # without the durable ledger cannot safely earn a refreshed quota.
            if any(e.get('dispatch_log') or e.get('dispatched') is not None
                   or (e.get('origin') != 'USER' and e.get('action') not in (None, 'notice')
                       and e.get('status') in {'DISPATCHED', 'DONE', 'FAILED'})
                   for e in ledger['events'] + ledger['history']):
                return result | {'blocked_reason': 'LEGACY_DISPATCH_LEDGER'}
            times = []
        from .scheduler import DISPATCH_LEDGER_MAX
        if (type(times) is not list or len(times) > DISPATCH_LEDGER_MAX
                or any(not _number(t) for t in times)
                or any(a > b for a, b in zip(times, times[1:]))):
            return result | {'blocked_reason': 'INVALID_DISPATCH_LEDGER'}
        if any(t > now for t in times):
            return result | {'blocked_reason': 'CLOCK_ROLLBACK'}
        recent = [t for t in times if now - WINDOW_SECONDS < t <= now]
        result.update(used=len(recent), remaining=max(0, result['limit'] - len(recent)),
                      next_replenishment_at=min(recent) + WINDOW_SECONDS if recent else None)
        if len(recent) >= result['limit']:
            result['blocked_reason'] = 'HOURLY_QUOTA' if result['limit'] else 'USER_BUDGET_ZERO'
        if remember_clock and now != state['last_clock']:
            current, version = _load(scheduler.s)
            if current['enabled'] and (current['last_clock'] is None or now >= current['last_clock']):
                current['last_clock'] = now
                scheduler.s.set_state(KEY, current, expected=version)
            elif current['enabled']:
                return result | {'blocked_reason': 'CLOCK_ROLLBACK', 'remaining': 0}
    except (KeyError, TypeError, ValueError, OverflowError):
        return result | {'blocked_reason': 'INVALID_IDLE_STATE', 'remaining': 0}
    return result


def blocked(scheduler, action, *, remember_clock=True):
    from .inputs import background_blocked, pauses
    try:
        state, _ = _load(scheduler.s)
        if not state['enabled']:
            return background_blocked(scheduler.s, action, scheduler.background_since_input())
        if action not in ALLOWED:
            return 'OUTSIDE_IDLE_CYCLE_ACTIONS'
        # Keep existing operator pause controls, including stricter protection
        # for the learning and dream phases hidden inside composite jobs.
        reason = background_blocked(scheduler.s, action, 0)
        if reason:
            return reason
        paused = pauses(scheduler.s)['paused']
        if 'training' in paused and action.startswith('learn_'):
            return 'PAUSED_TRAINING'
        if 'traum' in paused and action == 'sleep_full':
            return 'PAUSED_TRAUM'
        return _quota(scheduler, state, remember_clock=remember_clock)['blocked_reason']
    except (KeyError, TypeError, ValueError, OverflowError):
        return 'INVALID_IDLE_STATE'


def status(runtime):
    scheduler = runtime.sleep.scheduler
    try:
        state, _ = _load(runtime.store)
        enabled = state['enabled']
        if enabled:
            quota = _quota(scheduler, state)
        else:
            from .inputs import pauses
            limit = pauses(runtime.store)['burnout_budget']
            used = scheduler.background_since_input()
            quota = {'mode': 'PER_INPUT', 'limit': limit, 'used': used,
                     'remaining': max(0, limit - used), 'next_replenishment_at': None,
                     'blocked_reason': 'WAITING_FOR_INPUT' if used >= limit else None}
        reason = quota['blocked_reason']
    except (KeyError, TypeError, ValueError, OverflowError):
        enabled = False
        quota = {'mode': 'INVALID', 'remaining': 0}
        reason = 'INVALID_IDLE_STATE'
    if runtime.stop.is_set():
        reason = 'RUNTIME_STOPPED'
    elif runtime.paused:
        reason = 'RUNTIME_PAUSED'
    elif runtime.current is not None or not runtime.jobs.empty() or runtime.store.queue_stats()['count']:
        reason = 'FOREGROUND_OR_JOB_BUSY'
    else:
        resource = runtime.sleep.resource_state()
        if resource == 'CRITICAL':
            reason = 'RESOURCES_CRITICAL'
        elif resource == 'PRESSURE':
            reason = 'RESOURCE_PRESSURE_SLEEP_C_ONLY'
        elif reason is None:
            reason = blocked(scheduler, 'sleep_full', remember_clock=False)
    from .world_model import report
    world = report(runtime.store)
    sleep = runtime.sleep.cycle.status()
    worker = getattr(runtime, 'worker', None)
    if worker is None or not worker.is_alive():
        reason = 'WORKER_NOT_RUNNING'
    policy = sleep['policy']
    idle_seconds = runtime.sleep.idle_seconds()
    return {'revision': REVISION, 'enabled': enabled,
            'worker_alive': bool(worker and worker.is_alive()), 'current_job': runtime.current,
            'learning_mode': runtime.cfg.get('learning_mode'), 'quota': quota,
            'blocked_reason': reason, 'idle_seconds': round(idle_seconds, 3),
            'sleep_cycles': sleep['cycles'], 'last_sleep': sleep['last'],
            'idle_threshold_seconds': policy['sleep_idle_s'],
            'sleep_interval_seconds': policy['sleep_interval_s'],
            'last_real_learning': {'component': 'T8_WORLD_MODEL', 'status': world['status'],
                                   'samples': world.get('n', 0),
                                   'parameters_fitted': world['status'] == 'FITTED'},
            'claim_limit': 'Existing local idle jobs only; no new learner, GGUF update, '
                           'model promotion, external input or Android lifetime guarantee'}


def operator_command(runtime, args):
    if not args or args == ['status']:
        return status(runtime)
    if args in (['on'], ['off']):
        set_enabled(runtime.sleep.scheduler, args[0] == 'on', 'EXPLICIT_HUMAN')
        runtime.wake.set()
        return status(runtime)
    raise ValueError(':idle [status|on|off]')
