"""Revalidate all source-bound predictor receipts in a disposable Runtime copy.

This is a correctness-oriented synchronous fence, not a mobile scheduler.
"""
from __future__ import annotations

from . import world_model
from .store import Store

CHUNK = 200
ACTION_QUERY = ("SELECT a.id,a.event_id,a.status,a.expected,a.outcome,a.created,e.generation_id "
                "FROM actions a JOIN events e ON e.id=a.event_id WHERE a.outcome IS NOT NULL "
                "AND a.expected LIKE ? ORDER BY a.created DESC LIMIT ?")


class _SelectedActions:
    """Restrict T8's existing parser to a bounded list of exact action IDs."""
    def __init__(self, store, action_ids):
        self.store = store
        self.action_ids = tuple(action_ids)
        self.queries = 0

    def rows(self, sql, args=()):
        if sql == ACTION_QUERY:
            self.queries += 1
            if args != ('%"forecast"%', len(self.action_ids)):
                raise ValueError('unexpected T8 history selection')
            marks = ','.join('?' for _ in self.action_ids)
            sql = sql.replace('WHERE a.outcome IS NOT NULL',
                              'WHERE a.id IN (' + marks + ') AND a.outcome IS NOT NULL', 1)
            return self.store.rows(sql, self.action_ids + tuple(args))
        return self.store.rows(sql, args)


def _verify(world):
    if world._unusable:
        raise RuntimeError('Online world needs review after stale source or failed recovery')
    receipts = world.processed
    if type(receipts) is not dict or len(receipts) > world.MAX_HISTORY_RECEIPTS:
        raise ValueError('invalid online world history')
    if world.model.seen != len(receipts) or world._receipts() != receipts:
        raise ValueError('online world model and source history disagree')
    ids = sorted(receipts)
    for index in range(0, len(ids), CHUNK):
        selected = _SelectedActions(world.runtime.store, ids[index:index + CHUNK])
        rows = world_model.transitions(selected, limit=len(selected.action_ids))
        if selected.queries != 1 or len(rows) != len(selected.action_ids):
            raise ValueError('previously learned action no longer yields a valid transition')
        mapping = {row.get('action_id'): row for row in rows}
        if set(mapping) != set(selected.action_ids):
            raise ValueError('previously learned online world source missing or duplicate')
        for action_id in selected.action_ids:
            row = mapping[action_id]
            if world._digest(row) != receipts[action_id] or not world._source_current(row):
                raise ValueError('previously learned online world source changed or revoked')


def guarded(world, operation):
    """Fence cooperating SQLite revocations through verification and operation."""
    if type(world.runtime.store) is not Store:
        world._unusable = True
        raise ValueError('reviewed Store instance required')
    try:
        with world.runtime.store.tx():
            _verify(world)
            return operation()
    except BaseException:
        # Publication may already have occurred if a post-replace/fsync or
        # transaction completion fails. Never silently reuse that instance.
        world._unusable = True
        raise
