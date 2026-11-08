"""Review-only C5 human-feedback ledger; no runtime authority or implicit migration.
Rebuilds effective feedback from one latest rating per event. Persist returned JSON
using the caller's transactional state CAS; failed CAS must retry the whole operation.
"""
import math

REVISION = 'c5-feedback-ledger-candidate-v1'
MAX_EVENTS = 10000

def empty():
    return {'revision': REVISION, 'ratings': {}}

def record(state, event_id, context, action_id, score):
    """Return a fresh state with an upserted rating, never double-counting an event."""
    if not isinstance(state, dict) or state.get('revision') != REVISION:
        raise ValueError('unknown ledger revision')
    if not isinstance(event_id, str) or not event_id or len(event_id) > 256:
        raise ValueError('invalid event ID')
    if not all(isinstance(x, str) and x and len(x) <= 256 for x in (context, action_id)):
        raise ValueError('invalid action binding')
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 1 <= score <= 10:
        raise ValueError('invalid rating')
    old = state.get('ratings')
    if not isinstance(old, dict):
        raise ValueError('invalid ratings')
    prior = old.get(event_id)
    if prior is not None and (prior['context'], prior['action_id']) != (context, action_id):
        raise ValueError('event action binding changed')
    if prior is None and len(old) >= MAX_EVENTS:
        raise ValueError('ledger capacity exhausted; fail closed')
    ratings = dict(old)
    ratings[event_id] = {'context': context, 'action_id': action_id, 'score': float(score)}
    return {'revision': REVISION, 'ratings': ratings}

def aggregate(state):
    """Derive effective human feedback; never mutate historical C5 EMA implicitly."""
    if not isinstance(state, dict) or state.get('revision') != REVISION:
        raise ValueError('unknown ledger revision')
    out = {}
    for event_id, row in sorted(state['ratings'].items()):
        if not isinstance(event_id, str) or not isinstance(row, dict):
            raise ValueError('invalid ledger row')
        ctx, action, score = row['context'], row['action_id'], row['score']
        if not all(isinstance(x, str) and x for x in (ctx, action)) or isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 1 <= score <= 10:
            raise ValueError('invalid ledger row')
        key = ctx + '|' + action
        slot = out.setdefault(key, {'n': 0, 'human_approval_sum': 0., 'human_correction_sum': 0.})
        u = (score - 1.) / 9.
        slot['n'] += 1
        slot['human_approval_sum'] += u if u >= .5 else 0.
        slot['human_correction_sum'] += 1. - u if u < .5 else 0.
    return {k: {'n': v['n'], 'human_approval': v['human_approval_sum'] / v['n'],
                'human_correction': v['human_correction_sum'] / v['n']}
            for k, v in out.items()}
