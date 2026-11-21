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

REPLAY_MODES = ("uniform", "none", "uniform_budget", "session_contiguous", "on_demand_conflict", "on_demand_loss")
MAX_REPLAY_ROWS = 2048
MAX_REPLAY_CONSTRAINTS = 8


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


def select_replay_rows(mode, new_rows, old_rows, *, budget, salt, cohort_scores=None):
    """Select old train-fold rows; holdout rows and targets are never visible.

    on_demand_conflict ranks prior sessions by the negative cosine between
    new-cohort and session replay gradients. on_demand_loss ranks only sessions
    with positive loss growth in a disposable no-replay probe. Both are bounded
    experiments, not a reproduction of full reference-model Replay-on-Demand.
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
    extra = {"selected_session_keys": [], "legacy_rows_excluded": 0,
             "scored_session_count": 0, "unscored_session_count": 0}
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
    elif mode == "session_contiguous":
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
            start_index = int.from_bytes(digest[:8], "big") % (len(values) - count + 1)
            window = values[start_index:start_index + count]
            selected.extend(window)
            windows.append({
                "session_id": session_id,
                "start_index": start_index,
                "count": count,
                "start_action_id": window[0]["action_id"],
                "end_action_id": window[-1]["action_id"],
            })
        budget_matched = len(selected) == requested_budget_rows
    elif mode == "on_demand_loss":
        if type(cohort_scores) is not dict or len(cohort_scores) > 64:
            raise ValueError("loss-demand replay requires a bounded session-score map")
        for session_id, score in cohort_scores.items():
            if (type(session_id) is not str or not session_id or len(session_id) > 128
                    or type(score) not in (int, float) or not math.isfinite(score)
                    or score < 0.0):
                raise ValueError("invalid loss-demand replay score")
        groups = {}
        for row in old_rows:
            session_id = row.get("session_id")
            if type(session_id) is str and session_id:
                groups.setdefault(session_id, []).append(row)
        extra["legacy_rows_excluded"] = sum(
            1 for row in old_rows if not row.get("session_id")
        )
        if not set(cohort_scores).issubset(set(groups)):
            raise ValueError("loss-demand score references an unknown session")
        eligible_all = {
            session_id: values for session_id, values in groups.items()
            if len(values) >= 2
        }
        extra["scored_session_count"] = sum(
            1 for session_id in eligible_all if session_id in cohort_scores
        )
        extra["unscored_session_count"] = len(groups) - extra["scored_session_count"]
        eligible = {
            session_id: values for session_id, values in eligible_all.items()
            if session_id in cohort_scores and float(cohort_scores[session_id]) > 0.0
        }
        ranked = sorted(
            eligible,
            key=lambda session_id: (
                -float(cohort_scores[session_id]),
                hashlib.sha256((salt + "\0loss-rank\0" + session_id).encode("utf-8")).digest(),
            ),
        )
        max_sessions = min(MAX_REPLAY_CONSTRAINTS, budget // 2, len(ranked))
        selected_sessions = ranked[:max_sessions]
        eligible_rows = sum(len(eligible[session_id]) for session_id in selected_sessions)
        budget_rows = min(requested_budget_rows, eligible_rows)
        while selected_sessions and budget_rows < 2 * len(selected_sessions):
            selected_sessions.pop()
        allocation = {session_id: 2 for session_id in selected_sessions}
        remaining = budget_rows - sum(allocation.values())
        while remaining > 0:
            progressed = False
            for session_id in selected_sessions:
                if allocation[session_id] < len(eligible[session_id]):
                    allocation[session_id] += 1
                    remaining -= 1
                    progressed = True
                    if remaining == 0:
                        break
            if not progressed:
                break
        selected = []
        for session_id in selected_sessions:
            values = eligible[session_id]
            count = allocation[session_id]
            chosen = sorted(values, key=lambda row: _row_digest(salt, row))[:count]
            chosen.sort(key=lambda row: (float(row["created"]), row["action_id"]))
            selected.extend(chosen)
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]
            extra["selected_session_keys"].append(session_key)
            windows.append({
                "session_key": session_key,
                "count": count,
                "loss_demand_score": float(cohort_scores[session_id]),
            })
        budget_matched = len(selected) == requested_budget_rows
    else:
        if type(cohort_scores) is not dict or len(cohort_scores) > 64:
            raise ValueError("on-demand replay requires a bounded session-score map")
        for session_id, score in cohort_scores.items():
            if (type(session_id) is not str or not session_id or len(session_id) > 128
                    or type(score) not in (int, float) or not math.isfinite(score)
                    or score < 0.0):
                raise ValueError("invalid on-demand replay cohort score")
        groups = {}
        for row in old_rows:
            session_id = row.get("session_id")
            if type(session_id) is str and session_id:
                groups.setdefault(session_id, []).append(row)
        extra["legacy_rows_excluded"] = sum(
            1 for row in old_rows if not row.get("session_id")
        )
        eligible_all = {
            session_id: values for session_id, values in groups.items()
            if len(values) >= 2
        }
        if not set(cohort_scores).issubset(set(groups)):
            raise ValueError("on-demand replay score references an unknown session")
        eligible = {
            session_id: values for session_id, values in eligible_all.items()
            if session_id in cohort_scores
        }
        extra["scored_session_count"] = len(eligible)
        extra["unscored_session_count"] = len(groups) - len(eligible)
        ranked = sorted(
            eligible,
            key=lambda session_id: (
                -float(cohort_scores[session_id]),
                hashlib.sha256((salt + "\0rank\0" + session_id).encode("utf-8")).digest(),
            ),
        )
        max_sessions = min(MAX_REPLAY_CONSTRAINTS, budget // 2, len(ranked))
        selected_sessions = ranked[:max_sessions]
        eligible_rows = sum(len(eligible[session_id]) for session_id in selected_sessions)
        budget_rows = min(requested_budget_rows, eligible_rows)
        while selected_sessions and budget_rows < 2 * len(selected_sessions):
            selected_sessions.pop()
        allocation = {session_id: 2 for session_id in selected_sessions}
        remaining = budget_rows - sum(allocation.values())
        while remaining > 0:
            progressed = False
            for session_id in selected_sessions:
                if allocation[session_id] < len(eligible[session_id]):
                    allocation[session_id] += 1
                    remaining -= 1
                    progressed = True
                    if remaining == 0:
                        break
            if not progressed:
                break
        selected = []
        for session_id in selected_sessions:
            values = eligible[session_id]
            count = allocation[session_id]
            chosen = sorted(values, key=lambda row: _row_digest(salt, row))[:count]
            chosen.sort(key=lambda row: (float(row["created"]), row["action_id"]))
            selected.extend(chosen)
            session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]
            extra["selected_session_keys"].append(session_key)
            windows.append({
                "session_key": session_key,
                "count": count,
                "conflict_score": float(cohort_scores[session_id]),
            })
        budget_matched = len(selected) == requested_budget_rows

    selected_ids = [row["action_id"] for row in selected]
    manifest = {
        "mode": mode,
        "budget_rows": budget_rows,
        "selected_action_ids": selected_ids,
        "windows": windows,
        "selected_session_keys": extra["selected_session_keys"],
        "legacy_rows_excluded": extra["legacy_rows_excluded"],
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
        **extra,
    }
