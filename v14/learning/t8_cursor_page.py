"""Cursor paging adapter around the canonical V13 T8 transition reader.

The V13 world_model source is intentionally not modified: existing staged
consumers pin its exact bytes. This adapter rewrites only the bounded SQL page
query while delegating all parsing, ActionSelection checks and numeric target
construction to world_model.transitions(), then delegates provenance checks
to the canonical verify_committed_transitions() authority.
"""
from __future__ import annotations

import math

from v13 import world_model
from t8_store_authority import verify_committed_transitions


_TRANSITION_QUERY = (
    "SELECT a.id,a.event_id,a.status,a.expected,a.outcome,a.created,e.generation_id "
    "FROM actions a JOIN events e ON e.id=a.event_id "
    "WHERE a.outcome IS NOT NULL AND a.expected LIKE ? "
    "ORDER BY a.created DESC LIMIT ?"
)
_PAGE_SELECT = (
    "SELECT a.id,a.event_id,a.status,a.expected,a.outcome,a.created,e.generation_id "
    "FROM actions a JOIN events e ON e.id=a.event_id "
    "WHERE a.outcome IS NOT NULL AND a.expected LIKE ? "
)


class _CursorPageStore:
    def __init__(self, store, limit, after):
        self._store = store
        self.limit = limit
        self.after = after
        self.cursor = after

    def rows(self, sql, args=()):
        if sql == _TRANSITION_QUERY:
            if (type(args) not in (tuple, list) or len(args) != 2
                    or args[1] != self.limit):
                raise ValueError("unexpected canonical T8 transition query arguments")
            pattern = args[0]
            if self.after is None:
                # Select the oldest bounded window, then return it newest-first
                # because world_model.transitions() reverses its raw query.
                rows = self._store.rows(
                    "SELECT page.id,page.event_id,page.status,page.expected,page.outcome,"
                    "page.created,page.generation_id FROM ("
                    + _PAGE_SELECT
                    + "ORDER BY a.created ASC,a.id ASC LIMIT ?) AS page "
                    "ORDER BY page.created DESC,page.id DESC",
                    (pattern, self.limit),
                )
            else:
                created = float(self.after["created"])
                action_id = self.after["action_id"]
                rows = self._store.rows(
                    _PAGE_SELECT
                    + "AND (a.created > ? OR (a.created = ? AND a.id > ?)) "
                    "ORDER BY a.created DESC,a.id DESC LIMIT ?",
                    (pattern, created, created, action_id, self.limit),
                )
            if rows:
                newest = rows[0]
                self.cursor = {
                    "created": float(newest["created"]),
                    "action_id": newest["id"],
                }
            return rows
        return self._store.rows(sql, args)

    def one(self, sql, args=()):
        return self._store.one(sql, args)

    def read_source(self, source_ref):
        return self._store.read_source(source_ref)


def verify_committed_transitions_page(store, limit=world_model.MAX_ROWS, after=None):
    """Verify an oldest-first T8 page and return the raw SQL scan cursor.

    A malformed row is skipped by the canonical transition parser but still
    advances the raw cursor. Source read failures propagate; callers therefore
    do not commit a cursor for an incomplete provenance read.
    """
    if type(limit) is not int or not 1 <= limit <= world_model.MAX_ROWS:
        raise ValueError("limit")
    if after is not None:
        if (type(after) is not dict or set(after) != {"created", "action_id"}
                or type(after.get("created")) not in (int, float)
                or not math.isfinite(float(after["created"]))
                or type(after.get("action_id")) is not str
                or not after["action_id"] or len(after["action_id"]) > 128):
            raise ValueError("invalid T8 cursor")
    page_store = _CursorPageStore(store, limit, after)
    verified, rejected = verify_committed_transitions(page_store, limit=limit)
    return verified, rejected, page_store.cursor
