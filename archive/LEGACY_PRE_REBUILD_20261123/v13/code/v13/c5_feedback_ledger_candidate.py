"""Review-only C5 human-feedback ledger; no runtime authority or implicit migration.
Rebuilds effective feedback from one latest rating per event. Persist returned JSON
using the caller's transactional state CAS; failed CAS must retry the whole operation.
"""
import math

REVISION = 'c5-feedback-ledger-candidate-v1'
MAX_EVENTS = 10000

def _binding(value, *, action=False):
    # Contexts legitimately contain a route|effort separator. Only action IDs
    # must exclude '|', making the final separator unambiguous.
    return isinstance(value, str) and 0 < len(value) <= 256 and (not action or '|' not in value)

def _validate(state):
    if not isinstance(state, dict) or set(state) != {'revision', 'ratings'} or state['revision'] != REVISION:
        raise ValueError('unknown ledger revision')
    ratings = state['ratings']
    if not isinstance(ratings, dict) or len(ratings) > MAX_EVENTS:
        raise ValueError('invalid ratings')
    for event_id, row in ratings.items():
        if not isinstance(event_id, str) or not 0 < len(event_id) <= 256:
            raise ValueError('invalid event ID')
        if not isinstance(row, dict) or set(row) != {'context', 'action_id', 'score'}:
            raise ValueError('invalid ledger row')
        if not _binding(row['context']) or not _binding(row['action_id'], action=True):
            raise ValueError('invalid ledger row')
        score = row['score']
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 1 <= score <= 10:
            raise ValueError('invalid ledger row')
    return ratings

def empty():
    return {'revision': REVISION, 'ratings': {}}

def record(state, event_id, context, action_id, score):
    """Return a fresh state with an upserted rating, never double-counting an event."""
    old = _validate(state)
    if not isinstance(event_id, str) or not event_id or len(event_id) > 256:
        raise ValueError('invalid event ID')
    if not _binding(context) or not _binding(action_id, action=True):
        raise ValueError('invalid action binding')
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 1 <= score <= 10:
        raise ValueError('invalid rating')
    prior = old.get(event_id)
    if prior is not None and (prior['context'], prior['action_id']) != (context, action_id):
        raise ValueError('event action binding changed')
    if prior is None and len(old) >= MAX_EVENTS:
        raise ValueError('ledger capacity exhausted; fail closed')
    # Snapshot nested rows too: the caller must not mutate a returned state
    # by changing an earlier state (or vice versa) after a correction.
    ratings = {key: dict(row) for key, row in old.items()}
    ratings[event_id] = {'context': context, 'action_id': action_id, 'score': float(score)}
    return {'revision': REVISION, 'ratings': ratings}

def aggregate(state):
    """Derive effective human feedback; never mutate historical C5 EMA implicitly."""
    ratings = _validate(state)
    out = {}
    for event_id, row in sorted(ratings.items()):
        ctx, action, score = row['context'], row['action_id'], row['score']
        key = ctx + '|' + action
        slot = out.setdefault(key, {'n': 0, 'human_approval_sum': 0., 'human_correction_sum': 0.})
        u = (score - 1.) / 9.
        slot['n'] += 1
        slot['human_approval_sum'] += u if u >= .5 else 0.
        slot['human_correction_sum'] += 1. - u if u < .5 else 0.
    return {k: {'n': v['n'], 'human_approval': v['human_approval_sum'] / v['n'],
                'human_correction': v['human_correction_sum'] / v['n']}
            for k, v in out.items()}
