"""Deterministic, bounded replay selection for source-verified WorldJEPA rows.

The selectors operate only on the already source-disjoint training fold supplied
by the caller. They never see holdout rows and never promote an unknown session
into a synthetic session. The contiguous policy selects one bounded time window
per eligible session, with a deterministic salt for reproducibility.
"""
from __future__ import annotations

import hashlib
import json
import math

REPLAY_MODES = ("uniform", "none", "uniform_budget", "session_contiguous")
MAX_REPLAY_ROWS = 2048


def _validate_rows(rows, label):
    if type(rows) is not list or len(rows) > MAX_REPLAY_ROWS:
        raise ValueError(label + " rows")
    seen = set()
    for row in rows:
        if type(row) is not dict:
            raise ValueError(label + " row")
        action_id = row.get("action_id")
        source_sha = row.get("source_sha256")
        created = row.get("created")
        if (type(action_id) is not str or not action_id or len(action_id) > 128
                or action_id in seen or type(source_sha) is not str
                or len(source_sha) != 64
                or any(ch not in "0123456789abcdef" for ch in source_sha)
                or type(created) not in (int, float) or not math.isfinite(created)):
            raise ValueError(label + " identity")
        session_id = row.get("session_id")
        if session_id is not None and (
                type(session_id) is not str or not session_id or len(session_id) > 128):
            raise ValueError(label + " session")
        seen.add(action_id)
    return seen


def _row_digest(salt, row):
    raw = "\0".join((salt, row["action_id"], row["source_sha256"])).encode("utf-8")
    return hashlib.sha256(raw).digest()


def select_replay_rows(mode, new_rows, old_rows, *, budget, salt):
    """Select old train-fold rows; budget modes match replay row/array bytes.

    new_rows and old_rows must already be partitioned by the caller's
    source-disjoint holdout. Session-contiguous selection excludes legacy rows
    whose session provenance is absent instead of guessing their session.
    """
    if mode not in REPLAY_MODES:
        raise ValueError("unsupported WorldJEPA replay mode")
    if type(budget) is not int or not 0 <= budget <= MAX_REPLAY_ROWS:
        raise ValueError("replay budget")
    if type(salt) is not str or not salt or len(salt) > 256:
        raise ValueError("replay salt")
    new_ids = _validate_rows(new_rows, "new")
    old_ids = _validate_rows(old_rows, "old")
    if new_ids & old_ids:
        raise ValueError("new/old replay identity overlap")

    windows = []
    requested_budget_rows = min(budget, len(old_rows))
    if mode == "uniform":
        selected = list(old_rows)
        budget_rows = len(selected)
        budget_matched = None
    elif mode == "none":
        selected = []
        budget_rows = 0
        budget_matched = None
    elif mode == "uniform_budget":
        budget_rows = requested_budget_rows
        selected = sorted(old_rows, key=lambda row: _row_digest(salt, row))[:budget_rows]
        budget_matched = len(selected) == requested_budget_rows
    else:
        groups = {}
        for row in old_rows:
            session_id = row.get("session_id")
            if session_id is not None:
                groups.setdefault(session_id, []).append(row)
        for values in groups.values():
            values.sort(key=lambda row: (float(row["created"]), row["action_id"]))
        session_ids = sorted(groups)
        eligible = sum(len(groups[session_id]) for session_id in session_ids)
        budget_rows = min(budget, eligible)
        allocation = {session_id: 0 for session_id in session_ids}
        remaining = budget_rows
        while remaining:
            progressed = False
            for session_id in session_ids:
                if remaining == 0:
                    break
                if allocation[session_id] < len(groups[session_id]):
                    allocation[session_id] += 1
                    remaining -= 1
                    progressed = True
            if not progressed:
                break
        selected = []
        for session_id in session_ids:
            count = allocation[session_id]
            if not count:
                continue
            values = groups[session_id]
            digest = hashlib.sha256(
                (salt + "\0session\0" + session_id).encode("utf-8")
            ).digest()
            start = int.from_bytes(digest[:8], "big") % (len(values) - count + 1)
            window = values[start:start + count]
            selected.extend(window)
            windows.append({
                "session_id": session_id,
                "start_index": start,
                "count": count,
                "start_action_id": window[0]["action_id"],
                "end_action_id": window[-1]["action_id"],
            })
        budget_matched = len(selected) == requested_budget_rows

    selected_ids = [row["action_id"] for row in selected]
    manifest = {
        "mode": mode,
        "budget_rows": budget_rows,
        "selected_action_ids": selected_ids,
        "windows": windows,
    }
    manifest_sha256 = hashlib.sha256(json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    session_count = len({
        row["session_id"] for row in selected if row.get("session_id") is not None
    })
    return {
        "rows": selected,
        "budget_rows": budget_rows,
        "requested_budget_rows": requested_budget_rows,
        "budget_matched": budget_matched,
        "session_count": session_count,
        "window_count": len(windows),
        "manifest_sha256": manifest_sha256,
        "windows": windows,
    }
