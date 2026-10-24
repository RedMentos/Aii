"""Isolated B3-H9 exactly-once Callosum credit transition; no production wiring.

Intended insertion inside Callosum._mutate so the read-check-write is atomic
under Store's optimistic version check. No change to outcome formula or gates.
"""
import math


def credit_once(state, event_id, observations, update):
    """Apply only new, source-matched receiver observations to pending messages.

    `observations` are computed from verified receiver OfferPackets as in the
    existing Callosum.outcome; this function does NOT independently validate
    those packets. `update` is the existing Callosum._update bound callback.
    Returns the actual applied utility observations, not attempted count.
    """
    pending = state.get('pending', {}).get(event_id, [])
    if not isinstance(pending, list):
        raise ValueError('malformed pending Callosum state')
    applied = []
    seen = set()
    for obs in observations:
        mid = obs.get('msg')
        if not isinstance(mid, str) or not mid or mid in seen:
            continue
        seen.add(mid)
        if obs.get('event_id') != event_id:
            continue
        matches = [m for m in pending if m.get('msg') == mid]
        # A duplicate pending ID is ambiguous; fail closed for that message.
        if len(matches) != 1:
            continue
        m = matches[0]
        if m.get('scored'):
            continue
        if any(m.get(k) != obs.get(k) for k in ('direction', 'channel', 'receiver')):
            continue
        util = obs.get('utility')
        parts = obs.get('parts')
        if (not isinstance(util, (int, float)) or isinstance(util, bool)
                or not math.isfinite(util) or not isinstance(parts, dict)
                or any(not isinstance(v, (int, float)) or isinstance(v, bool)
                       or not math.isfinite(v) for v in parts.values())):
            continue
        update(state, m['direction'], m['channel'], float(util), parts)
        m['scored'] = True
        applied.append(obs)
    return applied


def observation(event_id, pending, utility, parts):
    """Construct an exact identity binding for one verified receiver offer."""
    return {'event_id': event_id, 'msg': pending['msg'],
            'direction': pending['direction'], 'channel': pending['channel'],
            'receiver': pending['receiver'], 'utility': utility, 'parts': parts}
