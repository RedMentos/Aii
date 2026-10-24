"""§94.4 Sleep C trace-decay planning, without learning or fact authority.

This helper does not access the Store, model weights, permissions or external
processes. Plan the *whole* batch before applying it so invalid persisted
state cannot leave an earlier trace half-decayed. Production callsite remains
behind existing SleepRuntime/age/resource gates.
"""
import math

DAY = 86400.0


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ': expected finite number')
    return float(value)


def plan_trace_decay(items, now, per_day, floor):
    """Return non-mutating, validated (item, action, priority, watermark) plans.

    Existing persisted schedules without ``trace_decay_at`` use their
    ``last``/``created`` anchor once; no attempt is made to undo old over-decay.
    """
    now = _finite(now, 'now')
    per_day = _finite(per_day, 'per_day')
    floor = _finite(floor, 'floor')
    if not (0.5 <= per_day <= 1.0 and 0.0 <= floor <= 0.5):
        raise ValueError('Sleep C decay policy outside canonical bounds')
    plan = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('trace item is not a dict')
        if item.get('retired'):
            continue
        expiry = _finite(item['expires'], 'expires')
        if expiry < now:
            plan.append((item, 'expire', None, None))
            continue
        priority = _finite(item['priority'], 'priority')
        if not 0.0 <= priority <= 1.0:
            raise ValueError('priority outside [0,1]')
        created = _finite(item['created'], 'created')
        last = item.get('last')
        origin = _finite(last, 'last') if last is not None else created
        watermark = item.get('trace_decay_at', origin)
        watermark = _finite(watermark, 'trace_decay_at')
        anchor = max(origin, watermark)
        if now <= anchor:
            plan.append((item, 'unchanged', priority, watermark))
            continue
        days = (now - anchor) / DAY
        # The floor is a lower bound for decay, never a priority-raising action.
        new_priority = min(priority, max(floor, priority * per_day ** days))
        plan.append((item, 'decay', new_priority, now))
    return plan


def apply_trace_decay(plan):
    """Apply an already validated plan; return (decayed_count, expired_count)."""
    decayed = expired = 0
    for item, action, priority, watermark in plan:
        if action == 'expire':
            item['retired'] = 'TTL'
            expired += 1
        elif action == 'decay':
            if priority < item['priority']:
                decayed += 1
            item['priority'] = priority
            item['trace_decay_at'] = watermark
        elif action != 'unchanged':
            raise ValueError('unknown trace decay action')
    return decayed, expired
